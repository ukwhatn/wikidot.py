"""Siteモジュールのユニットテスト"""

from typing import Any
from unittest.mock import MagicMock, create_autospec, patch

import pytest
from pytest_httpx import HTTPXMock

from wikidot.common.exceptions import (
    LoginRequiredException,
    NotFoundException,
    TargetErrorException,
    UnexpectedException,
    WikidotStatusCodeException,
)
from wikidot.module.client import Client
from wikidot.module.site import Site


def create_mock_client(is_logged_in: bool = True) -> MagicMock:
    """Clientクラスのモックを作成（isinstance()チェックを通過する）"""
    mock_client = create_autospec(Client, instance=True)
    mock_client.is_logged_in = is_logged_in
    if is_logged_in:
        mock_client.login_check.return_value = None
    else:
        mock_client.login_check.side_effect = LoginRequiredException("Login required")
    mock_client.amc_client = MagicMock()
    mock_client.amc_client.config.request_timeout = 30.0
    return mock_client


class TestSiteDataclass:
    """Siteデータクラスのテスト"""

    def test_site_str(self, mock_site_no_http: Site) -> None:
        """__str__が正しい文字列を返す"""
        result = str(mock_site_no_http)

        assert "Site(" in result
        assert "id=123456" in result
        assert "title=Test Site" in result
        assert "unix_name=test-site" in result

    def test_site_url_with_ssl(self, mock_client_no_http: MagicMock) -> None:
        """SSL対応サイトのURLはhttps"""
        site = Site(
            client=mock_client_no_http,
            id=1,
            title="Test",
            unix_name="test",
            domain="test.wikidot.com",
            ssl_supported=True,
        )

        assert site.url == "https://test.wikidot.com"

    def test_site_url_without_ssl(self, mock_client_no_http: MagicMock) -> None:
        """SSL非対応サイトのURLはhttp"""
        site = Site(
            client=mock_client_no_http,
            id=1,
            title="Test",
            unix_name="test",
            domain="test.wikidot.com",
            ssl_supported=False,
        )

        assert site.url == "http://test.wikidot.com"

    def test_site_has_accessors(self, mock_site_no_http: Site) -> None:
        """Siteはpages/page/forumアクセサを持つ"""
        assert hasattr(mock_site_no_http, "pages")
        assert hasattr(mock_site_no_http, "page")
        assert hasattr(mock_site_no_http, "forum")


