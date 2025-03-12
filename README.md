# wikidot.py

[![Documentation Status](https://github.com/ukwhatn/wikidot.py/actions/workflows/docs.yml/badge.svg)](https://ukwhatn.github.io/wikidot.py/)

Pythonで簡単にWikidotサイトと対話するためのライブラリです。

## 主な機能

- サイト、ページ、ユーザー、フォーラムなどの情報取得と操作
- ページの作成、編集、削除
- フォーラムスレッドの取得、作成、返信
- ユーザー管理とサイトメンバーシップ
- プライベートメッセージの送受信
- ログイン不要の機能と認証が必要な機能両方をサポート

## インストール

```bash
pip install wikidot
```

## 使用例（基本）

```python
import wikidot

# ログインなしでの使用
client = wikidot.Client()

# サイトとページの情報取得
site = client.site.get("scp-jp")
page = site.page.get("scp-173")

print(f"タイトル: {page.title}")
print(f"評価: {page.rating}")
print(f"作成者: {page.created_by.name}")
```

## ドキュメント

詳細な使用方法、APIリファレンス、例は公式ドキュメントをご覧ください：

📚 **[公式ドキュメント](https://ukwhatn.github.io/wikidot.py/)**

- [インストール方法](https://ukwhatn.github.io/wikidot.py/installation.html)
- [クイックスタート](https://ukwhatn.github.io/wikidot.py/quickstart.html)
- [使用例](https://ukwhatn.github.io/wikidot.py/examples.html)
- [APIリファレンス](https://ukwhatn.github.io/wikidot.py/reference/index.html)

## ドキュメント構築

ローカルでドキュメントを構築するには:

```bash
# ドキュメント生成に必要なパッケージをインストール
make docs-install

# ドキュメントをビルド
make docs-build

# ローカルサーバーでドキュメントを確認（オプション）
make docs-serve
```

## Contribution

- [ロードマップ](https://ukwhatn.notion.site/wikidot-py-roadmap?pvs=4)
- [Issue](https://github.com/ukwhatn/wikidot.py/issues)