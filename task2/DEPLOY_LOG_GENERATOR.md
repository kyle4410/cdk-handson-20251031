# CloudFormationデプロイ手順（ログ生成環境）

このドキュメントでは、CloudWatch Logsにログを出力するためのEventBridge + Lambda環境をCloudFormationでデプロイする手順を説明します。

## 前提条件

- AWS CLIがインストールされ、設定されていること
- 適切なIAM権限があること（CloudFormation、Lambda、EventBridge、CloudWatch Logsの作成権限）
- リージョン: **ap-northeast-1 (Tokyo)** を推奨

## デプロイ手順

### Linux/Mac

```bash
# デプロイ実行
aws cloudformation deploy \
  --template-file setup-log-generator.yaml \
  --stack-name hands-on-log-generator \
  --capabilities CAPABILITY_NAMED_IAM \
  --region ap-northeast-1 \
  --tags Project=HandsOn Component=LogGenerator

# 出力の確認
aws cloudformation describe-stacks \
  --stack-name hands-on-log-generator \
  --region ap-northeast-1 \
  --query 'Stacks[0].Outputs'
```

### Windows (PowerShell)

```powershell
# デプロイ実行
aws cloudformation deploy `
  --template-file setup-log-generator.yaml `
  --stack-name hands-on-log-generator `
  --capabilities CAPABILITY_NAMED_IAM `
  --region ap-northeast-1 `
  --tags Project=HandsOn Component=LogGenerator

# 出力の確認
aws cloudformation describe-stacks `
  --stack-name hands-on-log-generator `
  --region ap-northeast-1 `
  --query 'Stacks[0].Outputs'
```

### Windows (CMD)

```cmd
# デプロイ実行
aws cloudformation deploy ^
  --template-file setup-log-generator.yaml ^
  --stack-name hands-on-log-generator ^
  --capabilities CAPABILITY_NAMED_IAM ^
  --region ap-northeast-1 ^
  --tags Project=HandsOn Component=LogGenerator

# 出力の確認
aws cloudformation describe-stacks ^
  --stack-name hands-on-log-generator ^
  --region ap-northeast-1 ^
  --query 'Stacks[0].Outputs'
```

## 作成されるリソース

以下のリソースが作成されます：

1. **CloudWatch Logsグループ**: `/aws/access-logs/app-access-logs`
   - ログの保持期間: 7日
   - アクセスログを保存するための専用ロググループ

2. **CloudWatch Logsストリーム**: `app-instance-001`
   - 固定のインスタンスID形式のログストリーム
   - すべてのアクセスログがこのストリームに出力されます

3. **Lambda関数**: `hands-on-log-generator-log-generator`
   - ランタイム: Python 3.12
   - 5分ごとにCLF形式のログをCloudWatch Logs API経由で指定ロググループに直接出力
   - Lambda関数の実行ログは `/aws/lambda/hands-on-log-generator-log-generator` に出力されます

4. **EventBridgeルール**: `hands-on-log-generator-log-generator-schedule`
   - スケジュール: 3分ごと（デフォルト）
   - Lambda関数を自動トリガー

5. **IAMロール**: `hands-on-log-generator-log-generator-lambda-role`
   - CloudWatch Logsへの書き込み権限

## 動作確認

### 1. CloudWatch Logsの確認

```bash
# アクセスログのロググループを確認
aws logs describe-log-groups \
  --log-group-name-prefix "/aws/access-logs/app-access-logs" \
  --region ap-northeast-1

# アクセスログのログストリームを確認
aws logs describe-log-streams \
  --log-group-name "/aws/access-logs/app-access-logs" \
  --log-stream-name-prefix app-instance-001 \
  --region ap-northeast-1 \
  --order-by LastEventTime \
  --descending \
  --max-items 5

# 最新のアクセスログを確認
aws logs tail /aws/access-logs/app-access-logs \
  --log-stream-names app-instance-001 \
  --follow \
  --region ap-northeast-1

# Lambda関数の実行ログを確認（エラー確認用）
aws logs tail /aws/lambda/hands-on-log-generator-log-generator \
  --follow \
  --region ap-northeast-1
```

### 2. Lambda関数の実行確認

```bash
# Lambda関数の実行履歴を確認
aws lambda list-functions \
  --region ap-northeast-1 \
  --query 'Functions[?contains(FunctionName, `log-generator`)].FunctionName'

# Lambda関数のメトリクスを確認
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=hands-on-log-generator-log-generator \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --region ap-northeast-1
```

## パラメータのカスタマイズ

`setup-log-generator.yaml`の以下のパラメータを変更できます：

- **LogGroupName**: CloudWatch Logsグループ名（デフォルト: `/aws/access-logs/app-access-logs`）
- **LogStreamName**: CloudWatch Logsストリーム名（デフォルト: `app-instance-001`）
- **ScheduleExpression**: EventBridgeのスケジュール表現（デフォルト: `rate(3 minutes)`）

変更する場合は、デプロイ時にパラメータを指定：

```bash
aws cloudformation deploy \
  --template-file setup-log-generator.yaml \
  --stack-name hands-on-log-generator \
  --capabilities CAPABILITY_NAMED_IAM \
  --region ap-northeast-1 \
  --parameter-overrides \
    LogGroupName="/custom/log-group" \
    LogStreamName="custom-instance-001" \
    ScheduleExpression="rate(1 minutes)"
```

## 削除手順

### Linux/Mac

```bash
# スタックの削除
aws cloudformation delete-stack \
  --stack-name hands-on-log-generator \
  --region ap-northeast-1

# 削除状態の確認
aws cloudformation describe-stacks \
  --stack-name hands-on-log-generator \
  --region ap-northeast-1
```

### Windows (PowerShell)

```powershell
# スタックの削除
aws cloudformation delete-stack `
  --stack-name hands-on-log-generator `
  --region ap-northeast-1

# 削除状態の確認
aws cloudformation describe-stacks `
  --stack-name hands-on-log-generator `
  --region ap-northeast-1
```

### Windows (CMD)

```cmd
# スタックの削除
aws cloudformation delete-stack ^
  --stack-name hands-on-log-generator ^
  --region ap-northeast-1

# 削除状態の確認
aws cloudformation describe-stacks ^
  --stack-name hands-on-log-generator ^
  --region ap-northeast-1
```

## トラブルシューティング

### CloudFormationスタックがCREATE_FAILEDになる

- IAM権限が不足していないか確認
- スタックのイベントを確認:
  ```bash
  aws cloudformation describe-stack-events \
    --stack-name hands-on-log-generator \
    --region ap-northeast-1 \
    --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`]'
  ```

### Lambda関数が実行されない

- EventBridgeルールが有効になっているか確認
- Lambda関数の実行ログを確認
- IAMロールの権限を確認

### ログが出力されない

- CloudWatch Logsグループが作成されているか確認
- Lambda関数の実行ログ（`/aws/lambda/hands-on-log-generator-log-generator`）を確認
- EventBridgeのスケジュールが正しく設定されているか確認
- Lambda関数のIAMロールにCloudWatch Logsへの書き込み権限があるか確認
- 環境変数（LOG_GROUP_NAME、LOG_STREAM_NAME）が正しく設定されているか確認

## 注意事項

- この環境は3分ごとにLambda関数を実行します。コストに注意してください
- ハンズオン終了後は必ずスタックを削除してください
- CloudWatch Logsの保持期間は7日に設定されていますが、必要に応じて調整してください