class TestSiteFromUnixName:
    """Site.from_unix_name のテスト"""

    def test_from_unix_name_ssl_site(self, mock_client_no_http: MagicMock, httpx_mock: HTTPXMock) -> None:
        """SSL対応サイトを正しく取得できる"""
        html = """
        <html>
        <head><title>Test Site Title</title></head>
        <body>
        <script>
            WIKIREQUEST.info.siteId = 123456;
            WIKIREQUEST.info.siteUnixName = "test-site";
            WIKIREQUEST.info.domain = "test-site.wikidot.com";
        </script>
        </body>
        </html>
        """
        httpx_mock.add_response(
            url="http://test-site.wikidot.com",
            status_code=301,
            headers={"Location": "https://test-site.wikidot.com"},
        )
        httpx_mock.add_response(
            url="https://test-site.wikidot.com",
            text=html,
        )

        site = Site.from_unix_name(mock_client_no_http, "test-site")

        assert site.id == 123456
        assert site.title == "Test Site Title"
        assert site.unix_name == "test-site"
        assert site.domain == "test-site.wikidot.com"
        assert site.ssl_supported is True

    def test_from_unix_name_non_ssl_site(self, mock_client_no_http: MagicMock, httpx_mock: HTTPXMock) -> None:
        """SSL非対応サイトを正しく取得できる"""
        html = """
        <html>
        <head><title>Old Site</title></head>
        <body>
        <script>
            WIKIREQUEST.info.siteId = 999;
            WIKIREQUEST.info.siteUnixName = "old-site";
            WIKIREQUEST.info.domain = "old-site.wikidot.com";
        </script>
        </body>
        </html>
        """
        httpx_mock.add_response(
            url="http://old-site.wikidot.com",
            text=html,
        )

        site = Site.from_unix_name(mock_client_no_http, "old-site")

        assert site.id == 999
        assert site.ssl_supported is False

    def test_from_unix_name_not_found(self, mock_client_no_http: MagicMock, httpx_mock: HTTPXMock) -> None:
        """存在しないサイトはNotFoundException"""
        httpx_mock.add_response(
            url="http://nonexistent.wikidot.com",
            status_code=404,
        )

        with pytest.raises(NotFoundException):
            Site.from_unix_name(mock_client_no_http, "nonexistent")

    def test_from_unix_name_missing_site_id(self, mock_client_no_http: MagicMock, httpx_mock: HTTPXMock) -> None:
        """siteIdがない場合はUnexpectedException"""
        html = """
        <html>
        <head><title>Bad Site</title></head>
        <body>
        <script>
            WIKIREQUEST.info.siteUnixName = "bad-site";
            WIKIREQUEST.info.domain = "bad-site.wikidot.com";
        </script>
        </body>
        </html>
        """
        httpx_mock.add_response(
            url="http://bad-site.wikidot.com",
            text=html,
        )

        with pytest.raises(UnexpectedException) as exc_info:
            Site.from_unix_name(mock_client_no_http, "bad-site")

        assert "site id" in str(exc_info.value).lower()

    def test_from_unix_name_missing_title(self, mock_client_no_http: MagicMock, httpx_mock: HTTPXMock) -> None:
        """titleがない場合はUnexpectedException"""
        html = """
        <html>
        <head></head>
        <body>
        <script>
            WIKIREQUEST.info.siteId = 123;
            WIKIREQUEST.info.siteUnixName = "no-title";
            WIKIREQUEST.info.domain = "no-title.wikidot.com";
        </script>
        </body>
        </html>
        """
        httpx_mock.add_response(
            url="http://no-title.wikidot.com",
            text=html,
        )

        with pytest.raises(UnexpectedException) as exc_info:
            Site.from_unix_name(mock_client_no_http, "no-title")

        assert "title" in str(exc_info.value).lower()

    def test_from_unix_name_missing_unix_name(self, mock_client_no_http: MagicMock, httpx_mock: HTTPXMock) -> None:
        """siteUnixNameがない場合はUnexpectedException"""
        html = """
        <html>
        <head><title>Site</title></head>
        <body>
        <script>
            WIKIREQUEST.info.siteId = 123;
            WIKIREQUEST.info.domain = "site.wikidot.com";
        </script>
        </body>
        </html>
        """
        httpx_mock.add_response(
            url="http://site.wikidot.com",
            text=html,
        )

        with pytest.raises(UnexpectedException) as exc_info:
            Site.from_unix_name(mock_client_no_http, "site")

        assert "unix_name" in str(exc_info.value).lower()

    def test_from_unix_name_missing_domain(self, mock_client_no_http: MagicMock, httpx_mock: HTTPXMock) -> None:
        """domainがない場合はUnexpectedException"""
        html = """
        <html>
        <head><title>Site</title></head>
        <body>
        <script>
            WIKIREQUEST.info.siteId = 123;
            WIKIREQUEST.info.siteUnixName = "site";
        </script>
        </body>
        </html>
        """
        httpx_mock.add_response(
            url="http://site.wikidot.com",
            text=html,
        )

        with pytest.raises(UnexpectedException) as exc_info:
            Site.from_unix_name(mock_client_no_http, "site")

        assert "domain" in str(exc_info.value).lower()


class TestSiteAmcRequest:
    """Site.amc_request のテスト"""

    def test_amc_request_delegates_to_client(self, mock_client_no_http: MagicMock) -> None:
        """amc_requestはクライアントのAMCクライアントに委譲する"""
        site = Site(
            client=mock_client_no_http,
            id=1,
            title="Test",
            unix_name="test",
            domain="test.wikidot.com",
            ssl_supported=True,
        )
        mock_client_no_http.amc_client.request = MagicMock(return_value=(MagicMock(),))

        site.amc_request([{"moduleName": "Test"}])

        mock_client_no_http.amc_client.request.assert_called_once()
        call_args = mock_client_no_http.amc_client.request.call_args
        assert call_args[0][0] == [{"moduleName": "Test"}]
        assert call_args[0][2] == "test"  # site_name
        assert call_args[0][3] is True  # ssl_supported


