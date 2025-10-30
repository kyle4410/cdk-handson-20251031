# タスク3: VPC 内 Lambda から Secrets Manager 経由で RDS に登録

## 概要

お問い合わせフォーム（フロントは省略）の送信情報を **Lambda** が受け取り、**Secrets Manager** に保管された DB 資格情報を用いて **RDS（MySQL/Aurora MySQL）** に **プライベート接続で INSERT** します。RDS は **プライベートサブネット**に配置し、**NAT/IGW なし**（インターネット非到達）。必要な AWS API には **VPC エンドポイント**経由で到達します。

## 学習目標

- VPC内でのLambda実行
- Secrets Managerを使用したデータベース認証情報の管理
- VPCエンドポイントを使用したプライベート接続
- インターネット非到達環境でのLambda実行
- RDSへのプライベート接続

## 要件定義

### 基本要件

* VPC（2 つ以上の AZ）。**プライベートサブネットのみで RDS** を作成
* **Lambda を VPC 内で実行**（プライベートサブネットに ENI 付与）
* **インターネットに出さない**（NAT/IGW なし）
* **Secrets Manager** に `db-credentials` シークレットを作成（JSON）
* **VPC エンドポイント**（Interface）: `com.amazonaws.<region>.secretsmanager`, `logs`, `kms`（KMS を使う場合）。必要に応じて `ec2`、`lambda` も。S3 に触れる場合は **Gateway エンドポイント (S3)**
* セキュリティグループ: Lambda → RDS の 3306/TCP を許可。最小権限

### 構成図

```mermaid
flowchart LR
  Client((Form/Caller)) --> Lmb[Lambda (in VPC)]
  Lmb --- VPCE1[(VPCE: Secrets Manager)]
  Lmb --- VPCE2[(VPCE: Logs)]
  Lmb -->|3306| RDS[(RDS MySQL/Aurora)\nPrivate Subnets]
  Lmb -.->|GetSecret| Sec[Secrets Manager]
```

## 事前準備

### 1. データベーステーブルの作成

RDSインスタンス作成後、データベースに接続してテーブルを作成する必要があります。

詳細な手順は [テーブル作成手順](./DATABASE_SETUP.md) を参照してください。

### 2. Secrets Managerへのシークレット登録

RDSインスタンス作成後、以下の形式でシークレットを登録してください：

```json
{
  "engine": "mysql",
  "host": "<rds-endpoint>",
  "port": 3306,
  "username": "appuser",
  "password": "<your-password>",
  "dbname": "appdb"
}
```

**重要**: シークレット名は `db-credentials` としてください（またはLambda関数の環境変数で指定）。

### 3. 必要なファイル

- `lambda/rds-insert-handler.py`: RDSにINSERTするLambda関数
- `DATABASE_SETUP.md`: テーブル作成手順
- `LAMBDA_TEST.md`: Lambda関数のテスト手順

## 実装のヒント

### 必要なCDKリソース

1. **VPC関連**
   - VPC（2つ以上のAZ）
   - **プライベートサブネットのみ**（RDS稳定）
   - パブリックサブネットなし（IGWなし）
   - **VPCエンドポイント**（Interface）: Secrets Manager、CloudWatch Logs、KMS（必要に応じて）
   - セキュリティグループ（Lambda用、RDS用）

2. **RDS関連**
   - RDS MySQL/Aurora MySQLインスタンス（プライベートサブネット、マルチAZ推奨）
   - データベース名、ユーザー名、パスワード
   - パラメータグループ（必要に応じて）

3. **Secrets Manager**
   - シークレット: `db-credentials`（JSON形式）

4. **Lambda関数**
   - VPC内で実行するLambda関数
   - プライベートサブネットに配置
   - IAMロール（Secrets Manager読み取り、CloudWatch Logs書き込み）
   - 環境変数: `SECRET_ID=db-credentials`

5. **VPCエンドポイント**
   - Secrets Manager（Interface）
   - CloudWatch Logs（Interface）
   - KMS（Interface、暗号化を使用する場合）
   - EC2（Interface、必要に応じて）
   - Lambda（Interface、必要に応じて）
   - S3（Gateway、S3にアクセスする場合）

### スタック設計の提案

以下のようなスタック分割を推奨します：

- `VpcRdsStack`: VPC、プライベートサブネット、RDS、Secrets Manager
- `LambdaAppStack`: Lambda関数、IAMロール、セキュリティグループ
- `VpcEndpointStack`: VPCエンドポイント（Secrets Manager、Logs、KMSなど）

