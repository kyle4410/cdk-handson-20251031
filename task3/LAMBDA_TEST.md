# Lambda関数テスト手順

このドキュメントでは、RDS INSERT用Lambda関数をテストする手順を説明します。

## 前提条件

- Lambda関数がデプロイ済みであること
- RDSに `inquiries` テーブルが作成済みであること（[テーブル作成手順](./DATABASE_SETUP.md)参照）
- Secrets Managerに `db-credentials` シークレットが作成済みであること

## テスト方法

### 方法1: AWS Lambdaコンソールでテスト（推奨）

#### 1. テストイベントの作成

1. AWS Lambdaコンソールで対象のLambda関数を開く
2. **テスト**タブを選択
3. **新しいイベントを作成**をクリック
4. イベント名を入力（例: `test-inquiry-insert`）
5. 以下のJSONを入力：

```json
{
  "name": "山田太郎",
  "email": "yamada@example.com",
  "message": "これはテストメッセージです。Lambda関数が正常に動作していることを確認します。",
  "client_ip": "203.0.113.10"
}
```

6. **保存**をクリック

#### 2. テスト実行

1. 作成したテストイベントが選択されていることを確認
2. **テスト**ボタンをクリック
3. 実行結果を確認

#### 3. 成功時のレスポンス例

```json
{
  "statusCode": 200,
  "body": "{\"ok\": true, \"id\": 1, \"message\": \"Record inserted successfully\"}"
}
```

#### 4. CloudWatch Logsの確認

1. Lambda関数のページで**モニタリング**タブを選択
2. **CloudWatch Logsで表示**をクリック
3. 最新のログストリームを開く
4. 以下のようなログが出力されていることを確認：

```
[INFO] Received event: {"name":"山田太郎","email":"yamada@example.com",...}
[INFO] Retrieving secret from Secrets Manager: db-credentials
[INFO] Successfully retrieved secret. Connecting to RDS: mydb.xxxxx.rds.amazonaws.com:3306
[INFO] SUCCESS: Successfully connected to RDS
[INFO] Received data: name=山田太郎, email=yamada@example.com, message_length=45, client_ip=203.0.113.10
[INFO] SUCCESS: Inserted record with id=1 to RDS
[INFO] Database connection closed
[INFO] SUCCESS: Processing completed. Result: {...}
```

### 方法2: AWS CLIでテスト

#### 1. テストイベントJSONファイルの作成

`test-event.json` というファイルを作成：

```json
{
  "name": "佐藤花子",
  "email": "sato@example.com",
  "message": "AWS CLI経由でのテスト実行です。",
  "client_ip": "198.51.100.20"
}
```

#### 2. Lambda関数の実行

```bash
aws lambda invoke \
  --function-name <lambda-function-name> \
  --payload file://test-event.json \
  --region ap-northeast-1 \
  response.json
```

#### 3. レスポンスの確認

```bash
cat response.json | jq .
```

### 方法3: API Gateway経由でテスト（API Gatewayがある場合）

API GatewayとLambda関数を統合している場合、以下のようにテストできます：

```bash
# API Gatewayのエンドポイント
API_ENDPOINT="https://xxxxxxxxxx.execute-api.ap-northeast-1.amazonaws.com/prod/inquiry"

# リクエスト送信
curl -X POST ${API_ENDPOINT} \
  -H "Content-Type: application/json" \
  -d '{
    "name": "鈴木一郎",
    "email": "suzuki@example.com",
    "message": "API Gateway経由でのテストです。",
    "client_ip": "192.0.2.100"
  }'
```

## RDSでのデータ確認

### MySQLクライアントで確認

```sql
-- データベースを選択
USE appdb;

-- 全レコードを確認
SELECT * FROM inquiries ORDER BY created_at DESC;

-- 特定のレコードを確認
SELECT * FROM inquiries WHERE id = 1;

-- レコード数の確認
SELECT COUNT(*) FROM inquiries;
```

### AWS CLIで確認（RDS Data APIを使用している場合）

