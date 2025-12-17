"""Pageモジュールのユニットテスト"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest
from bs4 import BeautifulSoup

from wikidot.common import exceptions
from wikidot.module.page import Page, PageCollection, SearchPagesQuery

if TYPE_CHECKING:
    from wikidot.module.site import Site


# ============================================================
# SearchPagesQueryテスト
# ============================================================


class TestSearchPagesQuery:
    """SearchPagesQueryのテスト"""

    def test_default_values(self) -> None:
        """デフォルト値が正しく設定される"""
        query = SearchPagesQuery()
        # デフォルトは "*"
        assert query.category == "*"
        assert query.pagetype == "*"
        # Noneのデフォルト
        assert query.tags is None
        assert query.parent is None
        assert query.fullname is None
        assert query.rating is None
        assert query.votes is None
        assert query.created_by is None
        assert query.created_at is None
        assert query.updated_at is None
        # その他のデフォルト
        assert query.order == "created_at desc"
        assert query.offset == 0
        assert query.limit is None
        assert query.range is None

    def test_as_dict_basic(self) -> None:
        """基本的な値を辞書に変換できる"""
        query = SearchPagesQuery(
            category="_default",
            fullname="test-page",
            limit=10,
        )
        result = query.as_dict()
        assert result["category"] == "_default"
        assert result["fullname"] == "test-page"
        assert result["limit"] == 10

    def test_as_dict_with_tags_list(self) -> None:
        """タグリストが正しくスペース区切りに変換される"""
        query = SearchPagesQuery(tags=["tag1", "tag2", "tag3"])
        result = query.as_dict()
        assert result["tags"] == "tag1 tag2 tag3"

    def test_as_dict_with_tags_string(self) -> None:
        """文字列タグがそのまま保持される"""
        query = SearchPagesQuery(tags="tag1 tag2")
        result = query.as_dict()
        assert result["tags"] == "tag1 tag2"

    def test_as_dict_excludes_none(self) -> None:
        """None値は辞書に含まれない"""
        query = SearchPagesQuery(fullname="test-page", tags=None, parent=None)
        result = query.as_dict()
        # tagsとparentはNoneなので含まれない
        assert "tags" not in result
        assert "parent" not in result
        # fullnameは設定されているので含まれる
        assert "fullname" in result

    def test_as_dict_range(self) -> None:
        """rangeが正しく含まれる"""
        query = SearchPagesQuery(range="before")
        result = query.as_dict()
        assert "range" in result
        assert result["range"] == "before"

    def test_custom_values(self) -> None:
        """カスタム値が正しく設定される"""
        query = SearchPagesQuery(
            category="component",
            tags=["scp", "euclid"],
            parent="parent-page",
            rating=">=10",
            order="rating desc",
            limit=50,
            offset=20,
        )
        result = query.as_dict()
        assert result["category"] == "component"
        assert result["tags"] == "scp euclid"
        assert result["parent"] == "parent-page"
        assert result["rating"] == ">=10"
        assert result["order"] == "rating desc"
        assert result["limit"] == 50
        assert result["offset"] == 20


# ============================================================
# PageCollectionテスト
# ============================================================


class TestPageCollectionInit:
    """PageCollectionの初期化テスト"""

    def test_init_with_site_and_empty_pages(self, mock_site_no_http: Site) -> None:
        """サイトと空のページリストで初期化できる"""
        collection = PageCollection(mock_site_no_http, [])
        assert collection.site == mock_site_no_http
        assert len(collection) == 0

    def test_init_with_site_and_pages(self, mock_site_no_http: Site, mock_page_no_http: Page) -> None:
        """サイトとページリストで初期化できる"""
        collection = PageCollection(mock_site_no_http, [mock_page_no_http])
        assert collection.site == mock_site_no_http
        assert len(collection) == 1

    def test_find_existing_page(self, mock_site_no_http: Site, mock_page_no_http: Page) -> None:
        """存在するページをfullnameで検索できる"""
        collection = PageCollection(mock_site_no_http, [mock_page_no_http])
        found = collection.find("test-page")
        assert found is not None
        assert found.fullname == "test-page"

    def test_find_nonexistent_page(self, mock_site_no_http: Site) -> None:
        """存在しないページを検索するとNoneを返す"""
        collection = PageCollection(mock_site_no_http, [])
        found = collection.find("nonexistent")
        assert found is None


class TestPageCollectionParse:
    """PageCollection._parseのテスト"""

    def test_parse_single_page(self, mock_site_no_http: Site, page_listpages_single: dict[str, Any]) -> None:
        """単一ページをパースできる"""
        html_body = BeautifulSoup(page_listpages_single["body"], "lxml")
        pages = PageCollection._parse(mock_site_no_http, html_body)
        assert len(pages) == 1
        page = pages[0]
        assert page.fullname == "scp-001"
        assert page.title == "SCP-001"
        assert page.rating == 100

    def test_parse_multiple_pages(self, mock_site_no_http: Site, page_listpages_multiple: dict[str, Any]) -> None:
        """複数ページをパースできる"""
        html_body = BeautifulSoup(page_listpages_multiple["body"], "lxml")
        pages = PageCollection._parse(mock_site_no_http, html_body)
        assert len(pages) == 2
        assert pages[0].fullname == "scp-001"
        assert pages[1].fullname == "scp-002"

    def test_parse_empty_result(self, mock_site_no_http: Site, page_listpages_empty: dict[str, Any]) -> None:
        """空結果をパースできる"""
        html_body = BeautifulSoup(page_listpages_empty["body"], "lxml")
        pages = PageCollection._parse(mock_site_no_http, html_body)
        assert len(pages) == 0

    def test_parse_with_pm_rating(self, mock_site_no_http: Site, page_listpages_pm_rating: dict[str, Any]) -> None:
        """PM評価システムを正しくパースする"""
        html_body = BeautifulSoup(page_listpages_pm_rating["body"], "lxml")
        pages = PageCollection._parse(mock_site_no_http, html_body)
        assert len(pages) == 1
        # Note: rating_percent is None for non-5star rating (no span.page-rate-list-pages-start)
        assert pages[0].rating == 75
        assert pages[0].votes_count == 10

    def test_parse_missing_optional_fields(
        self, mock_site_no_http: Site, page_listpages_missing_fields: dict[str, Any]
    ) -> None:
        """オプションフィールドがなくてもパースできる"""
        html_body = BeautifulSoup(page_listpages_missing_fields["body"], "lxml")
        pages = PageCollection._parse(mock_site_no_http, html_body)
        assert len(pages) == 1
        assert pages[0].tags == []
        # 値が空の場合はNoneになる（実際のWikidotレスポンスでは値spanがない）
        assert pages[0].parent_fullname is None
        assert pages[0].rating_percent is None

    def test_parse_no_element_exception(self, mock_site_no_http: Site, page_listpages_invalid: dict[str, Any]) -> None:
        """必須要素がない場合にNoElementExceptionを送出"""
        html_body = BeautifulSoup(page_listpages_invalid["body"], "lxml")
        with pytest.raises(exceptions.NoElementException):
            PageCollection._parse(mock_site_no_http, html_body)


class TestPageCollectionSearchPages:
    """PageCollection.search_pagesのテスト"""

    def test_search_pages_basic(self, mock_site_no_http: Site, page_listpages_single: dict[str, Any]) -> None:
        """基本的なページ検索ができる"""
        mock_response = MagicMock()
        mock_response.json.return_value = page_listpages_single
        mock_site_no_http.amc_request = MagicMock(return_value=[mock_response])

        pages = PageCollection.search_pages(mock_site_no_http, SearchPagesQuery())
        assert len(pages) == 1
        assert pages[0].fullname == "scp-001"

    def test_search_pages_with_query(self, mock_site_no_http: Site, page_listpages_single: dict[str, Any]) -> None:
        """クエリパラメータを指定して検索できる"""
        mock_response = MagicMock()
        mock_response.json.return_value = page_listpages_single
        mock_site_no_http.amc_request = MagicMock(return_value=[mock_response])

        query = SearchPagesQuery(
            category="scp",
            tags=["euclid"],
            limit=10,
        )
        PageCollection.search_pages(mock_site_no_http, query)

        # amc_requestが正しいパラメータで呼ばれたか確認
        call_args = mock_site_no_http.amc_request.call_args
        request_body = call_args[0][0][0]
        assert request_body["category"] == "scp"
        assert request_body["tags"] == "euclid"
        assert request_body["limit"] == 10

    def test_search_pages_forbidden(self, mock_site_no_http: Site) -> None:
        """アクセス禁止時に空のコレクションを返す"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "ok",
            "body": '<p class="error-block">You are not allowed to access this page.</p>',
        }
        mock_site_no_http.amc_request = MagicMock(return_value=[mock_response])

        pages = PageCollection.search_pages(mock_site_no_http, SearchPagesQuery())
        assert len(pages) == 0


