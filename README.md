# 分散タスク管理ボット

このDiscordボットは、Supabaseをバックエンドとして利用し、分散型タスク管理機能を提供します。

## 機能概要

- **タスク管理**: ユーザーはタスクの追加、一覧表示、詳細確認、完了、編集、削除が可能です。
- **設定管理**: 管理者権限を持つユーザーは、ボットの基本的な設定を変更できます。
- **永続化**: すべてのタスクデータと設定はSupabaseに安全に保存されます。
- **ヘルスチェック**: `keep_alive.py`によって提供されるFlaskサーバーが、Koyebなどのプラットフォームでのボットの常時稼働をサポートします。

## セットアップ方法

### 1. 必要なもののインストール

Python 3.8以上がインストールされていることを確認してください。

```bash
# 仮想環境の作成とアクティベート (推奨)
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 依存関係のインストール
pip install discord.py flask supabase-py
```

### 2. 環境変数の設定

ボットの実行には、いくつかの環境変数が必要です。プロジェクトのルートディレクトリに `.env` ファイルを作成し、`_env.example` を参考に以下の情報を記述してください。

```ini
# .env
DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN_HERE
SUPABASE_URL=YOUR_SUPABASE_PROJECT_URL_HERE
SUPABASE_KEY=YOUR_SUPABASE_ANON_KEY_HERE
PORT=8080
```

- `DISCORD_TOKEN`: Discord Developer Portalで取得したボットのトークン。
- `SUPABASE_URL`: SupabaseプロジェクトのURL。
- `SUPABASE_KEY`: SupabaseプロジェクトのAnon Key。
- `PORT`: `keep_alive.py`がリッスンするポート（デフォルトは8080）。

### 3. Supabaseのセットアップ

Supabaseプロジェクトで、タスクデータと設定データを保存するためのテーブルを作成する必要があります。詳細については、`utils/supabase_manager.py`のTODOコメントを参照してください。

### 4. ボットの実行

環境変数を設定し、必要な依存関係をインストールしたら、以下のコマンドでボットを起動できます。

```bash
python main.py
```

ボットが正常に起動すると、コンソールにログインメッセージとコマンド同期のメッセージが表示されます。

### 5. Koyebへのデプロイ (オプション)

Koyebなどのクラウドプラットフォームにデプロイする場合、`keep_alive.py`が提供するウェブサーバーがヘルスチェックエンドポイントとして機能し、ボットが常時稼働するようにします。

## 使用方法

ボットがDiscordサーバーに参加したら、スラッシュコマンドを使用して操作できます。

- `/config`: ボットの管理者設定を行います。（管理者権限が必要です）
- `/task add`: 新しいタスクを追加します。
- `/task list`: 既存のタスクを一覧表示します。
- `/task detail`: 特定のタスクの詳細を表示します。
- `/task done`: タスクを完了済みにします。
- `/task edit`: 既存のタスクを編集します。
- `/task delete`: タスクを削除（ステータスを更新）します。

各コマンドの具体的な使用方法については、Discord内で`/help`コマンド（もし実装されていれば）または各コマンドの説明を参照してください。
