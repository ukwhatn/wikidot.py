# テストガイド

## テスト種別

| 種別 | 場所 | 実行コマンド | 対象 |
|-----|------|-------------|------|
| ユニットテスト | `tests/unit/` | `make test-unit` | 個別関数・クラス |
| 統合テスト | `tests/integration/` | `make test-integration` | API・HTTP連携 |

## テスト実行コマンド

```bash
# 全テスト実行
make test

# ユニットテストのみ
make test-unit

# 統合テストのみ
make test-integration

# カバレッジ付き（80%以上必須）
make test-cov

# 特定ファイルのみ
pytest tests/unit/test_xxx.py -v

# 特定テストのみ
pytest tests/unit/test_xxx.py::test_function_name -v
```

## ユニットテスト作成ガイド

### 基本構造

```python
import pytest
from wikidot.module.page import Page

class TestPage:
    """Pageクラスのテスト"""

    def test_from_name_returns_page(self, mock_client):
        """from_nameメソッドがPageオブジェクトを返すこと"""
        # Arrange
        site = mock_client.site.get("test-site")

        # Act
        page = site.page.get("test-page")

        # Assert
        assert page is not None
        assert isinstance(page, Page)

    def test_from_name_raises_not_found(self, mock_client):
        """存在しないページでNotFoundExceptionが発生すること"""
        # Arrange
        site = mock_client.site.get("test-site")

        # Act & Assert
        with pytest.raises(NotFoundException):
            site.page.get("nonexistent-page")
```

### フィクスチャの使用

`tests/conftest.py`:

```python
import pytest
from unittest.mock import MagicMock, AsyncMock

@pytest.fixture
def mock_client():
    """モッククライアントのフィクスチャ"""
    client = MagicMock()
    client.site.get.return_value = MagicMock()
    return client

@pytest.fixture
def mock_ajax_connector():
    """モックAjaxConnectorのフィクスチャ"""
    connector = MagicMock()
    connector.request = AsyncMock()
    return connector
```

### 非同期テスト

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """非同期関数のテスト"""
    # Arrange
    expected = "result"

    # Act
    result = await some_async_function()

    # Assert
    assert result == expected
```

### パラメータ化テスト

```python
import pytest

@pytest.mark.parametrize("input_value,expected", [
    ("test", "test"),
    ("Test Page", "test-page"),
    ("日本語ページ", "日本語ページ"),
])
def test_to_unix_name(input_value, expected):
    """Unix名への変換テスト"""
    result = to_unix_name(input_value)
    assert result == expected
```

## 統合テスト作成ガイド

### 基本構造

統合テストは実際のWikidot APIを呼び出すため、以下の点に注意:

```python
import pytest

@pytest.mark.integration
@pytest.mark.slow
class TestPageIntegration:
    """Pageの統合テスト"""

    def test_get_page_from_real_site(self, real_client):
        """実際のサイトからページを取得できること"""
        # Arrange
        site = real_client.site.get("scp-jp")

        # Act
        page = site.page.get("scp-173")

        # Assert
        assert page is not None
        assert page.fullname == "scp-173"
```

### 環境変数の設定

統合テストには認証情報が必要:

```bash
export WIKIDOT_USERNAME=your_username
export WIKIDOT_PASSWORD=your_password
```

## モック戦略

### HTTPリクエストのモック

```python
from pytest_httpx import HTTPXMock

def test_ajax_request(httpx_mock: HTTPXMock):
    """AJAXリクエストのモック"""
    # Arrange
    httpx_mock.add_response(
        url="https://www.wikidot.com/ajax-module-connector.php",
        json={"status": "ok", "body": "<div>content</div>"}
    )

    # Act
    result = connector.request("module", {"param": "value"})

    # Assert
    assert result["status"] == "ok"
```

### 時間のモック

```python
from unittest.mock import patch
from datetime import datetime

def test_time_dependent_function():
    """時間依存の関数のテスト"""
    fixed_time = datetime(2024, 1, 1, 0, 0, 0)

    with patch("wikidot.util.datetime") as mock_datetime:
        mock_datetime.now.return_value = fixed_time

        result = some_time_function()

        assert result.created_at == fixed_time
```

## pytestマーカー

| マーカー | 用途 | 実行方法 |
|---------|------|----------|
| `@pytest.mark.slow` | 時間のかかるテスト | `pytest -m "not slow"` で除外 |
| `@pytest.mark.integration` | 統合テスト | `pytest -m integration` で実行 |
| `@pytest.mark.asyncio` | 非同期テスト | pytest-asyncioで自動処理 |

## カバレッジ要件

wikidot.pyプロジェクトのカバレッジ要件: **80%以上**

```bash
# カバレッジ確認
make test-cov

# HTML形式でレポート生成
pytest --cov=src/wikidot --cov-report=html tests/

# カバレッジが80%未満の場合はCIが失敗
```

## テスト命名規則

### ファイル名

- `test_<モジュール名>.py`
- 例: `test_page.py`, `test_user.py`

### クラス名

- `Test<クラス名>`
- 例: `TestPage`, `TestUser`

### メソッド名

- `test_<機能>_<条件>_<期待結果>`
- 例: `test_from_name_with_valid_name_returns_page`
- 日本語も可: `test_存在しないページでエラー`

## ベストプラクティス

### 1. AAAパターン

```python
def test_example():
    # Arrange - 準備
    input_data = create_test_data()

    # Act - 実行
    result = function_under_test(input_data)

    # Assert - 検証
    assert result == expected
```

### 2. 1テスト1アサート（原則）

```python
# 良い例
def test_page_has_correct_title():
    page = get_test_page()
    assert page.title == "Expected Title"

def test_page_has_correct_content():
    page = get_test_page()
    assert "expected content" in page.source

# 避けるべき例
def test_page_properties():
    page = get_test_page()
    assert page.title == "Expected Title"
    assert "expected content" in page.source
    assert page.rating > 0
```

### 3. テストの独立性

各テストは独立して実行可能であること:

```python
# 良い例
def test_create_page(mock_site):
    page = mock_site.page.create("test-page", "content")
    assert page is not None

# 避けるべき例（前のテストに依存）
created_page = None

def test_create_page():
    global created_page
    created_page = site.page.create("test-page", "content")

def test_delete_page():
    created_page.delete()  # 前のテストに依存
```

### 4. 期待値はハードコード

```python
# 良い例
assert page.title == "SCP-173"

# 避けるべき例
expected_title = page.title  # 同じ値を参照している
assert page.title == expected_title
```
