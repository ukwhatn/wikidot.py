"""ForumCategoryモジュールのユニットテスト"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

from wikidot.common import exceptions
from wikidot.module.forum_category import ForumCategory, ForumCategoryCollection

if TYPE_CHECKING:
    from wikidot.module.site import Site


# ============================================================
# ForumCategoryCollectionテスト
# ============================================================


class TestForumCategoryCollectionInit:
    """ForumCategoryCollectionの初期化テスト"""

    def test_init_with_site_and_empty_categories(self, mock_site_no_http: Site) -> None:
        """サイトと空のカテゴリリストで初期化できる"""
        collection = ForumCategoryCollection(mock_site_no_http, [])
        assert collection.site == mock_site_no_http
        assert len(collection) == 0

    def test_init_with_site_and_categories(
        self, mock_site_no_http: Site, mock_forum_category_no_http: ForumCategory
    ) -> None:
        """サイトとカテゴリリストで初期化できる"""
        collection = ForumCategoryCollection(mock_site_no_http, [mock_forum_category_no_http])
        assert collection.site == mock_site_no_http
        assert len(collection) == 1

    def test_find_existing(self, mock_site_no_http: Site, mock_forum_category_no_http: ForumCategory) -> None:
        """存在するカテゴリをIDで検索できる"""
        collection = ForumCategoryCollection(mock_site_no_http, [mock_forum_category_no_http])
        found = collection.find(1001)
        assert found is not None
        assert found.id == 1001

    def test_find_nonexistent(self, mock_site_no_http: Site) -> None:
        """存在しないカテゴリを検索するとNoneを返す"""
        collection = ForumCategoryCollection(mock_site_no_http, [])
        found = collection.find(9999)
        assert found is None


class TestForumCategoryCollectionAcquireAll:
    """ForumCategoryCollection.acquire_allのテスト"""

    def test_acquire_all_success(self, mock_site_no_http: Site, forum_start: dict[str, Any]) -> None:
        """カテゴリ一覧を正常に取得できる"""
        mock_response = MagicMock()
        mock_response.json.return_value = forum_start
        mock_site_no_http.amc_request = MagicMock(return_value=[mock_response])

        collection = ForumCategoryCollection.acquire_all(mock_site_no_http)
        assert len(collection) == 2

    def test_acquire_all_parse_fields(self, mock_site_no_http: Site, forum_start: dict[str, Any]) -> None:
        """カテゴリの各フィールドが正しくパースされる"""
        mock_response = MagicMock()
        mock_response.json.return_value = forum_start
        mock_site_no_http.amc_request = MagicMock(return_value=[mock_response])

        collection = ForumCategoryCollection.acquire_all(mock_site_no_http)

        # 1つ目のカテゴリを検証
        category = collection[0]
        assert category.id == 1001
        assert category.title == "Test Category"
        assert category.description == "Test category description"
        assert category.threads_count == 10
        assert category.posts_count == 50

        # 2つ目のカテゴリを検証
        category2 = collection[1]
        assert category2.id == 1002
        assert category2.title == "Another Category"

    def test_acquire_all_empty(self, mock_site_no_http: Site, forum_start_empty: dict[str, Any]) -> None:
        """空のカテゴリ一覧を取得できる"""
        mock_response = MagicMock()
        mock_response.json.return_value = forum_start_empty
        mock_site_no_http.amc_request = MagicMock(return_value=[mock_response])

        collection = ForumCategoryCollection.acquire_all(mock_site_no_http)
        assert len(collection) == 0


# ============================================================
# ForumCategoryテスト
# ============================================================


class TestForumCategoryBasic:
    """ForumCategoryの基本テスト"""

    def test_str(self, mock_forum_category_no_http: ForumCategory) -> None:
        """__str__が正しい文字列を返す"""
        result = str(mock_forum_category_no_http)
        assert "ForumCategory" in result
        assert "id=1001" in result
        assert "Test Category" in result

    def test_threads_setter(self, mock_forum_category_no_http: ForumCategory) -> None:
        """threadsプロパティのsetterが動作する"""
        from wikidot.module.forum_thread import ForumThreadCollection

        threads = ForumThreadCollection(mock_forum_category_no_http.site)
        mock_forum_category_no_http.threads = threads
        assert mock_forum_category_no_http._threads == threads


class TestForumCategoryCreateThread:
    """ForumCategory.create_threadのテスト"""

    def test_create_thread_not_logged_in(self, mock_forum_category_no_http: ForumCategory) -> None:
        """ログインしていない場合に例外"""
        mock_forum_category_no_http.site.client.is_logged_in = False
        mock_forum_category_no_http.site.client.login_check = MagicMock(
            side_effect=exceptions.LoginRequiredException("Login required")
        )

        with pytest.raises(exceptions.LoginRequiredException):
            mock_forum_category_no_http.create_thread(
                title="Test Thread",
                description="Test description",
                source="Test content",
            )

    def test_create_thread_success(
        self,
        mock_forum_category_no_http: ForumCategory,
        forum_newthread_success: dict[str, Any],
        forum_thread_detail: dict[str, Any],
    ) -> None:
        """スレッド作成が成功する"""
        mock_forum_category_no_http.site.client.is_logged_in = True
        mock_forum_category_no_http.site.client.login_check = MagicMock()

        # 1回目: newThread, 2回目: get_from_id
        create_response = MagicMock()
        create_response.json.return_value = forum_newthread_success
        detail_response = MagicMock()
        detail_response.json.return_value = forum_thread_detail

        mock_forum_category_no_http.site.amc_request = MagicMock(side_effect=[[create_response], [detail_response]])

        thread = mock_forum_category_no_http.create_thread(
            title="Test Thread",
            description="Test description",
            source="Test content",
        )

        assert thread.id == 3001
        assert thread.category == mock_forum_category_no_http
