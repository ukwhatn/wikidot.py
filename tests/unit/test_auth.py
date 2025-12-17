"""
認証モジュールのユニットテスト

HTTPAuthenticationクラスをテストする。
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from wikidot.common.exceptions import SessionCreateException
from wikidot.module.auth import HTTPAuthentication


class TestHTTPAuthentication:
    """HTTPAuthenticationクラスのテスト"""

    def test_login_success(self):
        """ログイン成功"""
        mock_client = MagicMock()
        mock_client.amc_client.header.get_header.return_value = {}

        mock_response = MagicMock()
        mock_response.status_code = httpx.codes.OK
        mock_response.text = "Login successful"
        mock_response.cookies = {"WIKIDOT_SESSION_ID": "test-session-id"}

        with patch("wikidot.module.auth.httpx.post", return_value=mock_response):
            HTTPAuthentication.login(mock_client, "test-user", "test-password")

        mock_client.amc_client.header.set_cookie.assert_called_once_with("WIKIDOT_SESSION_ID", "test-session-id")

    def test_login_invalid_credentials(self):
        """認証失敗（ユーザー名/パスワード不一致）"""
        mock_client = MagicMock()
        mock_client.amc_client.header.get_header.return_value = {}

        mock_response = MagicMock()
        mock_response.status_code = httpx.codes.OK
        mock_response.text = "The login and password do not match"

        with patch("wikidot.module.auth.httpx.post", return_value=mock_response):
            with pytest.raises(SessionCreateException) as exc_info:
                HTTPAuthentication.login(mock_client, "wrong-user", "wrong-password")

            assert "invalid username or password" in str(exc_info.value)

    def test_login_http_error(self):
        """ログイン失敗（HTTPエラー）"""
        mock_client = MagicMock()
        mock_client.amc_client.header.get_header.return_value = {}

        mock_response = MagicMock()
        mock_response.status_code = httpx.codes.INTERNAL_SERVER_ERROR

        with patch("wikidot.module.auth.httpx.post", return_value=mock_response):
            with pytest.raises(SessionCreateException) as exc_info:
                HTTPAuthentication.login(mock_client, "test-user", "test-password")

            assert "HTTP status code" in str(exc_info.value)

    def test_login_no_session_cookie(self):
        """ログイン失敗（セッションCookieなし）"""
        mock_client = MagicMock()
        mock_client.amc_client.header.get_header.return_value = {}

        mock_response = MagicMock()
        mock_response.status_code = httpx.codes.OK
        mock_response.text = "Login successful"
        mock_response.cookies = {}  # セッションCookieなし

        with patch("wikidot.module.auth.httpx.post", return_value=mock_response):
            with pytest.raises(SessionCreateException) as exc_info:
                HTTPAuthentication.login(mock_client, "test-user", "test-password")

            assert "invalid cookies" in str(exc_info.value)

    def test_logout(self):
        """ログアウト成功"""
        mock_client = MagicMock()

        HTTPAuthentication.logout(mock_client)

        mock_client.amc_client.request.assert_called_once()
        mock_client.amc_client.header.delete_cookie.assert_called_once_with("WIKIDOT_SESSION_ID")

    def test_logout_suppresses_errors(self):
        """ログアウト時のエラーが抑制される"""
        mock_client = MagicMock()
        mock_client.amc_client.request.side_effect = Exception("Network error")

        # エラーが発生しても例外が送出されない
        HTTPAuthentication.logout(mock_client)

        # Cookieの削除は常に実行される
        mock_client.amc_client.header.delete_cookie.assert_called_once_with("WIKIDOT_SESSION_ID")
