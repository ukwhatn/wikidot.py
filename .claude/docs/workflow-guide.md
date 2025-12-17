# 作業ワークフローガイド

## 概要

wikidot.pyプロジェクトでの開発作業は、以下の5フェーズで進行する。
各フェーズで適切なサブエージェントを活用し、品質と効率を両立させる。

## フェーズ詳細

### フェーズ1: 調査

- 既存コードベースを深く調査
- 使用ツール:
  - Plan subagent: コードベース探索
  - WebSearch: 外部情報検索
  - context7: ライブラリドキュメント参照
  - dependency-analyzer: 影響範囲分析
- 取りうる選択肢が複数ある場合は、pros/consをユーザーに提示
- 既存コードとの親和性・整合性を重視

### フェーズ2: 計画立案

- code-plannerサブエージェントで詳細実装計画を立案
- 計画に含めるべき項目:
  - コミットタイミング
  - 型チェック・品質確認タイミング
  - テスト実行タイミング

### フェーズ3: 実装

- code-committerでこまめにコミット
  - git-cz形式（prefix以外は日本語）
  - Co-Authored-by、Generated with の使用禁止
- quality-checkerで品質確認しながら進行
- エラー発生時: code-plannerで修正計画を立案（場当たり的修正禁止）
- コメント: 不要なコメントは避け、Whyを示す場合のみ使用

### フェーズ4: 品質確認

- quality-checkerで最終品質チェック（lint, format, type-check, test）
- self-reviewerでセルフレビュー
- 問題があれば修正を提案

### フェーズ5: PR作成

- pr-creatorでDraft PR作成
- PRテンプレートに従った本文作成

## サブエージェント連携フロー

```
調査 ─────────────────────────────────────────────────────────────
  ├─ Plan subagent: コードベース探索
  └─ dependency-analyzer: 影響範囲分析

計画 ─────────────────────────────────────────────────────────────
  └─ code-planner: 詳細実装計画立案

実装 ─────────────────────────────────────────────────────────────
  ├─ 実装作業
  ├─ code-committer: コミット
  └─ quality-checker: 品質確認
       ├─ lint-runner
       ├─ format-runner
       ├─ typecheck-runner
       └─ test-runner

品質確認 ─────────────────────────────────────────────────────────
  ├─ quality-checker: 最終チェック
  └─ self-reviewer (合議制可): セルフレビュー

PR作成 ───────────────────────────────────────────────────────────
  └─ pr-creator: Draft PR作成
```

## 禁止事項

- 場当たり的なエラー修正（必ずcode-plannerで計画を立案）
- 不要なコメント（コードを読めばわかる内容）
- Co-Authored-by、Generated with の使用
- 絵文字の使用（ドキュメント・コミットメッセージ）

## ドキュメント作成ルール

- すべて日本語で記載
- 絵文字の使用禁止
- 明瞭で簡潔な文体

## 並列実行パターン

### 品質チェックの並列実行

quality-checkerが4つの専用エージェントを並列呼び出し:

```
quality-checker
    ├─ lint-runner     → Lintエラーレポート
    ├─ format-runner   → フォーマット違反レポート
    ├─ typecheck-runner → 型エラーレポート
    └─ test-runner     → テスト失敗レポート
```

### セルフレビューの合議制

複数のself-reviewerを並列起動し、レポートを統合:

```
メインセッション
    ├─ self-reviewer (instance 1) → レビューレポート1
    ├─ self-reviewer (instance 2) → レビューレポート2
    └─ self-reviewer (instance 3) → レビューレポート3
```

## モデル選択方針

- **sonnet**: 単純作業（コミット、PR作成、フォーマット実行など）
- **inherit（opus）**: 複雑な思考・分析（レビュー、計画立案、実装など）

## 品質チェックコマンド

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
```

## 品質要件

| 項目 | 要件 |
|-----|------|
| カバレッジ | 80%以上 |
| 型チェック | mypy strict相当 |
| Lint | Ruff (E, F, I, W, UP, B, C4, SIM) |
| フォーマット | Ruff format (120文字) |
