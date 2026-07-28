"""
ページリビジョンモジュールのユニットテスト

PageRevision, PageRevisionCollectionクラスをテストする。
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from wikidot.module.page_revision import PageRevision, PageRevisionCollection


@pytest.fixture
def mock_page():
    """モックページ"""
    page = MagicMock()
    page.site = MagicMock()
    page.site.amc_request = MagicMock()
    return page


@pytest.fixture
def mock_user():
    """モックユーザー"""
    user = MagicMock()
    user.id = 12345
    user.name = "test-user"
    return user


@pytest.fixture
def sample_revision(mock_page, mock_user):
    """サンプルリビジョン"""
    return PageRevision(
        page=mock_page,
        id=100,
        rev_no=1,
        created_by=mock_user,
        created_at=datetime(2023, 1, 1, 12, 0, 0),
        comment="Initial revision",
    )


class TestPageRevisionCollection:
    """PageRevisionCollectionクラスのテスト"""

    def test_init_empty(self):
        """空のコレクションの初期化"""
        collection = PageRevisionCollection()
        assert len(collection) == 0
        assert collection.page is None

    def test_init_with_page(self, mock_page, sample_revision):
        """ページを指定した初期化"""
        collection = PageRevisionCollection(page=mock_page, revisions=[sample_revision])
        assert len(collection) == 1
        assert collection.page == mock_page

    def test_init_infers_page_from_revision(self, sample_revision):
        """リビジョンからページを推測"""
        collection = PageRevisionCollection(revisions=[sample_revision])
        assert collection.page == sample_revision.page

    def test_iter(self, sample_revision):
        """イテレータのテスト"""
        collection = PageRevisionCollection(revisions=[sample_revision])
        revisions = list(collection)
        assert len(revisions) == 1
        assert revisions[0] == sample_revision

    def test_find_existing(self, sample_revision):
        """存在するリビジョンの検索"""
        collection = PageRevisionCollection(revisions=[sample_revision])
        result = collection.find(100)
        assert result == sample_revision

    def test_find_not_existing(self, sample_revision):
        """存在しないリビジョンの検索"""
        collection = PageRevisionCollection(revisions=[sample_revision])
        result = collection.find(999)
        assert result is None

    def test_get_sources_requires_page(self):
        """get_sourcesはpageが必要"""
        collection = PageRevisionCollection()
        with pytest.raises(ValueError) as exc_info:
            collection.get_sources()
        assert "Page is not set" in str(exc_info.value)

    def test_get_sources_success(self, mock_page, sample_revision):
        """get_sourcesの成功ケース"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"body": '<div class="page-source">Test wiki text</div>'}
        mock_page.site.amc_request.return_value = [mock_response]

        collection = PageRevisionCollection(page=mock_page, revisions=[sample_revision])
        result = collection.get_sources()

        assert result == collection
        assert sample_revision._source is not None
        assert sample_revision._source.wiki_text == "Test wiki text"

    def test_get_sources_skips_already_acquired(self, mock_page, sample_revision):
        """既に取得済みのソースはスキップ"""
        sample_revision._source = MagicMock()

        collection = PageRevisionCollection(page=mock_page, revisions=[sample_revision])
        result = collection.get_sources()

        mock_page.site.amc_request.assert_not_called()
        assert result == collection

    def test_get_htmls_requires_page(self):
        """get_htmlsはpageが必要"""
        collection = PageRevisionCollection()
        with pytest.raises(ValueError) as exc_info:
            collection.get_htmls()
        assert "Page is not set" in str(exc_info.value)

    def test_get_htmls_success(self, mock_page, sample_revision):
        """get_htmlsの成功ケース"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "body": "onclick=\"document.getElementById('page-version-info').style.display='none'\">close</a>\n\t</div>\n\n\n\n<p>Test HTML content</p>"
        }
        mock_page.site.amc_request.return_value = [mock_response]

        collection = PageRevisionCollection(page=mock_page, revisions=[sample_revision])
        result = collection.get_htmls()

        assert result == collection
        assert sample_revision._html is not None
        assert "<p>Test HTML content</p>" in sample_revision._html

    def test_get_htmls_skips_already_acquired(self, mock_page, sample_revision):
        """既に取得済みのHTMLはスキップ"""
        sample_revision._html = "<p>Already acquired</p>"

        collection = PageRevisionCollection(page=mock_page, revisions=[sample_revision])
        result = collection.get_htmls()

        mock_page.site.amc_request.assert_not_called()
        assert result == collection


class TestPageRevision:
    """PageRevisionクラスのテスト"""

    def test_is_source_acquired_false(self, sample_revision):
        """ソース未取得の確認"""
        assert sample_revision.is_source_acquired() is False

    def test_is_source_acquired_true(self, sample_revision):
        """ソース取得済みの確認"""
        sample_revision._source = MagicMock()
        assert sample_revision.is_source_acquired() is True

    def test_is_html_acquired_false(self, sample_revision):
        """HTML未取得の確認"""
        assert sample_revision.is_html_acquired() is False

    def test_is_html_acquired_true(self, sample_revision):
        """HTML取得済みの確認"""
        sample_revision._html = "<p>Test</p>"
        assert sample_revision.is_html_acquired() is True

    def test_source_property_lazy_load(self, mock_page, sample_revision):
        """sourceプロパティの遅延読み込み"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"body": '<div class="page-source">Lazy loaded text</div>'}
        mock_page.site.amc_request.return_value = [mock_response]

        result = sample_revision.source

        mock_page.site.amc_request.assert_called_once()
        assert result is not None

    def test_source_property_uses_cache(self, sample_revision):
        """sourceプロパティがキャッシュを使用"""
        mock_source = MagicMock()
        sample_revision._source = mock_source

        result = sample_revision.source

        assert result == mock_source

    def test_source_setter(self, sample_revision):
        """sourceセッター"""
        mock_source = MagicMock()
        sample_revision.source = mock_source
        assert sample_revision._source == mock_source

    def test_html_property_lazy_load(self, mock_page, sample_revision):
        """htmlプロパティの遅延読み込み"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "body": "onclick=\"document.getElementById('page-version-info').style.display='none'\">close</a>\n\t</div>\n\n\n\n<p>Lazy HTML</p>"
        }
        mock_page.site.amc_request.return_value = [mock_response]

        result = sample_revision.html

        mock_page.site.amc_request.assert_called_once()
        assert result is not None

    def test_html_property_uses_cache(self, sample_revision):
        """htmlプロパティがキャッシュを使用"""
        sample_revision._html = "<p>Cached HTML</p>"

        result = sample_revision.html

        assert result == "<p>Cached HTML</p>"

    def test_html_setter(self, sample_revision):
        """htmlセッター"""
        sample_revision.html = "<p>New HTML</p>"
        assert sample_revision._html == "<p>New HTML</p>"


class TestPageRevisionCollectionGetDiff:
    """PageRevisionCollection.get_diffのテスト"""

    def test_get_diff_returns_body(self, mock_page):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok", "body": "<div>diff</div>"}
        mock_page.site.amc_request.return_value = [mock_response]

        result = PageRevisionCollection.get_diff(mock_page, from_revision_id=1, to_revision_id=2)

        assert result == "<div>diff</div>"
        body = mock_page.site.amc_request.call_args[0][0][0]
        assert body["moduleName"] == "history/PageDiffModule"
        assert body["from_revision_id"] == 1
        assert body["to_revision_id"] == 2
        assert body["show_type"] == "inline"


class TestPageRevisionCollectionAcquire:
    """PageRevisionCollection.acquire（履歴の絞り込み）のテスト"""

    def test_acquire_defaults_to_all(self, mock_page):
        import json as json_module

        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok", "body": "<table class='page-history'></table>"}
        mock_page.site.amc_request.return_value = [mock_response]

        result = PageRevisionCollection.acquire(mock_page)

        assert len(result) == 0
        body = mock_page.site.amc_request.call_args[0][0][0]
        assert json_module.loads(body["options"]) == {"all": True}
        assert body["perpage"] == 20
        assert body["page"] == 1

    def test_acquire_with_options_filter(self, mock_page):
        import json as json_module

        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok", "body": "<table class='page-history'></table>"}
        mock_page.site.amc_request.return_value = [mock_response]

        PageRevisionCollection.acquire(mock_page, options={"tags": True, "move": True}, perpage=50, page_no=2)

        body = mock_page.site.amc_request.call_args[0][0][0]
        assert json_module.loads(body["options"]) == {"tags": True, "move": True}
        assert body["perpage"] == 50
        assert body["page"] == 2

    def test_acquire_parses_revisions(self, mock_page, mock_user):
        printuser_html = (
            '<span class="printuser avatarhover">'
            '<a href="http://www.wikidot.com/user:info/test-user" '
            'onclick="WIKIDOT.page.listeners.userInfo(12345); return false;">test-user</a>'
            "</span>"
        )
        html = (
            '<table class="page-history">'
            '<tr id="revision-row-100">'
            "<td>3.</td><td></td><td></td><td></td>"
            f"<td>{printuser_html}</td>"
            '<td><span class="odate time_1700000000">14 Nov 2023</span></td>'
            "<td>edit comment</td>"
            "</tr>"
            "</table>"
        )
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok", "body": html}
        mock_page.site.amc_request.return_value = [mock_response]

        result = PageRevisionCollection.acquire(mock_page)

        assert len(result) == 1
        assert result[0].id == 100
        assert result[0].rev_no == 3
        assert result[0].comment == "edit comment"


class TestPageRevisionRevert:
    """PageRevision.revertのテスト"""

    def test_revert_success(self, mock_page, sample_revision):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok"}
        mock_page.site.amc_request.return_value = [mock_response]

        result = sample_revision.revert()

        assert result == {"status": "ok"}
        body = mock_page.site.amc_request.call_args[0][0][0]
        assert body["action"] == "WikiPageAction"
        assert body["event"] == "revert"
        assert body["pageId"] == mock_page.id
        assert body["revisionId"] == sample_revision.id
        assert "force" not in body

    def test_revert_force(self, mock_page, sample_revision):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok"}
        mock_page.site.amc_request.return_value = [mock_response]

        sample_revision.revert(force=True)

        body = mock_page.site.amc_request.call_args[0][0][0]
        assert body["force"] == "yes"

    def test_revert_locked_response_not_swallowed(self, mock_page, sample_revision):
        """locks応答を握りつぶさず、呼び出し側にそのまま返す"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok", "locks": True, "body": "<div>locked</div>"}
        mock_page.site.amc_request.return_value = [mock_response]

        result = sample_revision.revert()

        assert result["locks"] is True
        assert result["body"] == "<div>locked</div>"
