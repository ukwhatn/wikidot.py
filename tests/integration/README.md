# 統合テスト

## 概要

このディレクトリには、実際のWikidotサーバー（ukwhatn-ci.wikidot.com）に対する統合テストが含まれています。

## 環境設定

### 必要な環境変数

```bash
export WIKIDOT_USERNAME=your_username
export WIKIDOT_PASSWORD=your_password
```

### テストサイト

- サイト名: `ukwhatn-ci.wikidot.com`
- 要件: テストアカウントがサイトのメンバーであること

## テスト実行

```bash
# 統合テストのみ実行
cd /Users/yuki.c.watanabe/dev/scp/libs/wikidot.py
make test-integration

# または直接pytest
pytest tests/integration/ -v

# 特定のテストファイルを実行
pytest tests/integration/test_page_lifecycle.py -v
```

## テストカバー範囲

| テストファイル | カバー機能 |
|--------------|----------|
| test_site.py | サイト取得、ページ取得 |
| test_page_lifecycle.py | ページ作成、取得、編集、削除 |
| test_page_tags.py | タグ追加、変更、削除 |
| test_page_meta.py | メタ設定、取得、更新、削除 |
| test_page_revision.py | リビジョン履歴取得、最新リビジョン取得 |
| test_page_votes.py | 投票情報取得 |
| test_page_discussion.py | ディスカッション取得、投稿作成 |
| test_forum_category.py | フォーラムカテゴリ一覧、スレッド取得 |
| test_user.py | ユーザー検索、一括取得 |
| test_pm.py | 受信箱/送信箱取得、メッセージ確認 |

## スキップ対象機能

以下の機能は統合テストからスキップされています:

### 1. サイト参加申請
- 理由: テストサイトへの参加申請は手動承認が必要
- 該当API: `site.application.*`

### 2. プライベートメッセージ送信
- 理由: 実ユーザーへのメッセージ送信を避けるため
- 該当API: `client.private_message.send()`
- 備考: 取得のみテスト。事前にInbox/Outboxにメッセージを入れておくこと

### 3. フォーラムカテゴリ/スレッド作成
- 理由: フォーラム構造への永続的な変更を避けるため
- 該当API: `site.forum.create_thread()`
- 備考: ページディスカッションへの投稿のみテスト

### 4. メンバー招待
- 理由: 実ユーザーへの招待を避けるため
- 該当API: `site.member.invite()`

## クリーンアップ戦略

1. 各テストクラスの`setup`フィクスチャでテスト用ページを作成
2. `yield`後のクリーンアップ処理で作成したページを削除
3. 削除失敗時はログ出力して続行
4. ページ命名: `{prefix}-{timestamp}-{random6chars}` 形式で衝突を回避

## 注意事項

- 環境変数が未設定の場合、統合テストは自動的にスキップされます
- テストは各ファイル内で順次実行されます（テスト間に依存関係がある場合があるため）
- APIレート制限に注意してください
- テスト実行後、クリーンアップに失敗したページが残る場合があります
  - ページ名プレフィックス（`test-`）で識別可能
  - 必要に応じて手動削除してください
