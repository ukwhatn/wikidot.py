"""SiteToolsAccessorモジュールのユニットテスト"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from wikidot.module.site_tools import SiteToolsAccessor

if TYPE_CHECKING:
    from wikidot.module.site import Site


def _mock_response(data: dict) -> MagicMock:
    response = MagicMock()
    response.json.return_value = data
    return response


class TestSiteToolsAccessorInit:
    """Site.toolsアクセサ経由での取得テスト"""

    def test_site_has_tools_accessor(self, mock_site_no_http: Site) -> None:
        assert isinstance(mock_site_no_http.tools, SiteToolsAccessor)
        assert mock_site_no_http.tools.site is mock_site_no_http


class TestSiteToolsSimpleViews:
    """パラメータなしのビュー取得系メソッドのテスト"""

    def test_get_overview(self, mock_site_no_http: Site) -> None:
        mock_site_no_http.amc_request = MagicMock(
            return_value=[_mock_response({"status": "ok", "body": "<div>overview</div>"})]
        )
        assert mock_site_no_http.tools.get_overview() == "<div>overview</div>"
        body = mock_site_no_http.amc_request.call_args[0][0][0]
        assert body["moduleName"] == "sitetools/SiteToolsModule"

    def test_get_orphaned_pages(self, mock_site_no_http: Site) -> None:
        mock_site_no_http.amc_request = MagicMock(
            return_value=[_mock_response({"status": "ok", "body": "<div>orphaned</div>"})]
        )
        assert mock_site_no_http.tools.get_orphaned_pages() == "<div>orphaned</div>"

    def test_get_drafts(self, mock_site_no_http: Site) -> None:
        mock_site_no_http.amc_request = MagicMock(
            return_value=[_mock_response({"status": "ok", "body": "<div>drafts</div>"})]
        )
        assert mock_site_no_http.tools.get_drafts() == "<div>drafts</div>"
        body = mock_site_no_http.amc_request.call_args[0][0][0]
        assert body["location"] == "sitetools"

    def test_get_categories(self, mock_site_no_http: Site) -> None:
        mock_site_no_http.amc_request = MagicMock(
            return_value=[_mock_response({"status": "ok", "body": "<div>categories</div>"})]
        )
        assert mock_site_no_http.tools.get_categories() == "<div>categories</div>"


class TestSiteToolsWantedPages:
    """get_wanted_pagesのテスト"""

    def test_get_wanted_pages_default(self, mock_site_no_http: Site) -> None:
        mock_site_no_http.amc_request = MagicMock(
            return_value=[_mock_response({"status": "ok", "body": "<div>wanted</div>"})]
        )
        mock_site_no_http.tools.get_wanted_pages()
        body = mock_site_no_http.amc_request.call_args[0][0][0]
        assert "p" not in body
        assert "embed" not in body

    def test_get_wanted_pages_with_params(self, mock_site_no_http: Site) -> None:
        mock_site_no_http.amc_request = MagicMock(
            return_value=[_mock_response({"status": "ok", "body": "<div>wanted</div>"})]
        )
        mock_site_no_http.tools.get_wanted_pages(page=2, embed=True)
        body = mock_site_no_http.amc_request.call_args[0][0][0]
        assert body["p"] == 2
        assert body["embed"] == "true"


class TestSiteToolsExpandCategory:
    """expand_categoryのテスト"""

    def test_expand_category(self, mock_site_no_http: Site) -> None:
        mock_site_no_http.amc_request = MagicMock(
            return_value=[_mock_response({"status": "ok", "body": "<div>pages</div>", "categoryId": 5})]
        )
        result = mock_site_no_http.tools.expand_category(5)
        assert result == "<div>pages</div>"
        body = mock_site_no_http.amc_request.call_args[0][0][0]
        assert body["category_id"] == 5
        assert "includeHidden" not in body

    def test_expand_category_include_hidden(self, mock_site_no_http: Site) -> None:
        mock_site_no_http.amc_request = MagicMock(
            return_value=[_mock_response({"status": "ok", "body": "<div>pages</div>"})]
        )
        mock_site_no_http.tools.expand_category(5, include_hidden=True)
        body = mock_site_no_http.amc_request.call_args[0][0][0]
        assert body["includeHidden"] == "true"


class TestSiteToolsRecentChanges:
    """get_recent_changesのテスト"""

    def test_default_options_is_all(self, mock_site_no_http: Site) -> None:
        mock_site_no_http.amc_request = MagicMock(
            return_value=[_mock_response({"status": "ok", "body": "<div></div>"})]
        )
        mock_site_no_http.tools.get_recent_changes()
        body = mock_site_no_http.amc_request.call_args[0][0][0]
        assert json.loads(body["options"]) == {"all": True}
        assert "categoryId" not in body
        assert "pageId" not in body

    def test_category_and_page_filter(self, mock_site_no_http: Site) -> None:
        mock_site_no_http.amc_request = MagicMock(
            return_value=[_mock_response({"status": "ok", "body": "<div></div>"})]
        )
        mock_site_no_http.tools.get_recent_changes(category_id=3, page_id=99)
        body = mock_site_no_http.amc_request.call_args[0][0][0]
        assert body["categoryId"] == 3
        assert body["pageId"] == 99

    def test_parses_changes(self, mock_site_no_http: Site) -> None:
        printuser_html = (
            '<span class="printuser avatarhover">'
            '<a href="http://www.wikidot.com/user:info/test-user" '
            'onclick="WIKIDOT.page.listeners.userInfo(12345); return false;">test-user</a>'
            "</span>"
        )
        html = (
            '<div class="changes-list-item">'
            '<td class="title"><a href="/component:scp-173">SCP-173</a></td>'
            '<td class="revision-no">3</td>'
            f'<td class="mod-by">{printuser_html}</td>'
            '<td class="mod-date"><span class="odate time_1700000000">14 Nov 2023</span></td>'
            '<td class="comments">edit note</td>'
            '<td class="flags"><span>S</span></td>'
            "</div>"
        )
        mock_site_no_http.amc_request = MagicMock(return_value=[_mock_response({"status": "ok", "body": html})])

        changes = mock_site_no_http.tools.get_recent_changes()

        assert len(changes) == 1
        assert changes[0].page_fullname == "component:scp-173"
        assert changes[0].page_title == "SCP-173"
        assert changes[0].revision_no == 3
        assert changes[0].comment == "edit note"
        assert changes[0].flags == ["S"]
