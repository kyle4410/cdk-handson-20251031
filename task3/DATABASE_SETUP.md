# データベーステーブル作成手順

このドキュメントでは、RDS MySQLインスタンスに `inquiries` テーブルを作成する手順を説明します。

## 前提条件

- RDS MySQLインスタンスが作成済みであること
- RDSインスタンスへの接続方法があること

## テーブル設計

### テーブル名

`inquiries`

### カラム定義

| カラム名 | 型 | 制約 | 説明 |
|---------|-----|------|------|
| id | BIGINT | PRIMARY KEY, AUTO_INCREMENT | レコードID |
| name | VARCHAR(100) | NOT NULL | 名前 |
| email | VARCHAR(255) | NOT NULL | メールアドレス |
| message | TEXT | NOT NULL | メッセージ内容 |
| client_ip | VARCHAR(45) | NULL | クライアントIPアドレス（IPv4/IPv6対応） |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | 作成日時 |

### インデックス

- PRIMARY KEY: `id`
- INDEX: `idx_created_at (created_at)`


## データベースとユーザーの作成

RDSインスタンス作成時にデータベースとユーザーを作成していない場合、以下の手順で作成してください。

```sql
-- データベースの作成
CREATE DATABASE IF NOT EXISTS appdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- ユーザーの作成（必要に応じて）
CREATE USER IF NOT EXISTS 'appuser'@'%' IDENTIFIED BY 'your-password';

-- 権限の付与
GRANT ALL PRIVILEGES ON appdb.* TO 'appuser'@'%';

-- 権限の反映
FLUSH PRIVILEGES;
```

## テーブル作成

### SQL実行

RDSに接続後、以下のSQLを実行してください：

```sql
-- データベースを選択
USE appdb;

-- テーブルの作成
CREATE TABLE IF NOT EXISTS inquiries (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(255) NOT NULL,
  message TEXT NOT NULL,
  client_ip VARCHAR(45) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='お問い合わせフォームテーブル';
```

### テーブル作成の確認

```sql
-- テーブル一覧の確認
SHOW TABLES;

-- テーブル構造の確認
DESCRIBE inquiries;

-- インデックスの確認
SHOW INDEX FROM inquiries;
```

### 実行結果の例

```sql
mysql> DESCRIBE inquiries;
+------------+--------------+------+-----+-------------------+-------------------+
| Field      | Type         | Null | Key | Default           | Extra             |
+------------+--------------+------+-----+-------------------+-------------------+
| id         | bigint       | NO   | PRI | NULL              | auto_increment    |
| name       | varchar(100) | NO   |     | NULL              |                   |
| email      | varchar(255) | NO   |     | NULL              |                   |
| message    | text         | NO   |     | NULL              |                   |
| client_ip  | varchar(45)  | YES  |     | NULL              |                   |
| created_at | timestamp    | NO   |     | CURRENT_TIMESTAMP | DEFAULT_GENERATED |
+------------+--------------+------+-----+-------------------+-------------------+
6 rows in set (0.01 sec)
```

## テストデータの挿入（オプション）

動作確認のためにテストデータを挿入することもできます：

```sql
-- テストデータの挿入
INSERT INTO inquiries(name,email,message,client_ip)
VALUES
  ('テスト太郎', 'test1@example.com', 'これはテストメッセージです', '192.0.2.1'),
  ('テスト花子', 'test2@example.com', 'もう一つのテストメッセージ', '198.51.100.2');

-- 挿入されたデータの確認
SELECT * FROM inquiries;
```

## トラブルシューティング

### 権限エラー

- ユーザーに適切な権限が付与されているか確認
- `FLUSH PRIVILEGES;` を実行したか確認

### テーブル作成エラー

- データベースが存在するか確認（`USE appdb;` で選択）
- 既存のテーブルと名前が衝突していないか確認
- エラーメッセージを確認（文字セット、エンジンなど）

## 次のステップ

テーブル作成が完了したら、以下の手順に進んでください：

1. Secrets Managerに認証情報を登録（README参照）
2. Lambda関数をデプロイ
3. Lambda関数をテスト（[Lambda関数テスト手順](./LAMBDA_TEST.md)参照）

