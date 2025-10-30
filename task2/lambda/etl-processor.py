"""
S3のGZIP圧縮されたログファイルを解凍し、CLF形式をパースしてJSONに変換するLambda関数
"""
import boto3
import gzip
import io
import json
import os
import re
import logging
from datetime import datetime, timezone

# ロギング設定（CloudWatch Logsに出力）
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Lambda環境ではルートロガーのハンドラが既に設定されているため、フォーマットのみ設定
# CloudWatch Logsに出力されるログのフォーマットを改善
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '[%(levelname)s] %(asctime)s - %(name)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

s3 = boto3.client("s3")
OUTPUT_PREFIX = os.getenv("OUTPUT_PREFIX", "structured/")
FAILED_PREFIX = os.getenv("FAILED_PREFIX", "structured/failed/")

# CLF 形式のログをパースする正規表現
# 形式: IP - - [timestamp] "METHOD path HTTP/1.1" status size "-" "user-agent"
# パスの部分はクエリパラメータ（?や=を含む）を含む可能性があるため、非貪欲マッチを使用
# パスの後には必ず空白があり、その後にHTTP/1.1などのプロトコルバージョンが続く
CLF_RE = re.compile(r"^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<ts>[^\]]+)\]\s+\"(?P<method>\S+)\s+(?P<path>[^\"]+?)\s+\S+\"\s+(?P<status>\d{3})\s+(?P<size>\d+)")

def parse_clf(line: str):
    """
    CLF形式のログ行をパースして辞書に変換

    Args:
        line: CLF形式のログ行

    Returns:
        パース成功時: 正規化された辞書、失敗時: None
    """
    try:
        m = CLF_RE.match(line.strip())
        if not m:
            return None

        ts_str = m.group("ts")  # e.g. 10/Oct/2025:13:55:36 +0000
        dt = datetime.strptime(ts_str, "%d/%b/%Y:%H:%M:%S %z").astimezone(timezone.utc)

        return {
            "ip": m.group("ip"),
            "method": m.group("method"),
            "path": m.group("path"),
            "status": int(m.group("status")),
            "size": int(m.group("size")),
            "ts_iso": dt.isoformat(),
            "yyyymmdd": dt.strftime("%Y%m%d"),
            "hour": dt.strftime("%H"),
        }
    except Exception as e:
        # CloudWatch Logsにエラーログを出力
        logger.warning(
            f"Failed to parse CLF line. "
            f"Line (first 200 chars): {line[:200]}, "
            f"Error: {str(e)}"
        )
        return None

