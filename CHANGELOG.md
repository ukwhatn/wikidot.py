# Changelog

このプロジェクトのすべての注目すべき変更点はこのファイルに記載されます。

フォーマットは [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) に基づいています。
バージョン管理は [セマンティックバージョニング](https://semver.org/lang/ja/) に従います。

## [Unreleased]

### Changed

- **BREAKING**: 内部クラス名を `*Methods` から `*Accessor` に変更
  - `SitePagesMethods` → `SitePagesAccessor`
  - `SitePageMethods` → `SitePageAccessor`
  - `SiteForumMethods` → `SiteForumAccessor`
  - `ClientUserMethods` → `ClientUserAccessor`
  - `ClientPrivateMessageMethods` → `ClientPrivateMessageAccessor`
  - `ClientSiteMethods` → `ClientSiteAccessor`
  - 注: `client.site`, `site.page` 等のプロパティ名は変更なし。内部クラスを直接参照していた場合のみ影響があります。

### Added

- 認証情報用の環境変数管理 (`.env.example`)
- ユニットテストフレームワーク (pytest, pytest-asyncio, pytest-cov)
- 例外クラス、StringUtil、SearchPagesQuery、Ajax関連クラスのユニットテスト

### Fixed

- 型ヒント記法を Python 3.10+ スタイルに統一 (`Optional[T]` → `T | None`)
- 例外ハンドリングを `contextlib.suppress` に統一
- Bugbear ルール違反の修正 (`zip()` への `strict=True` 追加等)
- ネストした `async with` 文の統合

### Security

- 認証情報のハードコード防止 (環境変数参照パターンに変更)