class TestPageCollectionAcquire:
    """PageCollection._acquire_*メソッドのテスト"""

    def test_acquire_sources_success(
        self, mock_site_no_http: Site, mock_page_with_id: Page, page_viewsource: dict[str, Any]
    ) -> None:
        """ソースを正常に取得できる"""
        collection = PageCollection(mock_site_no_http, [mock_page_with_id])

        mock_response = MagicMock()
        mock_response.json.return_value = page_viewsource
        mock_site_no_http.amc_request = MagicMock(return_value=[mock_response])

        collection.get_page_sources()
        assert mock_page_with_id._source is not None
        # フィクスチャの内容に合わせて検証
        assert "page content" in mock_page_with_id._source.wiki_text

    def test_acquire_revisions_success(
        self, mock_site_no_http: Site, mock_page_with_id: Page, page_revisionlist: dict[str, Any]
    ) -> None:
        """リビジョン一覧を正常に取得できる"""
        collection = PageCollection(mock_site_no_http, [mock_page_with_id])

        mock_response = MagicMock()
        mock_response.json.return_value = page_revisionlist
        mock_site_no_http.amc_request = MagicMock(return_value=[mock_response])

        collection.get_page_revisions()
        assert mock_page_with_id._revisions is not None
        # フィクスチャには3つのリビジョン
        assert len(mock_page_with_id._revisions) == 3

    def test_acquire_votes_success(
        self, mock_site_no_http: Site, mock_page_with_id: Page, page_whorated: dict[str, Any]
    ) -> None:
        """投票情報を正常に取得できる"""
        collection = PageCollection(mock_site_no_http, [mock_page_with_id])

        mock_response = MagicMock()
        mock_response.json.return_value = page_whorated
        mock_site_no_http.amc_request = MagicMock(return_value=[mock_response])

        collection.get_page_votes()
        assert mock_page_with_id._votes is not None


