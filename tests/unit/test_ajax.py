"""Ajaxモジュールのユニットテスト"""

from wikidot.connector.ajax import (
    AjaxModuleConnectorConfig,
    AjaxRequestHeader,
    _calculate_backoff,
    _mask_sensitive_data,
)


class TestAjaxRequestHeader:
    """AjaxRequestHeaderのテスト"""

    def test_default_values(self):
        """デフォルト値のテスト"""
        header = AjaxRequestHeader()
        assert header.content_type == "application/x-www-form-urlencoded; charset=UTF-8"
        assert header.user_agent == "WikidotPy"
        assert header.referer == "https://www.wikidot.com/"
        assert "wikidot_token7" in header.cookie
        assert header.cookie["wikidot_token7"] == 123456

    def test_custom_values(self):
        """カスタム値のテスト"""
        header = AjaxRequestHeader(
            content_type="application/json",
            user_agent="CustomAgent",
            referer="https://custom.wikidot.com/",
        )
        assert header.content_type == "application/json"
        assert header.user_agent == "CustomAgent"
        assert header.referer == "https://custom.wikidot.com/"

    def test_custom_cookie(self):
        """カスタムCookieのテスト"""
        header = AjaxRequestHeader(cookie={"session_id": "abc123"})
        assert "wikidot_token7" in header.cookie
        assert header.cookie["session_id"] == "abc123"

    def test_set_cookie(self):
        """Cookie設定のテスト"""
        header = AjaxRequestHeader()
        header.set_cookie("new_cookie", "value123")
        assert header.cookie["new_cookie"] == "value123"

    def test_delete_cookie(self):
        """Cookie削除のテスト"""
        header = AjaxRequestHeader(cookie={"to_delete": "value"})
        header.delete_cookie("to_delete")
        assert "to_delete" not in header.cookie

    def test_get_header(self):
        """ヘッダ取得のテスト"""
        header = AjaxRequestHeader()
        result = header.get_header()
        assert "Content-Type" in result
        assert "User-Agent" in result
        assert "Referer" in result
        assert "Cookie" in result
        assert result["Content-Type"] == "application/x-www-form-urlencoded; charset=UTF-8"
        assert result["User-Agent"] == "WikidotPy"
        assert result["Referer"] == "https://www.wikidot.com/"
        # Cookieはname=value;形式
        assert "wikidot_token7=123456;" in result["Cookie"]

    def test_get_header_with_multiple_cookies(self):
        """複数Cookieのヘッダ取得テスト"""
        header = AjaxRequestHeader(cookie={"extra": "value"})
        result = header.get_header()
        assert "wikidot_token7=123456;" in result["Cookie"]
        assert "extra=value;" in result["Cookie"]


class TestAjaxModuleConnectorConfig:
    """AjaxModuleConnectorConfigのテスト"""

    def test_default_values(self):
        """デフォルト値のテスト"""
        config = AjaxModuleConnectorConfig()
        assert config.request_timeout == 20
        assert config.attempt_limit == 3
        assert config.retry_interval == 1.0
        assert config.max_backoff == 60.0
        assert config.backoff_factor == 2.0
        assert config.semaphore_limit == 10

    def test_custom_values(self):
        """カスタム値のテスト"""
        config = AjaxModuleConnectorConfig(
            request_timeout=30,
            attempt_limit=5,
            retry_interval=2.0,
            max_backoff=120.0,
            backoff_factor=3.0,
            semaphore_limit=20,
        )
        assert config.request_timeout == 30
        assert config.attempt_limit == 5
        assert config.retry_interval == 2.0
        assert config.max_backoff == 120.0
        assert config.backoff_factor == 3.0
        assert config.semaphore_limit == 20

    def test_partial_custom_values(self):
        """一部カスタム値のテスト"""
        config = AjaxModuleConnectorConfig(request_timeout=60)
        assert config.request_timeout == 60
        # 他はデフォルト値
        assert config.attempt_limit == 3
        assert config.retry_interval == 1.0
        assert config.max_backoff == 60.0
        assert config.backoff_factor == 2.0
        assert config.semaphore_limit == 10


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
