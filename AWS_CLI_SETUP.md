# AWS CLI設定手順（SSOとプロファイル構成）

このドキュメントでは、AWS CLIを使用してSSO（Single Sign-On）でAWSアカウントにアクセスするための設定手順を説明します。

## 前提条件

- AWS CLI v2がインストールされていること
- AWS SSOにアクセスできること（SSOのURL、リージョン、アカウント情報を管理者から取得）

## ステップ1: AWS CLIのインストール確認

### Windows

```powershell
aws --version
```

インストールされていない場合:
1. [AWS CLI v2インストーラー](https://awscli.amazonaws.com/AWSCLIV2.msi)をダウンロード
2. インストーラーを実行してインストール

### macOS

```bash
aws --version
```

インストールされていない場合:
```bash
# Homebrewを使用
brew install awscli
```

### Linux

```bash
aws --version
```

インストールされていない場合:
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

## ステップ2: SSOの設定

### 初回設定

1. AWS CLIでSSOログインを開始:

```bash
aws configure sso
```

2. プロンプトに従って入力:

```
SSO session name (Recommended): hands-on-session
SSO start URL: https://<your-sso-portal>.awsapps.com/start
SSO region: ap-northeast-1
SSO registration scopes (Recommended): sso:account:access
```

3. ブラウザが開きます。AWS SSOにログインしてください

4. プロンプトが続きます:

```
CLI client id (Recommended): <自動生成されるID>
CLI client secret: <自動生成されるシークレット>
CLI region [None]: ap-northeast-1
CLI default output format [None]: json
CLI profile name [hands-on-session]: hands-on-profile
```

5. アカウントとロールを選択:

```
CLI sso account id [None]: <アカウントID>
CLI sso role name [None]: <ロール名（例: AdministratorAccess, PowerUserAccess）>
CLI default region [None]: ap-northeast-1
CLI default output format [None]: json
```

### 設定ファイルの確認

設定は `~/.aws/config` に保存されます：

```ini
[profile hands-on-profile]
sso_session = hands-on-session
sso_account_id = <アカウントID>
sso_role_name = <ロール名>
region = ap-northeast-1
output = json

[sso-session hands-on-session]
sso_start_url = https://<your-sso-portal>.awsapps.com/start
sso_region = ap-northeast-1
sso_registration_scopes = sso:account:access
```

## ステップ3: SSOログイン

### 初回ログイン

```bash
aws sso login --profile hands-on-profile
```

または

```bash
aws sso login
```

ブラウザが開き、AWS SSOにログインするよう求められます。ログインが完了すると、CLIでAWSアカウントにアクセスできるようになります。

### 複数プロファイルがある場合

```bash
aws sso login --profile <profile-name>
```

## ステップ4: 動作確認

### 基本的なコマンドで確認

```bash
# プロファイルを指定して実行
aws sts get-caller-identity --profile hands-on-profile

# 環境変数でプロファイルを設定
export AWS_PROFILE=hands-on-profile
aws sts get-caller-identity

# Windows PowerShellの場合
$env:AWS_PROFILE="hands-on-profile"
aws sts get-caller-identity
```

### CDKで使用する場合

CDKは `AWS_PROFILE` 環境変数を参照します：

```bash
# Linux/macOS
export AWS_PROFILE=hands-on-profile
cdk deploy

# Windows PowerShell
$env:AWS_PROFILE="hands-on-profile"
cdk deploy

# Windows CMD
set AWS_PROFILE=hands-on-profile
cdk deploy
```

## ステップ5: 複数プロファイルの管理（オプション）

複数のAWSアカウントや環境を使用する場合は、複数のプロファイルを作成できます。

### 追加プロファイルの設定

```bash
aws configure sso --profile hands-on-profile-dev
```

または、`~/.aws/config` を直接編集：

```ini
[profile hands-on-profile-dev]
sso_session = hands-on-session
sso_account_id = <開発アカウントID>
sso_role_name = <ロール名>
region = ap-northeast-1
output = json

[profile hands-on-profile-prod]
sso_session = hands-on-session
sso_account_id = <本番アカウントID>
sso_role_name = <ロール名>
region = ap-northeast-1
output = json
```

### プロファイルの切り替え

```bash
# 環境変数で切り替え
export AWS_PROFILE=hands-on-profile-dev

# またはコマンドでプロファイルを指定
aws s3 ls --profile hands-on-profile-dev
```

## トラブルシューティング

### SSOセッションが期限切れ

SSOセッションは一定時間（通常8時間）で期限切れになります。再度ログインしてください：

```bash
aws sso login --profile hands-on-profile
```

### プロファイルが見つからない

`~/.aws/config` ファイルを確認してください：

```bash
# Linux/macOS
cat ~/.aws/config

# Windows
type %USERPROFILE%\.aws\config
```

### アクセス権限エラー

以下のエラーが発生する場合、ロールに適切な権限がない可能性があります：

```
AccessDenied: User: arn:aws:sts::... is not authorized to perform: ...
```

**対処方法**:
- AWS SSO管理者に適切な権限が付与されているか確認
- 使用しているロールが適切か確認

### リージョンの不一致

エラーが発生する場合、リージョン設定を確認してください：

```bash
# 現在のリージョンを確認
aws configure get region --profile hands-on-profile

# リージョンを設定
aws configure set region ap-northeast-1 --profile hands-on-profile
```

### CDKでプロファイルが認識されない

環境変数が設定されているか確認：

```bash
# Linux/macOS
echo $AWS_PROFILE

# Windows PowerShell
echo $env:AWS_PROFILE

# Windows CMD
echo %AWS_PROFILE%
```

環境変数が設定されていない場合、設定してください：

```bash
# Linux/macOS
export AWS_PROFILE=hands-on-profile

# Windows PowerShell
$env:AWS_PROFILE="hands-on-profile"

# Windows CMD
set AWS_PROFILE=hands-on-profile
```

## セキュリティのベストプラクティス

1. **SSOセッションの管理**: 作業終了後は、必要に応じてセッションを無効化してください
2. **最小権限の原則**: 必要な最小限の権限のみを要求するロールを使用してください
3. **認証情報の保護**: `~/.aws/config` ファイルには機密情報が含まれる可能性があるため、適切に保護してください（ファイル権限: 600）

```bash
# Linux/macOS
chmod 600 ~/.aws/config

# Windows
# ファイルのプロパティで保護設定
```

## 参考資料

- [AWS CLI v2 ユーザーガイド - SSO](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html)
- [AWS SSO ユーザーガイド](https://docs.aws.amazon.com/singlesignon/latest/userguide/)
- [CDK ドキュメント - 環境変数](https://docs.aws.amazon.com/cdk/v2/guide/environments.html)

## よくある質問（FAQ）

### Q: SSOログインが毎回必要ですか？

A: SSOセッションは一定時間（通常8時間）有効です。期限切れになると再度ログインが必要です。

### Q: 複数のAWSアカウントを使い分けたい

A: 複数のプロファイルを作成し、`AWS_PROFILE` 環境変数で切り替えてください。

### Q: ローカル開発環境でもSSOを使えますか？

A: はい、`aws configure sso` で設定すればローカル環境でもSSOを使用できます。

### Q: CDKはSSOプロファイルを自動的に認識しますか？

A: はい、`AWS_PROFILE` 環境変数が設定されていれば自動的に認識します。