# ============================================================
# Pageテスト
# ============================================================


class TestPageProperties:
    """Pageのプロパティテスト"""

    def test_get_url(self, mock_page_no_http: Page) -> None:
        """URLが正しく生成される"""
        url = mock_page_no_http.get_url()
        assert url == "https://test-site.wikidot.com/test-page"

    def test_id_property_acquired(self, mock_page_with_id: Page) -> None:
        """取得済みIDが返される"""
        assert mock_page_with_id.id == 12345

    def test_source_property_auto_acquire(self, mock_page_with_id: Page, page_viewsource: dict[str, Any]) -> None:
        """ソースが未取得の場合自動取得する"""
        mock_response = MagicMock()
        mock_response.json.return_value = page_viewsource
        mock_page_with_id.site.amc_request = MagicMock(return_value=[mock_response])

        source = mock_page_with_id.source
        assert "page content" in source.wiki_text

    def test_revisions_property(self, mock_page_with_id: Page, page_revisionlist: dict[str, Any]) -> None:
        """リビジョンプロパティが正しく動作する"""
        mock_response = MagicMock()
        mock_response.json.return_value = page_revisionlist
        mock_page_with_id.site.amc_request = MagicMock(return_value=[mock_response])

        revisions = mock_page_with_id.revisions
        assert len(revisions) == 3

    def test_latest_revision(self, mock_page_with_id: Page, page_revisionlist: dict[str, Any]) -> None:
        """最新リビジョンを取得できる"""
        mock_response = MagicMock()
        mock_response.json.return_value = page_revisionlist
        mock_page_with_id.site.amc_request = MagicMock(return_value=[mock_response])
        mock_page_with_id.revisions_count = 3

        latest = mock_page_with_id.latest_revision
        assert latest.rev_no == 3

    def test_latest_revision_not_found(self, mock_page_with_id: Page) -> None:
        """最新リビジョンが見つからない場合に例外"""
        from wikidot.module.page import PageRevision, PageRevisionCollection

        # revisions_countと一致しないrev_noのリビジョンを設定
        mock_page_with_id.revisions_count = 5
        mock_page_with_id._revisions = PageRevisionCollection(
            mock_page_with_id,
            [
                PageRevision(
                    page=mock_page_with_id,
                    id=100,
                    rev_no=1,
                    created_by=None,
                    created_at=None,
                    comment="",
                )
            ],
        )

        with pytest.raises(exceptions.NotFoundException):
            _ = mock_page_with_id.latest_revision


