# CDKハンズオン - 受講者向けガイド

このリポジトリは、AWS CDKを使用したインフラ構築のハンズオン用リポジトリです。3人チームでそれぞれ異なるお題に取り組む形式で実施します。

## 全体注意事項

* **使用リージョン**: **ap-northeast-1 (Tokyo)** を推奨（別リージョンでも可。ただし③のマルチAZ要件は維持）
* **AWSアカウント**: 基本は各自の AWS アカウントで実施。費用が発生します。終了後は **必ず削除** してください
* **構築方法**: CDKで構築してください
* **タグ付け**: すべての課題で **タグ**（例: `Project=HandsOn`, `Team=A|B|C`, `Owner=<yourname>`）を付けること

## ハンズオンの進め方

### 1. 事前準備

1. [AWS CLI設定手順](./AWS_CLI_SETUP.md) を参照して、AWS CLIとSSOプロファイルを設定してください
2. CDKの環境をセットアップしてください（Node.js、CDK CLIのインストール）
3. このリポジトリをクローンまたはダウンロードしてください

### 2. チーム内での役割分担

チーム内で3つのタスクを分担してください：

- **タスク1**: ALB + AutoScaling + EC2 で Web サーバ構築
- **タスク2**: CloudWatch Logs → Firehose(5分バッファ) → S3 → Lambda 事前処理
- **タスク3**: VPC 内 Lambda から Secrets Manager 経由で RDS に登録

### 3. 各タスクの実施

各タスクのフォルダを開き、READMEを参照しながらCDKでインフラを構築してください：

- [タスク1: ALB + AutoScaling + EC2](./task1/README.md)
- [タスク2: CloudWatch Logs → Firehose → S3 → Lambda](./task2/README.md)
- [タスク3: VPC内Lambda → Secrets Manager → RDS](./task3/README.md)

## タスク一覧

### タスク1: ALB + AutoScaling + EC2 で Web サーバ構築

**難易度**: 初級

簡易ステータスページを作成します。リクエストを受けた **ALB** が背後の **EC2 Auto Scaling** へルーティングし、各 **EC2 が自身のインスタンスIDを返す**ことで、トラフィック分散とスケール挙動を可視化します。

**主な学習内容**:
- CDKを使用したALB、Target Group、Auto Scaling Groupの構築
- EC2インスタンスのユーザーデータでの初期化
- ヘルスチェックの設定と動作確認
- スケーリング挙動の理解

[詳細はこちら](./task1/README.md)

### タスク2: CloudWatch Logs → Firehose(5分バッファ) → S3 → Lambda 事前処理

**難易度**: 中級

**CloudWatch Logs** に継続出力される **アクセスログ（Common Log Format 互換）** を、**Kinesis Data Firehose** で **5分毎にバルク出力**して **S3** に蓄積。到着トリガーで **Lambda** がログを**パース・正規化・日次集計キー付与**までを行い、**後続の分析基盤**が取り込みやすい JSON に整形します。

**主な学習内容**:
- CloudWatch Logs Subscription Filterの設定
- Kinesis Data Firehoseの設定と動作確認
- S3イベントトリガーによるLambda実行
- ログパース処理の実装
- データパイプラインの構築

[詳細はこちら](./task2/README.md)

### タスク3: VPC 内 Lambda から Secrets Manager 経由で RDS に登録

**難易度**: 上級

お問い合わせフォーム（フロントは省略）の送信情報を **Lambda** が受け取り、**Secrets Manager** に保管された DB 資格情報を用いて **RDS（MySQL/Aurora MySQL）** に **プライベート接続で INSERT** します。RDS は **プライベートサブネット**に配置し、**NAT/IGW なし**（インターネット非到達）。必要な AWS API には **VPC エンドポイント**経由で到達します。

**主な学習内容**:
- VPC内でのLambda実行
- Secrets Managerを使用したデータベース認証情報の管理
- VPCエンドポイントを使用したプライベート接続
- インターネット非到達環境でのLambda実行
- RDSへのプライベート接続

[詳細はこちら](./task3/README.md)

## CDKの基本コマンド

各タスクのフォルダで以下のコマンドを使用します：

```bash
# 依存関係のインストール（初回のみ）
npm install

# CDKの初期化（既に初期化済みの場合は不要）
cdk init app --language typescript

# 型定義の確認
npm run build

# デプロイ前の確認（変更内容を表示）
cdk diff

# デプロイ
cdk deploy

# すべてのスタックをデプロイ
cdk deploy --all

# スタックの削除
cdk destroy

# すべてのスタックを削除
cdk destroy --all
```

## 共通のヒント

### スタック分割

複数のスタックに分割することで、管理しやすくなります。例えば：

- **タスク1**: `NetworkStack`, `AlbAsgStack`
- **タスク2**: `LogIngestStack`（Logs→Firehose→S3）, `EtlLambdaStack`
- **タスク3**: `VpcRdsStack`, `LambdaAppStack`, `VpcEndpointStack`

### 検証方法

- **CloudWatch Logs**: Lambda関数の実行ログやEC2のログを確認
- **ALBアクセス**: ブラウザやcurlでALBのDNS名にアクセス
- **S3出力**: S3バケットにファイルが作成されているか確認
- **RDSの実データ**: MySQLクライアントでデータを確認

### トラブルシューティング

- **CloudWatch Logs**でエラーメッセージを確認
- **セキュリティグループ**の設定を確認（必要な通信が許可されているか）
- **IAMロール**の権限を確認
- **VPCエンドポイント**が正しく設定されているか確認（タスク3）

## クリーンアップ

**重要**: ハンズオン終了後、すべてのリソースを削除してください。費用が発生します。

### 削除手順

1. 各タスクのCDKスタックを削除:
   ```bash
   # 各タスクのフォルダで実行
   cdk destroy --all
   ```

2. タスク2で作成したCloudFormationスタックを削除（該当する場合）:
   ```bash
   # task2フォルダで実行
   ./deploy-log-generator.sh destroy
   # または Windows の場合
   .\deploy-log-generator.ps1 -Action destroy
   ```

3. 手動で作成したリソースを確認・削除:
   - Secrets Managerのシークレット
   - RDSスナップショット（自動スナップショットが作成されている場合）
   - S3バケット内のデータ（バケット自体はCDKで削除される場合があります）

### コスト確認

削除後、AWSコンソールで請求ダッシュボードを確認し、予期しない課金がないか確認してください。

## 参考資料

- [AWS CDK公式ドキュメント](https://docs.aws.amazon.com/cdk/)
- [AWS CDK APIリファレンス](https://docs.aws.amazon.com/cdk/api/v2/)
- [AWS CLI設定手順](./AWS_CLI_SETUP.md)

## サポート

質問や問題が発生した場合は、以下の順序で確認してください：

1. 各タスクのREADMEの「トラブルシューティング」セクションを確認
2. CloudWatch Logsでエラーログを確認
3. インストラクターに質問

## 競技ルール（任意）

チームで競う場合のルール例：

- ①の安定稼働→②の structured 出力確認→③の VPC 内成功の順にクリアで加点
- 完成までの時間で順位を決定
- 追加課題をクリアするとボーナス点

## ライセンス

このリポジトリはハンズオン用です。自由にご利用ください。