class TestSiteInviteUser:
    """Site.invite_user のテスト"""

    def test_invite_user_success(self, site_invite_member_success: dict[str, Any]) -> None:
        """ユーザー招待成功"""
        mock_client = create_mock_client(is_logged_in=True)
        site = Site(
            client=mock_client,
            id=123456,
            title="Test",
            unix_name="test",
            domain="test.wikidot.com",
            ssl_supported=True,
        )

        mock_response = MagicMock()
        mock_response.json.return_value = site_invite_member_success
        mock_client.amc_client.request.return_value = (mock_response,)

        mock_user = MagicMock()
        mock_user.id = 12345
        mock_user.name = "test-user"

        site.invite_user(mock_user, "Welcome message")

        mock_client.amc_client.request.assert_called_once()
        call_args = mock_client.amc_client.request.call_args[0][0][0]
        assert call_args["action"] == "ManageSiteMembershipAction"
        assert call_args["event"] == "inviteMember"
        assert call_args["user_id"] == 12345

    def test_invite_user_already_invited(self, site_invite_member_already_invited: dict[str, Any]) -> None:
        """既に招待済みでTargetErrorException"""
        mock_client = create_mock_client(is_logged_in=True)
        site = Site(
            client=mock_client,
            id=123456,
            title="Test",
            unix_name="test",
            domain="test.wikidot.com",
            ssl_supported=True,
        )

        mock_user = MagicMock()
        mock_user.id = 12345
        mock_user.name = "test-user"

        with patch.object(site, "amc_request") as mock_amc_request:
            mock_amc_request.side_effect = WikidotStatusCodeException(
                site_invite_member_already_invited["message"],
                "already_invited",
            )

            with pytest.raises(TargetErrorException, match="already invited"):
                site.invite_user(mock_user, "Welcome")

    def test_invite_user_already_member(self, site_invite_member_already_member: dict[str, Any]) -> None:
        """既にメンバーでTargetErrorException"""
        mock_client = create_mock_client(is_logged_in=True)
        site = Site(
            client=mock_client,
            id=123456,
            title="Test",
            unix_name="test",
            domain="test.wikidot.com",
            ssl_supported=True,
        )

        mock_user = MagicMock()
        mock_user.id = 12345
        mock_user.name = "test-user"

        with patch.object(site, "amc_request") as mock_amc_request:
            mock_amc_request.side_effect = WikidotStatusCodeException(
                site_invite_member_already_member["message"],
                "already_member",
            )

            with pytest.raises(TargetErrorException, match="already a member"):
                site.invite_user(mock_user, "Welcome")

    def test_invite_user_not_logged_in(self) -> None:
        """未ログインでLoginRequiredException"""
        mock_client = create_mock_client(is_logged_in=False)
        site = Site(
            client=mock_client,
            id=123456,
            title="Test",
            unix_name="test",
            domain="test.wikidot.com",
            ssl_supported=True,
        )

        mock_user = MagicMock()
        mock_user.id = 12345

        with pytest.raises(LoginRequiredException):
            site.invite_user(mock_user, "Welcome")

    def test_invite_user_other_error_reraises(self) -> None:
        """その他のエラーは再送出"""
        mock_client = create_mock_client(is_logged_in=True)
        site = Site(
            client=mock_client,
            id=123456,
            title="Test",
            unix_name="test",
            domain="test.wikidot.com",
            ssl_supported=True,
        )

        mock_user = MagicMock()
        mock_user.id = 12345
        mock_user.name = "test-user"

        with patch.object(site, "amc_request") as mock_amc_request:
            mock_amc_request.side_effect = WikidotStatusCodeException(
                "Some other error",
                "other_error",
            )

            with pytest.raises(WikidotStatusCodeException) as exc_info:
                site.invite_user(mock_user, "Welcome")

            assert exc_info.value.status_code == "other_error"


