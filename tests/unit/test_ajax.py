"""Ajaxモジュールのユニットテスト"""

from wikidot.connector.ajax import AjaxModuleConnectorConfig, AjaxRequestHeader


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
        assert config.retry_interval == 5
        assert config.semaphore_limit == 10

    def test_custom_values(self):
        """カスタム値のテスト"""
        config = AjaxModuleConnectorConfig(
            request_timeout=30,
            attempt_limit=5,
            retry_interval=10,
            semaphore_limit=20,
        )
        assert config.request_timeout == 30
        assert config.attempt_limit == 5
        assert config.retry_interval == 10
        assert config.semaphore_limit == 20

    def test_partial_custom_values(self):
        """一部カスタム値のテスト"""
        config = AjaxModuleConnectorConfig(request_timeout=60)
        assert config.request_timeout == 60
        # 他はデフォルト値
        assert config.attempt_limit == 3
        assert config.retry_interval == 5
        assert config.semaphore_limit == 10