def lambda_handler(event, context):
    """
    S3イベントを受けてGZIPファイルを処理するLambdaハンドラ

    Args:
        event: S3イベント
        context: Lambdaコンテキスト

    Returns:
        処理結果の辞書
    """
    logger.info(f"Received event: {json.dumps(event)}")

    processed_count = 0
    success_count = 0
    error_count = 0

    try:
        for record in event.get("Records", []):
            bucket = record["s3"]["bucket"]["name"]
            key = record["s3"]["object"]["key"]

            logger.info(f"Processing file: s3://{bucket}/{key}")

            try:
                # S3からオブジェクトを取得
                obj = s3.get_object(Bucket=bucket, Key=key)
                byts = obj["Body"].read()

                logger.info(f"Downloaded {len(byts)} bytes from S3")

                # GZIP解凍（Firehose出力はGZIP圧縮されている）
                # 二重圧縮の可能性があるため、繰り返し解凍を試行
                try:
                    decompressed_bytes = gzip.decompress(byts)
                    logger.info(f"GZIP decompressed (1st): {len(decompressed_bytes)} bytes")

                    # 解凍後のデータがまだGZIP圧縮されているかチェック
                    # GZIPマジックナンバー: 0x1f 0x8b
                    if len(decompressed_bytes) >= 2 and decompressed_bytes[0] == 0x1f and decompressed_bytes[1] == 0x8b:
                        logger.info("Detected double GZIP compression, decompressing again...")
                        decompressed_bytes = gzip.decompress(decompressed_bytes)
                        logger.info(f"GZIP decompressed (2nd): {len(decompressed_bytes)} bytes")

                    # UTF-8デコード
                    data = decompressed_bytes.decode("utf-8")
                    logger.info(f"UTF-8 decoded successfully: {len(data)} characters")
                    logger.info(f"First 200 chars: {data[:200]}")

                except gzip.BadGzipFile:
                    # GZIP形式ではない場合、生データとして処理
                    logger.warning("Not a valid GZIP file, treating as raw data")
                    data = byts.decode("utf-8")
                    logger.info(f"Raw data (not compressed): {len(data)} characters")
                except UnicodeDecodeError as e:
                    logger.error(f"UTF-8デコードエラー: {str(e)}")
                    logger.error(f"First 10 bytes (hex): {decompressed_bytes[:10].hex()}")
                    raise
                except Exception as e:
                    logger.error(f"GZIP解凍エラー: {str(e)}", exc_info=True)
                    raise

                ok = []
                ng = []

                # Firehose出力のJSON形式を処理
                try:
                    # JSON形式の場合
                    firehose_data = json.loads(data)
                    logger.info(f"JSON parsed successfully. messageType: {firehose_data.get('messageType')}")

                    if firehose_data.get("messageType") == "DATA_MESSAGE":
                        # CloudWatch LogsからのFirehose出力
                        log_events = firehose_data.get("logEvents", [])
                        logger.info(f"Processing {len(log_events)} log events from Firehose")

                        for event in log_events:
                            message = event.get("message", "")
                            if not message.strip():
                                continue

                            parsed = parse_clf(message)
                            if parsed:
                                # タイムスタンプを追加
                                parsed["log_timestamp"] = event.get("timestamp")
                                parsed["log_id"] = event.get("id")
                                ok.append(parsed)
                            else:
                                ng.append({"raw": message, "log_id": event.get("id")})
                    else:
                        logger.info(f"Not DATA_MESSAGE format, messageType: {firehose_data.get('messageType')}")
                        # 通常のCLF形式のログファイル
                        for line in data.splitlines():
                            if not line.strip():
                                continue
                            parsed = parse_clf(line)
                            if parsed:
                                ok.append(parsed)
                            else:
                                ng.append({"raw": line})
                except json.JSONDecodeError as e:
                    # JSON解析に失敗した場合、通常のCLF形式として処理
                    logger.warning(f"JSON解析に失敗: {str(e)}")
                    logger.warning(f"Data content (first 500 chars): {data[:500]}")
                    logger.info("Processing as CLF logs")
                    for line in data.splitlines():
                        if not line.strip():
                            continue
                        parsed = parse_clf(line)
                        if parsed:
                            ok.append(parsed)
                        else:
                            ng.append({"raw": line})

                logger.info(f"Parsed results: {len(ok)} successful, {len(ng)} failed")

                # 出力キー（raw/ 以下のキーを structured/ に差し替える）
                if "raw/" in key:
                    base = key.split("raw/", 1)[-1]
                else:
                    # raw/がない場合はファイル名のみ
                    base = os.path.basename(key)

                out_ok = OUTPUT_PREFIX + base.replace(".gz", ".json")
                out_ng = FAILED_PREFIX + base.replace(".gz", ".json")

                # パース失敗したログがある場合、CloudWatch Logsに警告を出力
                if ng:
                    logger.warning(
                        f"Found {len(ng)} failed log lines in s3://{bucket}/{key}. "
                        f"Failed lines will be written to s3://{bucket}/{out_ng}. "
                        f"First failed line (max 200 chars): {ng[0].get('raw', '')[:200] if ng else 'N/A'}"
                    )

                # 成功したログをS3に書き込み
                if ok:
                    try:
                        ok_body = "\n".join(json.dumps(x) for x in ok)
                        s3.put_object(
                            Bucket=bucket,
                            Key=out_ok,
                            Body=ok_body.encode("utf-8"),
                            ContentType="application/json"
                        )
                        logger.info(f"SUCCESS: Wrote {len(ok)} parsed logs to s3://{bucket}/{out_ok}")
                        success_count += len(ok)
                    except Exception as e:
                        # CloudWatch LogsにS3書き込みエラーを出力
                        logger.error(
                            f"ERROR: Failed to write success logs to s3://{bucket}/{out_ok}. "
                            f"Error type: {type(e).__name__}, "
                            f"Error message: {str(e)}",
                            exc_info=True
                        )
                        raise

                # 失敗したログをS3に書き込み
                if ng:
                    try:
                        ng_body = "\n".join(json.dumps(x) for x in ng)
                        s3.put_object(
                            Bucket=bucket,
                            Key=out_ng,
                            Body=ng_body.encode("utf-8"),
                            ContentType="application/json"
                        )
                        logger.info(f"WARNING: Wrote {len(ng)} failed logs to s3://{bucket}/{out_ng}")
                        error_count += len(ng)
                    except Exception as e:
                        # CloudWatch LogsにS3書き込みエラーを出力
                        logger.error(
                            f"ERROR: Failed to write failed logs to s3://{bucket}/{out_ng}. "
                            f"Error type: {type(e).__name__}, "
                            f"Error message: {str(e)}",
                            exc_info=True
                        )
                        raise

                processed_count += 1

            except Exception as e:
                # CloudWatch Logsにエラーログを出力（スタックトレース付き）
                error_msg = (
                    f"ERROR: Failed to process s3://{bucket}/{key}. "
                    f"Error type: {type(e).__name__}, "
                    f"Error message: {str(e)}"
                )
                logger.error(error_msg, exc_info=True)
                error_count += 1
                # 処理を続行（他のファイルを処理）

        result = {
            "status": "done",
            "processed_files": processed_count,
            "successful_logs": success_count,
            "failed_logs": error_count
        }

        logger.info(f"SUCCESS: Processing completed. Result: {json.dumps(result)}")
        return result

    except Exception as e:
        # CloudWatch Logsにエラーログを出力（スタックトレース付き）
        error_msg = (
            f"ERROR: Lambda handler failed. "
            f"Error type: {type(e).__name__}, "
            f"Error message: {str(e)}"
        )
        logger.error(error_msg, exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }

