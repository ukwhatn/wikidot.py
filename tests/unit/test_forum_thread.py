"""ForumThreadモジュールのユニットテスト"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest
from bs4 import BeautifulSoup

from wikidot.common import exceptions
from wikidot.module.forum_thread import ForumThread, ForumThreadCollection

if TYPE_CHECKING:
    from wikidot.module.forum_category import ForumCategory
    from wikidot.module.site import Site


# ============================================================
# ForumThreadCollectionテスト
# ============================================================


class TestForumThreadCollectionInit:
    """ForumThreadCollectionの初期化テスト"""

    def test_init_with_site_and_empty_threads(self, mock_site_no_http: Site) -> None:
        """サイトと空のスレッドリストで初期化できる"""
        collection = ForumThreadCollection(mock_site_no_http, [])
        assert collection.site == mock_site_no_http
        assert len(collection) == 0

    def test_init_with_site_and_threads(self, mock_site_no_http: Site, mock_forum_thread_no_http: ForumThread) -> None:
        """サイトとスレッドリストで初期化できる"""
        collection = ForumThreadCollection(mock_site_no_http, [mock_forum_thread_no_http])
        assert collection.site == mock_site_no_http
        assert len(collection) == 1

    def test_find_existing(self, mock_site_no_http: Site, mock_forum_thread_no_http: ForumThread) -> None:
        """存在するスレッドをIDで検索できる"""
        collection = ForumThreadCollection(mock_site_no_http, [mock_forum_thread_no_http])
        found = collection.find(3001)
        assert found is not None
        assert found.id == 3001

    def test_find_nonexistent(self, mock_site_no_http: Site) -> None:
        """存在しないスレッドを検索するとNoneを返す"""
        collection = ForumThreadCollection(mock_site_no_http, [])
        found = collection.find(9999)
        assert found is None


class TestForumThreadCollectionParseListInCategory:
    """ForumThreadCollection._parse_list_in_categoryのテスト"""

    def test_parse_success(self, mock_site_no_http: Site, forum_threads_in_category: dict[str, Any]) -> None:
        """カテゴリ内スレッド一覧を正常にパースできる"""
        html = BeautifulSoup(forum_threads_in_category["body"], "lxml")
        collection = ForumThreadCollection._parse_list_in_category(mock_site_no_http, html)
        assert len(collection) == 2

    def test_parse_fields(self, mock_site_no_http: Site, forum_threads_in_category: dict[str, Any]) -> None:
        """スレッドの各フィールドが正しくパースされる"""
        html = BeautifulSoup(forum_threads_in_category["body"], "lxml")
        collection = ForumThreadCollection._parse_list_in_category(mock_site_no_http, html)

        # 1つ目のスレッドを検証
        thread = collection[0]
        assert thread.id == 3001
        assert thread.title == "Test Thread"
        assert thread.description == "Test thread description"
        assert thread.post_count == 5

        # 2つ目のスレッドを検証
        thread2 = collection[1]
        assert thread2.id == 3002
        assert thread2.title == "Another Thread"

    def test_parse_with_category(
        self,
        mock_site_no_http: Site,
        mock_forum_category_no_http: ForumCategory,
        forum_threads_in_category: dict[str, Any],
    ) -> None:
        """カテゴリを指定してパースできる"""
        html = BeautifulSoup(forum_threads_in_category["body"], "lxml")
        collection = ForumThreadCollection._parse_list_in_category(mock_site_no_http, html, mock_forum_category_no_http)
        assert collection[0].category == mock_forum_category_no_http


class TestForumThreadCollectionParseThreadPage:
    """ForumThreadCollection._parse_thread_pageのテスト"""

    def test_parse_success(self, mock_site_no_http: Site, forum_thread_detail: dict[str, Any]) -> None:
        """スレッド詳細ページを正常にパースできる"""
        html = BeautifulSoup(forum_thread_detail["body"], "lxml")
        thread = ForumThreadCollection._parse_thread_page(mock_site_no_http, html)
        assert thread is not None
        assert thread.id == 3001

    def test_parse_fields(self, mock_site_no_http: Site, forum_thread_detail: dict[str, Any]) -> None:
        """スレッド詳細の各フィールドが正しくパースされる"""
        html = BeautifulSoup(forum_thread_detail["body"], "lxml")
        thread = ForumThreadCollection._parse_thread_page(mock_site_no_http, html)

        assert thread.id == 3001
        assert thread.title == "Test Thread Title"
        assert thread.description == "Test thread description"
        assert thread.post_count == 5


class TestForumThreadCollectionAcquireAll:
    """ForumThreadCollection.acquire_all_in_categoryのテスト"""

    def test_acquire_all_single_page(
        self, mock_forum_category_no_http: ForumCategory, forum_threads_in_category: dict[str, Any]
    ) -> None:
        """単一ページのスレッド一覧を取得できる"""
        mock_response = MagicMock()
        mock_response.json.return_value = forum_threads_in_category
        mock_forum_category_no_http.site.amc_request = MagicMock(return_value=[mock_response])

        collection = ForumThreadCollection.acquire_all_in_category(mock_forum_category_no_http)
        assert len(collection) == 2

    def test_acquire_all_pagination(
        self, mock_forum_category_no_http: ForumCategory, forum_threads_in_category: dict[str, Any]
    ) -> None:
        """複数ページのスレッド一覧を取得できる（ページャーあり）"""
        # ページャー付きのレスポンスを作成
        body_with_pager = forum_threads_in_category["body"] + '<div class="pager"><a>1</a><a>2</a><a>next</a></div>'
        first_response = MagicMock()
        first_response.json.return_value = {"status": "ok", "body": body_with_pager}

        second_response = MagicMock()
        second_response.json.return_value = forum_threads_in_category

        mock_forum_category_no_http.site.amc_request = MagicMock(side_effect=[[first_response], [second_response]])

        collection = ForumThreadCollection.acquire_all_in_category(mock_forum_category_no_http)
        # 最初のページで2件 + 2ページ目で2件 = 4件
        assert len(collection) == 4


class TestForumThreadCollectionAcquireFromIds:
    """ForumThreadCollection.acquire_from_thread_idsのテスト"""

    def test_acquire_from_ids_success(self, mock_site_no_http: Site, forum_thread_detail: dict[str, Any]) -> None:
        """スレッドIDからスレッド情報を取得できる"""
        mock_response = MagicMock()
        mock_response.json.return_value = forum_thread_detail
        mock_site_no_http.amc_request = MagicMock(return_value=[mock_response])

        collection = ForumThreadCollection.acquire_from_thread_ids(mock_site_no_http, [3001])
        assert len(collection) == 1
        assert collection[0].id == 3001


# ============================================================
# ForumThreadテスト
# ============================================================


class TestForumThreadBasic:
    """ForumThreadの基本テスト"""

    def test_str(self, mock_forum_thread_no_http: ForumThread) -> None:
        """__str__が正しい文字列を返す"""
        result = str(mock_forum_thread_no_http)
        assert "ForumThread" in result
        assert "id=3001" in result
        assert "Test Thread" in result

    def test_url_property(self, mock_forum_thread_no_http: ForumThread) -> None:
        """urlプロパティが正しいURLを返す"""
        url = mock_forum_thread_no_http.url
        assert "test-site.wikidot.com" in url
        assert "forum/t-3001" in url


class TestForumThreadPosts:
    """ForumThread.postsプロパティのテスト"""

    def test_posts_property_calls_acquire(self, mock_forum_thread_no_http: ForumThread) -> None:
        """postsプロパティがForumPostCollection.acquire_allを呼び出す"""
        from wikidot.module.forum_post import ForumPostCollection

        mock_posts = ForumPostCollection(mock_forum_thread_no_http)
        mock_forum_thread_no_http._posts = mock_posts

        result = mock_forum_thread_no_http.posts
        assert result == mock_posts

    def test_posts_setter(self, mock_forum_thread_no_http: ForumThread) -> None:
        """_postsに直接設定できる"""
        from wikidot.module.forum_post import ForumPostCollection

        posts = ForumPostCollection(mock_forum_thread_no_http)
        mock_forum_thread_no_http._posts = posts
        assert mock_forum_thread_no_http._posts == posts


class TestForumThreadReply:
    """ForumThread.replyのテスト"""

    def test_reply_not_logged_in(self, mock_forum_thread_no_http: ForumThread) -> None:
        """ログインしていない場合に例外"""
        mock_forum_thread_no_http.site.client.is_logged_in = False
        mock_forum_thread_no_http.site.client.login_check = MagicMock(
            side_effect=exceptions.LoginRequiredException("Login required")
        )

        with pytest.raises(exceptions.LoginRequiredException):
            mock_forum_thread_no_http.reply(source="Test reply")

    def test_reply_success(self, mock_forum_thread_no_http: ForumThread, amc_ok_response: dict[str, Any]) -> None:
        """返信が成功する"""
        mock_forum_thread_no_http.site.client.is_logged_in = True
        mock_forum_thread_no_http.site.client.login_check = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = amc_ok_response
        mock_forum_thread_no_http.site.amc_request = MagicMock(return_value=[mock_response])

        initial_count = mock_forum_thread_no_http.post_count
        result = mock_forum_thread_no_http.reply(source="Test reply")

        assert result == mock_forum_thread_no_http
        assert mock_forum_thread_no_http.post_count == initial_count + 1
        assert mock_forum_thread_no_http._posts is None  # キャッシュがクリアされる

    def test_reply_with_title(self, mock_forum_thread_no_http: ForumThread, amc_ok_response: dict[str, Any]) -> None:
        """タイトル付きで返信できる"""
        mock_forum_thread_no_http.site.client.is_logged_in = True
        mock_forum_thread_no_http.site.client.login_check = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = amc_ok_response
        mock_forum_thread_no_http.site.amc_request = MagicMock(return_value=[mock_response])

        mock_forum_thread_no_http.reply(source="Test reply", title="Re: Test")

        # amc_requestの呼び出し引数を検証
        call_args = mock_forum_thread_no_http.site.amc_request.call_args[0][0][0]
        assert call_args["title"] == "Re: Test"

    def test_reply_to_parent_post(
        self, mock_forum_thread_no_http: ForumThread, amc_ok_response: dict[str, Any]
    ) -> None:
        """親投稿への返信ができる"""
        mock_forum_thread_no_http.site.client.is_logged_in = True
        mock_forum_thread_no_http.site.client.login_check = MagicMock()

        mock_response = MagicMock()
        mock_response.json.return_value = amc_ok_response
        mock_forum_thread_no_http.site.amc_request = MagicMock(return_value=[mock_response])

        mock_forum_thread_no_http.reply(source="Test reply", parent_post_id=5001)

        # amc_requestの呼び出し引数を検証
        call_args = mock_forum_thread_no_http.site.amc_request.call_args[0][0][0]
        assert call_args["parentId"] == "5001"


class TestForumThreadGetFromId:
    """ForumThread.get_from_idのテスト"""

    def test_get_from_id_success(self, mock_site_no_http: Site, forum_thread_detail: dict[str, Any]) -> None:
        """IDからスレッドを取得できる"""
        mock_response = MagicMock()
        mock_response.json.return_value = forum_thread_detail
        mock_site_no_http.amc_request = MagicMock(return_value=[mock_response])

        thread = ForumThread.get_from_id(mock_site_no_http, 3001)
        assert thread.id == 3001
        assert thread.title == "Test Thread Title"
