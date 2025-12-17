# コードレビュー学習ログ

過去のコードレビューで指摘されたパターンを蓄積し、同様のミスを防ぐためのドキュメントです。

**更新ルール**: 重要なレビュー指摘を受けた際にその都度追記してください。

---

## ミスパターン一覧

### 1. 非同期処理の不適切な使用

**問題**:
- `asyncio.run()`を内部で不必要に呼び出す
- async/awaitの欠落
- セマフォによる並行数制限の考慮漏れ

**回避方法**:
1. 内部処理は非同期、外部APIは同期（`asyncio.run`でラップ）を徹底
2. `AjaxModuleConnectorClient`のセマフォ設定を確認
3. 並列実行時は`asyncio.gather`を適切に使用

---

### 2. 型ヒントの不整合

**問題**:
- `Optional[T]`と`T | None`の混在
- 戻り値型の省略
- `Any`の過剰使用

**回避方法**:
1. `T | None`形式で統一（`Optional`は使用しない）
2. すべての関数に戻り値型を明示
3. `Any`は最後の手段として、具体的な型を使用

**チェックコマンド**:
```bash
# Optional使用箇所の確認
grep -r "Optional\[" src/wikidot/

# Any使用箇所の確認
grep -r ": Any" src/wikidot/
```

---

### 3. 例外階層の誤用

**問題**:
- 不適切な基底例外の継承
- 既存例外で対応可能なケースで新規例外を作成
- 例外メッセージの不統一

**回避方法**:
1. `WikidotException`階層を確認してから例外を追加
2. 既存例外（`NotFoundException`, `ForbiddenException`等）を優先使用
3. 例外メッセージは具体的かつ一貫した形式で記述

**例外階層**:
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

---

### 4. Accessorパターンの違反

**問題**:
- Accessorクラス以外で直接リソースを操作
- クラス名が`*Accessor`パターンに従っていない
- `*Methods`（旧命名）の使用

**回避方法**:
1. リソース操作はAccessorクラス経由で行う
2. 新規Accessorは`*Accessor`命名パターンに従う
3. 既存コードの命名パターンを確認

**チェックコマンド**:
```bash
# Accessorクラスの確認
grep -r "class.*Accessor" src/wikidot/

# 旧命名パターンの確認
grep -r "class.*Methods" src/wikidot/
```

---

### 5. テストカバレッジの不足

**問題**:
- 新規機能にテストが追加されていない
- エッジケースのテスト漏れ
- カバレッジ80%未満

**回避方法**:
1. 新規機能には必ずユニットテストを追加
2. 正常系・異常系・境界値のテストケースを網羅
3. `make test-cov`でカバレッジを確認

---

## PR別の教訓

（今後のレビュー指摘を受けて追記）

---

## 追記テンプレート

新しい教訓を追記する際は、以下のテンプレートを使用してください:

```markdown
### N. [ミスパターン名]

**発生例**: PR #XXXX（[PR名]）

**問題**:
- [具体的な問題点1]
- [具体的な問題点2]

**回避方法**:
1. [具体的な回避方法1]
2. [具体的な回避方法2]

**チェックコマンド**:
```bash
# [確認コマンド]
```
```
