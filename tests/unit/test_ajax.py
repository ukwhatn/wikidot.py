"""Ajaxモジュールのユニットテスト

ヘルパー関数のテストを行う。
AjaxRequestHeaderとAjaxModuleConnectorConfigのテストはtest_amc_client.pyに統合済み。
"""

from unittest.mock import MagicMock

import pytest

from wikidot.common.exceptions import ResponseDataException
from wikidot.connector.ajax import (
    _calculate_backoff,
    _encode_amc_body,
    _mask_sensitive_data,
    require_body,
)


class TestMaskSensitiveData:
    """_mask_sensitive_data関数のテスト"""

    def test_masks_password(self):
        """パスワードがマスクされる"""
        body = {"username": "test", "password": "secret123"}
        result = _mask_sensitive_data(body)
        assert result["username"] == "test"
        assert result["password"] == "***MASKED***"
        # 元の辞書は変更されない
        assert body["password"] == "secret123"

    def test_masks_login(self):
        """loginがマスクされる"""
        body = {"login": "secret"}
        result = _mask_sensitive_data(body)
        assert result["login"] == "***MASKED***"

    def test_masks_session_id(self):
        """WIKIDOT_SESSION_IDがマスクされる"""
        body = {"WIKIDOT_SESSION_ID": "abc123"}
        result = _mask_sensitive_data(body)
        assert result["WIKIDOT_SESSION_ID"] == "***MASKED***"

    def test_masks_wikidot_token(self):
        """wikidot_token7がマスクされる"""
        body = {"wikidot_token7": 123456}
        result = _mask_sensitive_data(body)
        assert result["wikidot_token7"] == "***MASKED***"

    def test_preserves_non_sensitive_data(self):
        """機密でないデータは保持される"""
        body = {"moduleName": "test", "page_id": 123}
        result = _mask_sensitive_data(body)
        assert result["moduleName"] == "test"
        assert result["page_id"] == 123

    def test_empty_dict(self):
        """空の辞書でも動作する"""
        result = _mask_sensitive_data({})
        assert result == {}


class TestCalculateBackoff:
    """_calculate_backoff関数のテスト"""

    def test_first_retry(self):
        """最初のリトライ（retry_count=1）"""
        # 2^0 * 1.0 = 1.0（ジッターなしの場合）
        result = _calculate_backoff(1, 1.0, 2.0, 60.0)
        # ジッターがあるので範囲でチェック
        assert 1.0 <= result <= 1.1

    def test_second_retry(self):
        """2回目のリトライ（retry_count=2）"""
        # 2^1 * 1.0 = 2.0（ジッターなしの場合）
        result = _calculate_backoff(2, 1.0, 2.0, 60.0)
        assert 2.0 <= result <= 2.2

    def test_third_retry(self):
        """3回目のリトライ（retry_count=3）"""
        # 2^2 * 1.0 = 4.0（ジッターなしの場合）
        result = _calculate_backoff(3, 1.0, 2.0, 60.0)
        assert 4.0 <= result <= 4.4

    def test_respects_max_backoff(self):
        """max_backoffを超えない"""
        # 2^9 * 1.0 = 512.0 > 60.0
        result = _calculate_backoff(10, 1.0, 2.0, 60.0)
        assert result == 60.0

    def test_custom_base_interval(self):
        """カスタムのbase_interval"""
        # 2^1 * 2.0 = 4.0（ジッターなしの場合）
        result = _calculate_backoff(2, 2.0, 2.0, 60.0)
        assert 4.0 <= result <= 4.4

    def test_custom_backoff_factor(self):
        """カスタムのbackoff_factor"""
        # 3^2 * 1.0 = 9.0（ジッターなしの場合）
        result = _calculate_backoff(3, 1.0, 3.0, 60.0)
        assert 9.0 <= result <= 9.9


class TestEncodeAmcBody:
    """_encode_amc_body関数のテスト"""

    def test_scalar_only_body_unchanged(self):
        """list値を含まないbodyはそのまま返る"""
        body = {"moduleName": "Test", "page_id": 123, "wikidot_token7": 123456}
        result = _encode_amc_body(body)
        assert result == body

    def test_list_value_gets_bracket_key(self):
        """list値を持つキーは[]サフィックス付きにリネームされる"""
        body = {"moduleName": "DashboardMessageAction", "selected": [1, 2, 3]}
        result = _encode_amc_body(body)
        assert "selected" not in result
        assert result["selected[]"] == [1, 2, 3]
        assert result["moduleName"] == "DashboardMessageAction"

    def test_multiple_list_values(self):
        """複数のlist値キーがそれぞれ[]付きになる"""
        body = {"selected": [1, 2], "messages": [3, 4], "other": "scalar"}
        result = _encode_amc_body(body)
        assert result == {"selected[]": [1, 2], "messages[]": [3, 4], "other": "scalar"}

    def test_result_is_still_a_mapping(self):
        """戻り値はhttpxのdata=がサポートするMapping（dict）のまま"""
        result = _encode_amc_body({"others": [1, 2]})
        assert isinstance(result, dict)


class TestRequireBody:
    """require_body関数のテスト"""

    def test_returns_body_when_present(self):
        """bodyフィールドがあれば値を返す"""
        response = MagicMock()
        response.json.return_value = {"status": "ok", "body": "<div>test</div>"}
        assert require_body(response, "TestModule") == "<div>test</div>"

    def test_raises_when_body_missing(self):
        """存在しないmoduleNameの応答（bodyフィールド欠落）ではResponseDataException"""
        response = MagicMock()
        response.json.return_value = {"status": "ok", "jsInclude": [], "cssInclude": []}
        with pytest.raises(ResponseDataException):
            require_body(response, "managesite/NoSuchModule")

    def test_error_message_includes_module_name(self):
        """例外メッセージにモジュール名が含まれる（デバッグしやすさのため）"""
        response = MagicMock()
        response.json.return_value = {"status": "ok"}
        with pytest.raises(ResponseDataException, match="managesite/NoSuchModule"):
            require_body(response, "managesite/NoSuchModule")