class TestPageWriteMethods:
    """Pageの書き込み系メソッドテスト"""

    def test_destroy_success(self, mock_page_with_id: Page, page_delete_success: dict[str, Any]) -> None:
        """ページを正常に削除できる"""
        mock_response = MagicMock()
        mock_response.json.return_value = page_delete_success
        mock_page_with_id.site.amc_request = MagicMock(return_value=[mock_response])
        mock_page_with_id.site.client.is_logged_in = True
        mock_page_with_id.site.client.login_check = MagicMock()

        # 例外が発生しなければOK
        mock_page_with_id.destroy()
        mock_page_with_id.site.amc_request.assert_called_once()

    def test_destroy_not_logged_in(self, mock_page_with_id: Page) -> None:
        """ログインしていない場合に例外"""
        mock_page_with_id.site.client.is_logged_in = False
        mock_page_with_id.site.client.login_check = MagicMock(
            side_effect=exceptions.LoginRequiredException("Login required")
        )

        with pytest.raises(exceptions.LoginRequiredException):
            mock_page_with_id.destroy()

    def test_commit_tags_success(self, mock_page_with_id: Page, page_savetags_success: dict[str, Any]) -> None:
        """タグを正常に保存できる"""
        mock_response = MagicMock()
        mock_response.json.return_value = page_savetags_success
        mock_page_with_id.site.amc_request = MagicMock(return_value=[mock_response])
        mock_page_with_id.site.client.is_logged_in = True
        mock_page_with_id.site.client.login_check = MagicMock()

        result = mock_page_with_id.commit_tags()
        assert result == mock_page_with_id

    def test_commit_tags_not_logged_in(self, mock_page_with_id: Page) -> None:
        """ログインしていない場合に例外"""
        mock_page_with_id.site.client.is_logged_in = False
        mock_page_with_id.site.client.login_check = MagicMock(
            side_effect=exceptions.LoginRequiredException("Login required")
        )

        with pytest.raises(exceptions.LoginRequiredException):
            mock_page_with_id.commit_tags()

    def test_set_parent_success(self, mock_page_with_id: Page, page_setparent_success: dict[str, Any]) -> None:
        """親ページを正常に設定できる"""
        mock_response = MagicMock()
        mock_response.json.return_value = page_setparent_success
        mock_page_with_id.site.amc_request = MagicMock(return_value=[mock_response])
        mock_page_with_id.site.client.is_logged_in = True
        mock_page_with_id.site.client.login_check = MagicMock()

        result = mock_page_with_id.set_parent("parent-page")
        assert result.parent_fullname == "parent-page"

    def test_set_parent_clear(self, mock_page_with_id: Page, page_setparent_success: dict[str, Any]) -> None:
        """親ページをクリアできる"""
        mock_response = MagicMock()
        mock_response.json.return_value = page_setparent_success
        mock_page_with_id.site.amc_request = MagicMock(return_value=[mock_response])
        mock_page_with_id.site.client.is_logged_in = True
        mock_page_with_id.site.client.login_check = MagicMock()

        result = mock_page_with_id.set_parent(None)
        assert result.parent_fullname is None

    def test_rename_success(self, mock_page_with_id: Page, page_rename_success: dict[str, Any]) -> None:
        """ページ名を正常に変更できる"""
        mock_response = MagicMock()
        mock_response.json.return_value = page_rename_success
        mock_page_with_id.site.amc_request = MagicMock(return_value=[mock_response])
        mock_page_with_id.site.client.is_logged_in = True
        mock_page_with_id.site.client.login_check = MagicMock()

        result = mock_page_with_id.rename("new-page-name")
        assert result.fullname == "new-page-name"
        assert result.name == "new-page-name"
        assert result.category == "_default"

    def test_rename_with_category(self, mock_page_with_id: Page, page_rename_success: dict[str, Any]) -> None:
        """カテゴリ付きでページ名を変更できる"""
        mock_response = MagicMock()
        mock_response.json.return_value = page_rename_success
        mock_page_with_id.site.amc_request = MagicMock(return_value=[mock_response])
        mock_page_with_id.site.client.is_logged_in = True
        mock_page_with_id.site.client.login_check = MagicMock()

        result = mock_page_with_id.rename("component:new-name")
        assert result.fullname == "component:new-name"
        assert result.name == "new-name"
        assert result.category == "component"

    def test_vote_positive(self, mock_page_with_id: Page, page_ratepage_success: dict[str, Any]) -> None:
        """正の投票ができる"""
        mock_response = MagicMock()
        mock_response.json.return_value = page_ratepage_success
        mock_page_with_id.site.amc_request = MagicMock(return_value=[mock_response])
        mock_page_with_id.site.client.is_logged_in = True
        mock_page_with_id.site.client.login_check = MagicMock()

        new_rating = mock_page_with_id.vote(1)
        assert new_rating == 11
        assert mock_page_with_id.rating == 11

    def test_vote_negative(self, mock_page_with_id: Page) -> None:
        """負の投票ができる"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok", "type": "P", "points": 9}
        mock_page_with_id.site.amc_request = MagicMock(return_value=[mock_response])
        mock_page_with_id.site.client.is_logged_in = True
        mock_page_with_id.site.client.login_check = MagicMock()

        new_rating = mock_page_with_id.vote(-1)
        assert new_rating == 9

    def test_vote_not_logged_in(self, mock_page_with_id: Page) -> None:
        """ログインしていない場合に例外"""
        mock_page_with_id.site.client.is_logged_in = False
        mock_page_with_id.site.client.login_check = MagicMock(
            side_effect=exceptions.LoginRequiredException("Login required")
        )

        with pytest.raises(exceptions.LoginRequiredException):
            mock_page_with_id.vote(1)

    def test_cancel_vote_success(self, mock_page_with_id: Page, page_cancelvote_success: dict[str, Any]) -> None:
        """投票キャンセルができる"""
        mock_response = MagicMock()
        mock_response.json.return_value = page_cancelvote_success
        mock_page_with_id.site.amc_request = MagicMock(return_value=[mock_response])
        mock_page_with_id.site.client.is_logged_in = True
        mock_page_with_id.site.client.login_check = MagicMock()

        new_rating = mock_page_with_id.cancel_vote()
        assert new_rating == 10
        assert mock_page_with_id.rating == 10


class TestPageCreateOrEdit:
    """Page.create_or_editのテスト"""

    def test_create_new_page(
        self,
        mock_site_no_http: Site,
        page_pageedit_success: dict[str, Any],
        page_savepage_success: dict[str, Any],
        page_listpages_single: dict[str, Any],
    ) -> None:
        """新規ページを作成できる"""
        mock_site_no_http.client.is_logged_in = True
        mock_site_no_http.client.login_check = MagicMock()

        # ページロック取得 → 保存 → 検索 の順
        mock_lock_response = MagicMock()
        mock_lock_response.json.return_value = page_pageedit_success

        mock_save_response = MagicMock()
        mock_save_response.json.return_value = page_savepage_success

        mock_search_response = MagicMock()
        mock_search_response.json.return_value = page_listpages_single

        mock_site_no_http.amc_request = MagicMock(
            side_effect=[
                [mock_lock_response],
                [mock_save_response],
                [mock_search_response],
            ]
        )

        page = Page.create_or_edit(
            mock_site_no_http,
            "new-page",
            title="New Page Title",
            source="Page content",
        )
        assert page.fullname == "scp-001"

    def test_edit_locked_page(self, mock_site_no_http: Site, page_pageedit_locked: dict[str, Any]) -> None:
        """ロック済みページの編集で例外"""
        mock_site_no_http.client.is_logged_in = True
        mock_site_no_http.client.login_check = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = page_pageedit_locked
        mock_site_no_http.amc_request = MagicMock(return_value=[mock_response])

        with pytest.raises(exceptions.TargetErrorException):
            Page.create_or_edit(mock_site_no_http, "locked-page")

    def test_edit_without_page_id(self, mock_site_no_http: Site) -> None:
        """既存ページ編集時にpage_idがないと例外"""
        mock_site_no_http.client.is_logged_in = True
        mock_site_no_http.client.login_check = MagicMock()

        # page_revision_idがある = 既存ページ
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "ok",
            "lock_id": "abc",
            "lock_secret": "xyz",
            "page_revision_id": 100,  # 既存ページ
        }
        mock_site_no_http.amc_request = MagicMock(return_value=[mock_response])

        with pytest.raises(ValueError, match="page_id must be specified"):
            Page.create_or_edit(mock_site_no_http, "existing-page")

    def test_edit_raise_on_exists(self, mock_site_no_http: Site) -> None:
        """raise_on_exists=Trueで既存ページの場合に例外"""
        mock_site_no_http.client.is_logged_in = True
        mock_site_no_http.client.login_check = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "ok",
            "lock_id": "abc",
            "lock_secret": "xyz",
            "page_revision_id": 100,
        }
        mock_site_no_http.amc_request = MagicMock(return_value=[mock_response])

        with pytest.raises(exceptions.TargetExistsException):
            Page.create_or_edit(mock_site_no_http, "existing-page", raise_on_exists=True)

    def test_edit_not_logged_in(self, mock_site_no_http: Site) -> None:
        """ログインしていない場合に例外"""
        mock_site_no_http.client.is_logged_in = False
        mock_site_no_http.client.login_check = MagicMock(
            side_effect=exceptions.LoginRequiredException("Login required")
        )

        with pytest.raises(exceptions.LoginRequiredException):
            Page.create_or_edit(mock_site_no_http, "new-page")


class TestPageEdit:
    """Page.editのテスト"""

    def test_edit_existing_page(
        self,
        mock_page_with_id: Page,
        page_pageedit_existing: dict[str, Any],
        page_savepage_success: dict[str, Any],
        page_listpages_single: dict[str, Any],
        page_viewsource: dict[str, Any],
    ) -> None:
        """既存ページを編集できる"""
        mock_page_with_id.site.client.is_logged_in = True
        mock_page_with_id.site.client.login_check = MagicMock()

        # source取得用
        mock_source_response = MagicMock()
        mock_source_response.json.return_value = page_viewsource

        # ページロック取得
        mock_lock_response = MagicMock()
        mock_lock_response.json.return_value = page_pageedit_existing

        # 保存
        mock_save_response = MagicMock()
        mock_save_response.json.return_value = page_savepage_success

        # 検索
        mock_search_response = MagicMock()
        mock_search_response.json.return_value = page_listpages_single

        mock_page_with_id.site.amc_request = MagicMock(
            side_effect=[
                [mock_source_response],  # source取得
                [mock_lock_response],  # ロック取得
                [mock_save_response],  # 保存
                [mock_search_response],  # 検索
            ]
        )

        page = mock_page_with_id.edit(title="Updated Title")
        assert page is not None

    def test_edit_force_unlock(
        self,
        mock_page_with_id: Page,
        page_pageedit_existing: dict[str, Any],
        page_savepage_success: dict[str, Any],
        page_listpages_single: dict[str, Any],
    ) -> None:
        """強制アンロックして編集できる"""
        mock_page_with_id.site.client.is_logged_in = True
        mock_page_with_id.site.client.login_check = MagicMock()

        # sourceを直接渡すのでsource取得は不要
        mock_lock_response = MagicMock()
        mock_lock_response.json.return_value = page_pageedit_existing

        mock_save_response = MagicMock()
        mock_save_response.json.return_value = page_savepage_success

        mock_search_response = MagicMock()
        mock_search_response.json.return_value = page_listpages_single

        mock_page_with_id.site.amc_request = MagicMock(
            side_effect=[
                [mock_lock_response],  # ロック取得
                [mock_save_response],  # 保存
                [mock_search_response],  # 検索
            ]
        )

        mock_page_with_id.edit(source="New source", force_edit=True)

        # force_lock=yesが含まれていることを確認
        call_args_list = mock_page_with_id.site.amc_request.call_args_list
        lock_call = call_args_list[0]  # 1回目がロック取得
        assert lock_call[0][0][0].get("force_lock") == "yes"
