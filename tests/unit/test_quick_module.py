"""QuickModuleのユニットテスト"""

from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from wikidot.util.quick_module import QMCPage, QMCUser, QuickModule


class TestQMCUser:
    """QMCUserデータクラスのテスト"""

    def test_init(self):
        """初期化"""
        user = QMCUser(id=12345, name="test-user")

        assert user.id == 12345
        assert user.name == "test-user"


class TestQMCPage:
    """QMCPageデータクラスのテスト"""

    def test_init(self):
        """初期化"""
        page = QMCPage(title="Test Page", unix_name="test-page")

        assert page.title == "Test Page"
        assert page.unix_name == "test-page"


class TestQuickModuleRequest:
    """QuickModule._requestのテスト"""

    def test_request_member_lookup(self, quickmodule_member_lookup: dict[str, Any]):
        """MemberLookupQModuleリクエスト"""
        mock_response = MagicMock()
        mock_response.status_code = httpx.codes.OK
        mock_response.json.return_value = quickmodule_member_lookup

        with patch("httpx.get", return_value=mock_response) as mock_get:
            result = QuickModule._request("MemberLookupQModule", 123456, "test")

            mock_get.assert_called_once()
            call_url = mock_get.call_args[0][0]
            assert "MemberLookupQModule" in call_url
            assert "s=123456" in call_url
            assert "q=test" in call_url
            assert result == quickmodule_member_lookup

    def test_request_user_lookup(self, quickmodule_user_lookup: dict[str, Any]):
        """UserLookupQModuleリクエスト"""
        mock_response = MagicMock()
        mock_response.status_code = httpx.codes.OK
        mock_response.json.return_value = quickmodule_user_lookup

        with patch("httpx.get", return_value=mock_response):
            result = QuickModule._request("UserLookupQModule", 123456, "test")

            assert result == quickmodule_user_lookup

    def test_request_page_lookup(self, quickmodule_page_lookup: dict[str, Any]):
        """PageLookupQModuleリクエスト"""
        mock_response = MagicMock()
        mock_response.status_code = httpx.codes.OK
        mock_response.json.return_value = quickmodule_page_lookup

        with patch("httpx.get", return_value=mock_response):
            result = QuickModule._request("PageLookupQModule", 123456, "test")

            assert result == quickmodule_page_lookup

    def test_request_invalid_module_raises(self):
        """無効なモジュール名でValueError"""
        with pytest.raises(ValueError, match="Invalid module name"):
            QuickModule._request("InvalidModule", 123456, "test")

    def test_request_site_not_found(self):
        """サイトが見つからない場合ValueError"""
        mock_response = MagicMock()
        mock_response.status_code = httpx.codes.INTERNAL_SERVER_ERROR

        with (
            patch("httpx.get", return_value=mock_response),
            pytest.raises(ValueError, match="Site is not found"),
        ):
            QuickModule._request("MemberLookupQModule", 999999, "test")


class TestQuickModuleMemberLookup:
    """QuickModule.member_lookupのテスト"""

    def test_member_lookup_success(self, quickmodule_member_lookup: dict[str, Any]):
        """メンバー検索成功"""
        mock_response = MagicMock()
        mock_response.status_code = httpx.codes.OK
        mock_response.json.return_value = quickmodule_member_lookup

        with patch("httpx.get", return_value=mock_response):
            users = QuickModule.member_lookup(123456, "test")

            assert len(users) == 2
            assert users[0].id == 12345
            assert users[0].name == "test-user"
            assert users[1].id == 67890
            assert users[1].name == "test-user-2"

    def test_member_lookup_empty(self, quickmodule_member_lookup_empty: dict[str, Any]):
        """メンバー検索（結果なし）"""
        mock_response = MagicMock()
        mock_response.status_code = httpx.codes.OK
        mock_response.json.return_value = quickmodule_member_lookup_empty

        with patch("httpx.get", return_value=mock_response):
            users = QuickModule.member_lookup(123456, "nonexistent")

            assert len(users) == 0


class TestQuickModuleUserLookup:
    """QuickModule.user_lookupのテスト"""

    def test_user_lookup_success(self, quickmodule_user_lookup: dict[str, Any]):
        """ユーザー検索成功"""
        mock_response = MagicMock()
        mock_response.status_code = httpx.codes.OK
        mock_response.json.return_value = quickmodule_user_lookup

        with patch("httpx.get", return_value=mock_response):
            users = QuickModule.user_lookup(123456, "test")

            assert len(users) == 1
            assert users[0].id == 12345
            assert users[0].name == "test-user"


class TestQuickModulePageLookup:
    """QuickModule.page_lookupのテスト"""

    def test_page_lookup_success(self, quickmodule_page_lookup: dict[str, Any]):
        """ページ検索成功"""
        mock_response = MagicMock()
        mock_response.status_code = httpx.codes.OK
        mock_response.json.return_value = quickmodule_page_lookup

        with patch("httpx.get", return_value=mock_response):
            pages = QuickModule.page_lookup(123456, "test")

            assert len(pages) == 2
            assert pages[0].unix_name == "test-page"
            assert pages[0].title == "Test Page"
            assert pages[1].unix_name == "scp-001"
            assert pages[1].title == "SCP-001"

    def test_page_lookup_empty(self, quickmodule_page_lookup_empty: dict[str, Any]):
        """ページ検索（結果なし）"""
        mock_response = MagicMock()
        mock_response.status_code = httpx.codes.OK
        mock_response.json.return_value = quickmodule_page_lookup_empty

        with patch("httpx.get", return_value=mock_response):
            pages = QuickModule.page_lookup(123456, "nonexistent")

            assert len(pages) == 0
