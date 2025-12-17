"""Siteモジュールのユニットテスト"""

from unittest.mock import MagicMock

import pytest
from pytest_httpx import HTTPXMock

from wikidot.common.exceptions import NotFoundException, UnexpectedException
from wikidot.module.site import Site


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

    def test_from_unix_name_ssl_site(
        self, mock_client_no_http: MagicMock, httpx_mock: HTTPXMock
    ) -> None:
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

    def test_from_unix_name_non_ssl_site(
        self, mock_client_no_http: MagicMock, httpx_mock: HTTPXMock
    ) -> None:
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

    def test_from_unix_name_not_found(
        self, mock_client_no_http: MagicMock, httpx_mock: HTTPXMock
    ) -> None:
        """存在しないサイトはNotFoundException"""
        httpx_mock.add_response(
            url="http://nonexistent.wikidot.com",
            status_code=404,
        )

        with pytest.raises(NotFoundException):
            Site.from_unix_name(mock_client_no_http, "nonexistent")

    def test_from_unix_name_missing_site_id(
        self, mock_client_no_http: MagicMock, httpx_mock: HTTPXMock
    ) -> None:
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

    def test_from_unix_name_missing_title(
        self, mock_client_no_http: MagicMock, httpx_mock: HTTPXMock
    ) -> None:
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

    def test_from_unix_name_missing_unix_name(
        self, mock_client_no_http: MagicMock, httpx_mock: HTTPXMock
    ) -> None:
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

    def test_from_unix_name_missing_domain(
        self, mock_client_no_http: MagicMock, httpx_mock: HTTPXMock
    ) -> None:
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

    def test_amc_request_delegates_to_client(
        self, mock_client_no_http: MagicMock
    ) -> None:
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