class TestSiteMemberLookup:
    """Site.member_lookup のテスト"""

    def test_member_lookup_found(self, quickmodule_member_lookup: dict[str, Any]) -> None:
        """メンバーが見つかる場合"""
        mock_client = create_mock_client()
        site = Site(
            client=mock_client,
            id=123456,
            title="Test",
            unix_name="test",
            domain="test.wikidot.com",
            ssl_supported=True,
        )

        with patch("wikidot.module.site.QuickModule.member_lookup") as mock_lookup:
            from wikidot.util.quick_module import QMCUser

            mock_lookup.return_value = [
                QMCUser(id=12345, name="test-user"),
                QMCUser(id=67890, name="test-user-2"),
            ]

            result = site.member_lookup("test-user")

            assert result is True
            mock_lookup.assert_called_once_with(123456, "test-user")

    def test_member_lookup_not_found(self, quickmodule_member_lookup_empty: dict[str, Any]) -> None:
        """メンバーが見つからない場合"""
        mock_client = create_mock_client()
        site = Site(
            client=mock_client,
            id=123456,
            title="Test",
            unix_name="test",
            domain="test.wikidot.com",
            ssl_supported=True,
        )

        with patch("wikidot.module.site.QuickModule.member_lookup") as mock_lookup:
            mock_lookup.return_value = []

            result = site.member_lookup("nonexistent")

            assert result is False

    def test_member_lookup_with_user_id_match(self) -> None:
        """ユーザーIDも一致する場合"""
        mock_client = create_mock_client()
        site = Site(
            client=mock_client,
            id=123456,
            title="Test",
            unix_name="test",
            domain="test.wikidot.com",
            ssl_supported=True,
        )

        with patch("wikidot.module.site.QuickModule.member_lookup") as mock_lookup:
            from wikidot.util.quick_module import QMCUser

            mock_lookup.return_value = [QMCUser(id=12345, name="test-user")]

            result = site.member_lookup("test-user", user_id=12345)

            assert result is True

    def test_member_lookup_with_user_id_mismatch(self) -> None:
        """ユーザーIDが不一致の場合"""
        mock_client = create_mock_client()
        site = Site(
            client=mock_client,
            id=123456,
            title="Test",
            unix_name="test",
            domain="test.wikidot.com",
            ssl_supported=True,
        )

        with patch("wikidot.module.site.QuickModule.member_lookup") as mock_lookup:
            from wikidot.util.quick_module import QMCUser

            mock_lookup.return_value = [QMCUser(id=12345, name="test-user")]

            result = site.member_lookup("test-user", user_id=99999)

            assert result is False


class TestSiteGetRecentChanges:
    """Site.get_recent_changes のテスト"""

    def test_get_recent_changes_success(self, site_changes: dict[str, Any]) -> None:
        """変更履歴取得成功"""
        mock_client = create_mock_client()
        site = Site(
            client=mock_client,
            id=123456,
            title="Test",
            unix_name="test",
            domain="test.wikidot.com",
            ssl_supported=True,
        )

        mock_response = MagicMock()
        mock_response.json.return_value = site_changes
        mock_client.amc_client.request.return_value = (mock_response,)

        with patch("wikidot.module.site.user_parser") as mock_user_parser:
            mock_user = MagicMock()
            mock_user_parser.return_value = mock_user

            changes = site.get_recent_changes()

            assert len(changes) == 2
            assert changes[0].page_fullname == "test:test-page"
            assert changes[0].page_title == "test:\nTest Page Title"
            assert changes[0].revision_no == 3
            assert "S" in changes[0].flags
            assert changes[0].comment == "Test edit comment"
            assert changes[1].page_fullname == "scp-001"
            assert changes[1].revision_no == 1
            assert "N" in changes[1].flags

    def test_get_recent_changes_empty(self, site_changes_empty: dict[str, Any]) -> None:
        """変更履歴が空の場合"""
        mock_client = create_mock_client()
        site = Site(
            client=mock_client,
            id=123456,
            title="Test",
            unix_name="test",
            domain="test.wikidot.com",
            ssl_supported=True,
        )

        mock_response = MagicMock()
        mock_response.json.return_value = site_changes_empty
        mock_client.amc_client.request.return_value = (mock_response,)

        changes = site.get_recent_changes()

        assert len(changes) == 0

    def test_get_recent_changes_with_limit(self, site_changes: dict[str, Any]) -> None:
        """limit指定時"""
        mock_client = create_mock_client()
        site = Site(
            client=mock_client,
            id=123456,
            title="Test",
            unix_name="test",
            domain="test.wikidot.com",
            ssl_supported=True,
        )

        mock_response = MagicMock()
        mock_response.json.return_value = site_changes
        mock_client.amc_client.request.return_value = (mock_response,)

        with patch("wikidot.module.site.user_parser") as mock_user_parser:
            mock_user = MagicMock()
            mock_user_parser.return_value = mock_user

            changes = site.get_recent_changes(limit=1)

            assert len(changes) == 1
            assert changes[0].page_fullname == "test:test-page"
