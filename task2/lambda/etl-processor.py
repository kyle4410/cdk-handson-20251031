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

# ロギング設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
OUTPUT_PREFIX = os.getenv("OUTPUT_PREFIX", "structured/")
FAILED_PREFIX = os.getenv("FAILED_PREFIX", "structured/failed/")

# CLF 形式のログをパースする正規表現
CLF_RE = re.compile(r"^(?P<ip>\S+) \S+ \S+ \[(?P<ts>[^\]]+)\] \"(?P<method>\S+) (?P<path>\S+) \S+\" (?P<status>\d{3}) (?P<size>\d+)")

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
        logger.warning(f"Failed to parse line: {line[:100]}... Error: {str(e)}")
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

                # GZIP 解凍（Firehose 出力前提）
                with gzip.GzipFile(fileobj=io.BytesIO(byts), mode='rb') as gz:
                    data = gz.read().decode("utf-8", errors="replace")

                logger.info(f"Decompressed data: {len(data)} characters")

                ok = []
                ng = []

                # 各行をパース
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

                # 成功したログをS3に書き込み
                if ok:
                    ok_body = "\n".join(json.dumps(x) for x in ok)
                    s3.put_object(
                        Bucket=bucket,
                        Key=out_ok,
                        Body=ok_body.encode("utf-8"),
                        ContentType="application/json"
                    )
                    logger.info(f"SUCCESS: Wrote {len(ok)} parsed logs to s3://{bucket}/{out_ok}")
                    success_count += len(ok)

                # 失敗したログをS3に書き込み
                if ng:
                    ng_body = "\n".join(json.dumps(x) for x in ng)
                    s3.put_object(
                        Bucket=bucket,
                        Key=out_ng,
                        Body=ng_body.encode("utf-8"),
                        ContentType="application/json"
                    )
                    logger.info(f"WARNING: Wrote {len(ng)} failed logs to s3://{bucket}/{out_ng}")
                    error_count += len(ng)

                processed_count += 1

            except Exception as e:
                error_msg = f"ERROR: Failed to process s3://{bucket}/{key}: {str(e)}"
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
        error_msg = f"ERROR: Lambda handler failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }

