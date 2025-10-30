# CloudFormationデプロイ手順（ログ生成環境）

このドキュメントでは、CloudWatch Logsにログを出力するためのEventBridge + Lambda環境をCloudFormationでデプロイする手順を説明します。

## 前提条件

- AWS CLIがインストールされ、設定されていること
- 適切なIAM権限があること（CloudFormation、Lambda、EventBridge、CloudWatch Logsの作成権限）
- リージョン: **ap-northeast-1 (Tokyo)** を推奨

## デプロイ手順

### 方法1: AWS CLIを使用（推奨）

#### Linux/Mac

```bash
# スタック名を指定（任意）
STACK_NAME="hands-on-log-generator"

# デプロイ実行
aws cloudformation deploy \
  --template-file setup-log-generator.yaml \
  --stack-name ${STACK_NAME} \
  --capabilities CAPABILITY_NAMED_IAM \
  --region ap-northeast-1 \
  --tags Project=HandsOn Component=LogGenerator

# 出力の確認
aws cloudformation describe-stacks \
  --stack-name ${STACK_NAME} \
  --region ap-northeast-1 \
  --query 'Stacks[0].Outputs'
```

#### Windows (PowerShell)

```powershell
# スタック名を指定
$STACK_NAME = "hands-on-log-generator"

# デプロイ実行
aws cloudformation deploy `
  --template-file setup-log-generator.yaml `
  --stack-name $STACK_NAME `
  --capabilities CAPABILITY_NAMED_IAM `
  --region ap-northeast-1 `
  --tags Project=HandsOn Component=LogGenerator

# 出力の確認
aws cloudformation describe-stacks `
  --stack-name $STACK_NAME `
  --region ap-northeast-1 `
  --query 'Stacks[0].Outputs'
```

### 方法2: スクリプトを使用

#### Linux/Mac

```bash
chmod +x deploy-log-generator.sh
./deploy-log-generator.sh
```

#### Windows

```powershell
.\deploy-log-generator.ps1
```

## 作成されるリソース

以下のリソースが作成されます：

1. **CloudWatch Logsグループ**: `/aws/lambda/log-generator`
   - ログの保持期間: 7日

2. **Lambda関数**: `hands-on-log-generator-log-generator`
   - ランタイム: Python 3.12
   - 5分ごとにCLF形式のログをCloudWatch Logsに出力

3. **EventBridgeルール**: `hands-on-log-generator-log-generator-schedule`
   - スケジュール: 5分ごと（デフォルト）
   - Lambda関数を自動トリガー

4. **IAMロール**: `hands-on-log-generator-log-generator-lambda-role`
   - CloudWatch Logsへの書き込み権限

## 動作確認

### 1. CloudWatch Logsの確認

```bash
# ロググループを確認
aws logs describe-log-groups \
  --log-group-name-prefix "/aws/lambda/log-generator" \
  --region ap-northeast-1

# ログストリームを確認
aws logs describe-log-streams \
  --log-group-name "/aws/lambda/log-generator" \
  --region ap-northeast-1 \
  --order-by LastEventTime \
  --descending \
  --max-items 5

# 最新のログを確認
aws logs tail /aws/lambda/log-generator \
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

- **LogGroupName**: CloudWatch Logsグループ名（デフォルト: `/aws/lambda/log-generator`）
- **ScheduleExpression**: EventBridgeのスケジュール表現（デフォルト: `rate(5 minutes)`）

変更する場合は、デプロイ時にパラメータを指定：

```bash
aws cloudformation deploy \
  --template-file setup-log-generator.yaml \
  --stack-name ${STACK_NAME} \
  --capabilities CAPABILITY_NAMED_IAM \
  --region ap-northeast-1 \
  --parameter-overrides \
    LogGroupName="/custom/log-group" \
    ScheduleExpression="rate(10 minutes)"
```

## 削除手順

### AWS CLIを使用

```bash
# スタックの削除
aws cloudformation delete-stack \
  --stack-name ${STACK_NAME} \
  --region ap-northeast-1

# 削除状態の確認
aws cloudformation describe-stacks \
  --stack-name ${STACK_NAME} \
  --region ap-northeast-1
```

### スクリプトを使用

#### Linux/Mac

```bash
./deploy-log-generator.sh destroy
```

#### Windows

```powershell
.\deploy-log-generator.ps1 -Action destroy
```

## トラブルシューティング

### CloudFormationスタックがCREATE_FAILEDになる

- IAM権限が不足していないか確認
- スタックのイベントを確認:
  ```bash
  aws cloudformation describe-stack-events \
    --stack-name ${STACK_NAME} \
    --region ap-northeast-1 \
    --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`]'
  ```

### Lambda関数が実行されない

- EventBridgeルールが有効になっているか確認
- Lambda関数の実行ログを確認
- IAMロールの権限を確認

### ログが出力されない

- CloudWatch Logsグループが作成されているか確認
- Lambda関数の実行ログを確認
- EventBridgeのスケジュールが正しく設定されているか確認

## 注意事項

- この環境は5分ごとにLambda関数を実行します。コストに注意してください
- ハンズオン終了後は必ずスタックを削除してください
- CloudWatch Logsの保持期間は7日に設定されていますが、必要に応じて調整してください