RDS Data APIを使用している場合は、以下のように確認できます：

```bash
aws rds-data execute-statement \
  --resource-arn <cluster-arn> \
  --secret-arn <secret-arn> \
  --database appdb \
  --sql "SELECT * FROM inquiries ORDER BY created_at DESC LIMIT 10"
```

## エラーケースのテスト

### 必須パラメータ不足の場合

```json
{
  "name": "テストユーザー",
  "email": "test@example.com"
  // messageがない
}
```

**期待されるレスポンス**:
```json
{
  "statusCode": 400,
  "body": "{\"error\": \"name,email,message are required\"}"
}
```

### 無効なデータの場合

```json
{
  "name": "",
  "email": "invalid-email",
  "message": "テスト",
  "client_ip": "203.0.113.10"
}
```

**期待される動作**:
- `name` が空の場合は400エラーになる可能性があります
- 実際の動作は実装によります

## トラブルシューティング

### Lambda関数がタイムアウトする

- CloudWatch Logsでタイムアウト前にどの処理で止まっているか確認
- Lambda関数のタイムアウト設定を延長（デフォルト3秒から30秒以上推奨）

### Secrets Managerからシークレットを取得できない

**CloudWatch Logsでのエラーメッセージ例**:
```
ERROR: Failed to connect to RDS: An error occurred (AccessDen心胸Exception) when calling the GetSecretValue operation
```

**対処方法**:
- Lambda関数のIAMロールに `secretsmanager:GetSecretValue` 権限があるか確認

### RDSに接続できない

**CloudWatch Logsでのエラーメッセージ例**:
```
ERROR: Failed to connect to RDS: (2003, "Can't connect to MySQL server on 'xxx.rds.amazonaws.com' (timed out)")
```

**対処方法**:
- RDSエンドポイント名が正しいか確認
- セキュリティグループでLambdaからRDS（3306/TCP）への通信が許可されているか確認
- Secrets Managerのシークレット内容（host、port）が正しいか確認

### データベース接続エラー

**CloudWatch Logsでのエラーメッセージ例**:
```
ERROR: Failed to insert record: (1045, "Access denied for user 'appuser'@'xxx' (using password: YES)")
```

**対処方法**:
- Secrets Managerのシークレット内容（username、password、dbname）が正しいか確認
- RDSでユーザーが正しく作成され、権限が付与されているか確認

### INSERTエラー

**CloudWatch Logsでのエラーメッセージ例**:
```
ERROR: Failed to insert record: (1146, "Table 'appdb.inquiries' doesn't exist")
```

**対処方法**:
- テーブルが正しく作成されているか確認（[テーブル作成手順](./DATABASE_SETUP.md)参照）
- Secrets Managerのシークレット内容（dbname）が正しいか確認

## 成功条件の確認

以下のすべてが満たされていることを確認してください：

- [ ] Lambda関数の実行が成功（statusCode: 200）
- [ ] CloudWatch Logsに `SUCCESS` ログが出力されている
- [ ] RDSの `inquiries` テーブルにレコードが追加されている
- [ ] エラーログが出力されていない
- [ ] NAT/IGWなしで実行できている（VPCエンドポイント経由）

## 負荷テスト（オプション）

複数のリクエストを同時に送信して、Lambda関数の動作を確認することもできます：

```bash
# 10個のリクエストを同時に送信
for i in {1..10}; do
  aws lambda invoke \
    --function-name <lambda-function-name> \
    --payload "{\"name\":\"テスト${i}\",\"email\":\"test${i}@example.com\",\"message\":\"テストメッセージ${i}\",\"client_ip\":\"203.0.113.${i}\"}" \
    --region ap-northeast-1 \
    "response-${i}.json" &
done
wait

# すべてのレスポンスを確認
cat response-*.json | jq .
```

## クリーンアップ

テストが完了したら、必要に応じてテストデータを削除してください：

```sql
-- テストデータの削除（注意: 本番データも削除される可能性があります）
DELETE FROM inquiries WHERE email LIKE '%@example.com';
```