### Lambda関数の実装

RDS INSERT用Lambda関数（`lambda/rds-insert-handler.py`）を参照してください。この関数は：
- Secrets Managerからデータベース認証情報を取得
- PyMySQLを使用してRDSに接続
- リクエストデータを `inquiries` テーブルにINSERT
- 処理の成功/失敗をCloudWatch Logsに出力

### 依存パッケージの管理

Lambda関数でPyMySQLを使用するため、以下のいずれかの方法で依存パッケージを追加する必要があります：

1. **Lambdaレイヤーを使用**（推奨）
2. **デプロイパッケージに同梱**（レイヤーを使用しない場合）

インターネット非到達環境のため、**Lambdaレイヤーやデプロイパッケージは事前に準備**してください。

## 検証手順

### 1. テーブル作成の確認

RDSに接続して `inquiries` テーブルが作成されていることを確認してください。

### 2. Secrets Managerの確認

AWSコンソールまたはCLIでシークレットが正しく作成されていることを確認：

```bash
aws secretsmanager describe-secret --secret-id db-credentials --region ap-northeast-1
```

### 3. VPCエンドポイントの確認

VPCエンドポイントが正しく作成され、利用可能な状態であることを確認：

```bash
aws ec2 describe-vpc-endpoints --region ap-northeast-1
```

### 4. Lambda関数のテスト

詳細なテスト手順は [Lambda関数テスト手順](./LAMBDA_TEST.md) を参照してください。

基本的な流れ：
1. Lambda関数のコンソールでテストイベントを作成
2. テストイベントを実行
3. CloudWatch Logsで実行結果を確認
4. RDSでレコードが挿入されたことを確認

## 成功条件

- [ ] RDS に `inquiries` テーブルが作成済みであること
- [ ] Secrets Managerに `db-credentials` シークレットが作成されていること
- [ ] VPCエンドポイントが正しく動作していること
- [ ] テストイベント実行で Lambda が成功（200）すること
- [ใหม่] RDS にレコードが追加されること
- [ ] Lambda 実行は **NAT/IGW 無し**でも成功すること（＝VPC エンドポイント経由で Secrets 取得・ログ出力できる）

## 制限・注意

* インターネット非到達要件のため、**OS/Lib の外部ダウンロード不可**。依存パッケージはデプロイパッケージに同梱
* RDS は **マルチAZ** を推奨（本番想定の可用性）
* KMS 暗号化を使う場合、**`kms:Decrypt`** と **VPCE for KMS** のエンドポイントポリシーに注意
* Lambda関数がVPC内で実行されるため、**コールドスタート時間が長くなる**可能性があります
* セキュリティグループの設定（Lambda → RDS の 3306/TCP）を忘れないこと

## トラブルシューティング

### Lambda関数がタイムアウトする

- VPCエンドポイントが正しく設定されているか確認
- セキュリティグループで適切な通信が許可されているか確認
- RDSエンドポイント名が正しいか確認
- CloudWatch Logsでエラー内容を確認

### Secrets Managerからシークレットを取得できない

- VPCエンドポイント（Secrets Manager）が作成されているか確認
- VPCエンドポイントのセキュリティグループでLambdaからの通信が許可されているか確認
- Lambda関数のIAMロールに `secretsmanager:GetSecretValue` 権限があるか確認
- エンドポイントポリシーを確認

### RDSに接続できない

- セキュリティグループでLambdaからRDS（3306/TCP）への通信が許可されているか確認
- RDSエンドポイント名とポート番号が正しいか確認
- Secrets Managerのシークレット内容（host、port、username、password、dbname）が正しいか確認
- データベースが正しく作成されているか確認

### CloudWatch Logsに出力されない

- VPCエンドポイント（CloudWatch Logs）が作成されているか確認
- VPCエンドポイントのセキュリティグループでLambdaからの通信が許可されているか確認
- Lambda関数のIAMロールに `logs:CreateLogGroup`、`logs:CreateLogStream`、`logs:PutLogEvents` 権限があるか確認

## クリーンアップ

ハンズオン終了後、作成したスタックを削除してください：

```bash
cdk destroy --all
```

**重要**: 以下のリソースも手動で削除する必要がある場合があります：
- Secrets Managerのシークレット
- RDSスナップショット（自動スナップショットが作成されている場合）

費用が発生するため、必ず削除してください。

## 参考資料

- [テーブル作成手順](./DATABASE_SETUP.md)
- [Lambda関数テスト手順](./LAMBDA_TEST.md)

