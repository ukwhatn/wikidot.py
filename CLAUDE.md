# CLAUDE.md - wikidot.py プロジェクトガイド

このドキュメントはAIエージェント向けのプロジェクトガイドです。

## プロジェクト概要

**wikidot.py** は、PythonでWikidotサイトと対話するための非同期ユーティリティライブラリです。

- **バージョン**: 4.0.0
- **Python対応**: 3.10, 3.11, 3.12, 3.13, 3.14
- **ライセンス**: MIT

### 主な機能

- サイト情報の取得・管理
- ページの作成、編集、削除、検索（ListPagesModule対応）
- ユーザー情報の取得・検索
- フォーラム（カテゴリ、スレッド、投稿）操作
- プライベートメッセージの送受信
- 認証機能（ログインなしでも公開情報はアクセス可能）

## ディレクトリ構造

```
wikidot.py/
├── src/wikidot/
│   ├── __init__.py          # パッケージ初期化（動的インポート）
│   ├── common/              # 共通ユーティリティ
│   │   ├── decorators.py    # @login_required デコレータ
│   │   ├── exceptions.py    # カスタム例外
│   │   └── logger.py        # ロギング設定
│   ├── connector/           # HTTP通信
│   │   ├── ajax.py          # AjaxModuleConnectorClient
│   │   └── api.py           # APIキー定義
│   ├── module/              # コアモジュール
│   │   ├── client.py        # Client（メインエントリポイント）
│   │   ├── site.py          # Site（サイト管理）
│   │   ├── page.py          # Page（ページ操作・最大モジュール）
│   │   ├── user.py          # User階層（User, DeletedUser等）
│   │   ├── auth.py          # HTTPAuthentication
│   │   ├── forum_*.py       # フォーラム関連
│   │   ├── private_message.py
│   │   ├── page_*.py        # ページ関連（revision, votes, file等）
│   │   └── site_*.py        # サイト関連（member, application）
│   └── util/                # ユーティリティ
│       ├── quick_module.py  # QuickModule検索
│       ├── stringutil.py    # 文字列変換（Unix形式化）
│       ├── requestutil.py   # 非同期リクエスト
│       └── parser/          # HTMLパーサー
├── tests/
│   ├── unit/                # ユニットテスト
│   ├── integration/         # 統合テスト
│   └── fixtures/            # テストフィクスチャ
├── pyproject.toml           # プロジェクト設定
└── Makefile                 # 開発コマンド
```

## 開発コマンド

```bash
# フォーマット
make format

# リント（Ruff + mypy）
make lint

# リント修正
make lint-fix

# テスト実行
make test              # 全テスト
make test-unit         # ユニットテストのみ
make test-integration  # 統合テストのみ
make test-cov          # カバレッジ付き（80%以上必須）

# ビルド
make build

# リリース（バージョン更新→フォーマット→コミット→PR→Release）
make release version=X.Y.Z
```

## アーキテクチャ

### 設計パターン

1. **Facadeパターン**: `Client`が複数システムの統一インターフェース
2. **Accessorパターン**: 機能をグループ化（`client.user`, `client.site`, `site.page`等）
3. **Collectionパターン**: 複数リソースの一括操作（`PageCollection`, `UserCollection`等）
4. **Factoryパターン**: `Page.from_name()`, `Site.from_unix_name()`等のクラスメソッド

### コアクラス

```python
# Client - メインエントリポイント
client = wikidot.Client(username, password)
client.user.get("username")
client.site.get("scp-jp")
client.private_message.inbox

# Site - サイト操作
site = client.site.get("scp-jp")
site.page.get("page-name")
site.pages.search(category="*", tags=["tag1"])
site.forum.get_categories()

# Page - ページ操作
page = site.page.get("page-name")
page.source          # ページソース
page.votes           # 投票情報
page.update(source, comments)
page.delete()
```

### User階層

```
AbstractUser (基底)
├── User            # 通常ユーザー
├── DeletedUser     # 削除済みユーザー
├── AnonymousUser   # 匿名ユーザー
├── GuestUser       # ゲストユーザー
└── WikidotUser     # Wikidot公式ユーザー
```

### 非同期処理

- 内部で`asyncio`を使用（`asyncio.gather`で並列実行）
- 外部APIは同期的（`asyncio.run`でラップ）
- `AjaxModuleConnectorClient`がセマフォで並行数制限（デフォルト10）
- 自動リトライ（指数バックオフ + ジッター）

### 例外階層

```
WikidotException (基底)
├── UnexpectedException
├── SessionCreateException
├── LoginRequiredException
├── AjaxModuleConnectorException
│   ├── AMCHttpStatusCodeException
│   ├── WikidotStatusCodeException
│   └── ResponseDataException
├── NotFoundException
├── TargetExistsException
├── TargetErrorException
├── ForbiddenException
└── NoElementException
```

## コード品質設定

### Ruff（リンター/フォーマッター）

- ターゲット: Python 3.10
- 行長: 120文字
- 有効ルール: E, F, I, W, UP, B, C4, SIM

### mypy（型チェック）

- strictモード相当
- `disallow_untyped_defs = true`
- テストは緩和設定

### pytest

- カバレッジ要件: 80%以上
- マーカー: `@pytest.mark.slow`, `@pytest.mark.integration`

## 重要な実装詳細

### 認証フロー

1. `Client.__init__(username, password)`
2. `HTTPAuthentication.login()` → Wikidot ログインエンドポイントへPOST
3. `WIKIDOT_SESSION_ID` クッキーを抽出
4. `@login_required` デコレータで検証

### HTMLパース

- BeautifulSoup4 + lxml
- `odate_parse()`: Wikidot日時要素をdatetimeに変換
- `user_parse()`: HTML要素からUser型を自動判定

### SearchPagesQuery

ListPagesModuleの複雑なクエリをPythonで表現：

```python
@dataclass
class SearchPagesQuery:
    pagetype: str = "*"
    category: str = "*"
    tags: str | list[str] | None = None
    parent: str | None = None
    created_by: User | str | None = None
    rating: str | None = None
    order: str = "created_at desc"
    offset: int = 0
    limit: int = 100
```

## 環境変数

```bash
WIKIDOT_USERNAME=your_username
WIKIDOT_PASSWORD=your_password
```

## 依存関係

### 必須

- `httpx >= 0.25, < 0.29` - 非同期HTTPクライアント
- `beautifulsoup4 >= 4.12.2, < 4.15.0` - HTMLパース
- `lxml >= 4.9.3, < 6.1.0` - XML/HTMLレンダリング

### 開発

- `ruff` - リンター/フォーマッター
- `mypy` - 型チェック
- `pytest`, `pytest-asyncio`, `pytest-cov`, `pytest-httpx` - テスト

## CI/CD

### GitHub Actions

- **check_code_quality.yml**: PR時にformat→lint→test（Python 3.10〜3.14）
- **publish.yml**: mainブランチへのプッシュ時にPyPIへ公開

## 注意事項

- 型ヒントは `T | None` 形式を使用（`Optional[T]` ではない）
- 内部クラス名は `*Accessor` パターン（v4.0.0で `*Methods` から変更）
- 公開APIは静的メソッドとAccessorパターンで構成
- エラーは明確な例外で区別（リトライ可能 vs 永続的）
