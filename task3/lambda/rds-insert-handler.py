"""
RDSにINSERTするLambda関数
Secrets Managerから認証情報を取得し、VPC内のRDS（MySQL）に接続してデータをINSERTします
"""
import json
import os
import logging
import boto3
import pymysql

# ロギング設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Secrets Manager クライアント
secrets = boto3.client('secretsmanager')
SECRET_ID = os.getenv('SECRET_ID', 'db-credentials')

def get_db_connection():
    """
    Secrets Managerから認証情報を取得し、RDSに接続する

    Returns:
        pymysql.Connection: データベース接続オブジェクト
    """
    try:
        logger.info(f"Retrieving secret from Secrets Manager: {SECRET_ID}")

        # Secrets Managerからシークレットを取得
        response = secrets.get_secret_value(SecretId=SECRET_ID)
        secret_string = response['SecretString']
        conf = json.loads(secret_string)

        logger.info(f"Successfully retrieved secret. Connecting to RDS: {conf.get('host')}:{conf.get('port', 3306)}")

        # RDSに接続
        conn = pymysql.connect(
            host=conf['host'],
            port=conf.get('port', 3306),
            user=conf['username'],
            password=conf['password'],
            database=conf['dbname'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10
        )

        logger.info("SUCCESS: Successfully connected to RDS")
        return conn

    except Exception as e:
        error_msg = f"ERROR: Failed to connect to RDS: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise

def lambda_handler(event, context):
    """
    Lambdaハンドラ: リクエストデータを受けてRDSにINSERTする

    Args:
        event: Lambdaイベント（API Gatewayイベントまたはテストイベント）
        context: Lambdaコンテキスト

    Returns:
        dict: レスポンス（ステータスコードとボディ）
    """
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        # リクエストボディの取得
        body = event.get('body')
        if isinstance(body, str):
            body = json.loads(body)
        elif body is None:
            # bodyがない場合、event自体をbodyとして扱う
            body = event

        # 必須パラメータの取得と検証
        name = body.get('name')
        email = body.get('email')
        message = body.get('message')
        client_ip = body.get('client_ip')

        logger.info(f"Received data: name={name}, email={email}, message_length={len(message) if message else 0}, client_ip={client_ip}")

        if not (name and email and message):
            error_msg = "name,email,message are required"
            logger.error(f"ERROR: Validation failed - {error_msg}")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": error_msg})
            }

        # データベース接続
        conn = get_db_connection()

        try:
            # INSERT実行
            with conn.cursor() as cur:
                sql = "INSERT INTO inquiries(name,email,message,client_ip) VALUES(%s,%s,%s,%s)"
                cur.execute(sql, (name, email, message, client_ip))

            # コミット
            conn.commit()

            # 挿入されたレコードのIDを取得（AUTO_INCREMENT）
            inserted_id = conn.insert_id()

            logger.info(f"SUCCESS: Inserted record with id={inserted_id} to RDS")

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "ok": True,
                    "id": inserted_id,
                    "message": "Record inserted successfully"
                })
            }

        except Exception as e:
            # ロールバック
            conn.rollback()
            error_msg = f"ERROR: Failed to insert record: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise

        finally:
            conn.close()
            logger.info("Database connection closed")

    except Exception as e:
        error_msg = f"ERROR: Lambda handler failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Internal server error",
                "message": str(e)
            })
        }

