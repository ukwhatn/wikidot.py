"""pytest設定とフィクスチャ"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from wikidot.connector.ajax import AjaxModuleConnectorConfig
    from wikidot.module.site import Site

FIXTURES_DIR = Path(__file__).parent / "fixtures"
HTML_SAMPLES_DIR = FIXTURES_DIR / "html_samples"
AMC_RESPONSES_DIR = FIXTURES_DIR / "amc_responses"


# ============================================================
# 基本フィクスチャ
# ============================================================


@pytest.fixture
def mock_credentials() -> dict[str, str]:
    """テスト用認証情報"""
    return {
        "username": "test_user",
        "password": "test_password",
    }


# ============================================================
# クライアント関連フィクスチャ
# ============================================================


@pytest.fixture
def mock_amc_config() -> AjaxModuleConnectorConfig:
    """テスト用AMC設定（短いタイムアウト）"""
    from wikidot.connector.ajax import AjaxModuleConnectorConfig

    return AjaxModuleConnectorConfig(
        request_timeout=5,
        attempt_limit=2,
        retry_interval=0,
        semaphore_limit=5,
    )


@pytest.fixture
def mock_client_no_http() -> MagicMock:
    """HTTPリクエストなしでClientをモック"""
    from wikidot.connector.ajax import AjaxModuleConnectorConfig, AjaxRequestHeader

    mock = MagicMock()
    mock.amc_client = MagicMock()
    mock.amc_client.header = AjaxRequestHeader()
    mock.amc_client.config = AjaxModuleConnectorConfig(
        request_timeout=5,
        attempt_limit=2,
        retry_interval=0,
    )
    mock.is_logged_in = False
    return mock


@pytest.fixture
def mock_site_no_http(mock_client_no_http: MagicMock) -> Site:
    """HTTPリクエストなしでSiteを作成"""
    from wikidot.module.site import Site

    return Site(
        client=mock_client_no_http,
        id=123456,
        title="Test Site",
        unix_name="test-site",
        domain="test-site.wikidot.com",
        ssl_supported=True,
    )


# ============================================================
# AMCレスポンスフィクスチャ
# ============================================================


@pytest.fixture
def amc_ok_response() -> dict[str, Any]:
    """成功AMCレスポンス"""
    return {"status": "ok", "body": ""}


@pytest.fixture
def amc_error_response() -> Callable[[str, str], dict[str, Any]]:
    """エラーAMCレスポンスファクトリ"""

    def _make_error(status: str, message: str = "") -> dict[str, Any]:
        return {"status": status, "message": message}

    return _make_error


@pytest.fixture
def amc_try_again_response() -> dict[str, str]:
    """try_again AMCレスポンス"""
    return {"status": "try_again"}


@pytest.fixture
def amc_no_permission_response() -> dict[str, str]:
    """no_permission AMCレスポンス"""
    return {"status": "no_permission"}


# ============================================================
# ファイル読み込みヘルパー
# ============================================================


def _load_html(filename: str) -> str:
    """HTMLフィクスチャファイルを読み込む（内部用）"""
    path = HTML_SAMPLES_DIR / filename
    return path.read_text(encoding="utf-8").strip()


def _load_json(subdir: str, filename: str) -> dict[str, Any]:
    """JSONフィクスチャファイルを読み込む（内部用）"""
    path = AMC_RESPONSES_DIR / subdir / filename
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def load_html_fixture() -> Callable[[str], str]:
    """HTMLフィクスチャファイルを読み込む"""
    return _load_html


@pytest.fixture
def load_json_fixture() -> Callable[[str, str], dict[str, Any]]:
    """JSONフィクスチャファイルを読み込む"""

    def _load(subdir: str, filename: str) -> dict[str, Any]:
        return _load_json(subdir, filename)

    return _load


# ============================================================
# Printuser HTMLフィクスチャ
# ============================================================


@pytest.fixture
def printuser_regular_html() -> str:
    """通常ユーザーのprintuser HTML"""
    return _load_html("printuser_regular.html")


@pytest.fixture
def printuser_deleted_html() -> str:
    """削除済みユーザーのprintuser HTML"""
    return _load_html("printuser_deleted.html")


@pytest.fixture
def printuser_deleted_no_id_html() -> str:
    """ID無し削除済みユーザーのprintuser HTML"""
    return _load_html("printuser_deleted_no_id.html")


@pytest.fixture
def printuser_anonymous_html() -> str:
    """匿名ユーザーのprintuser HTML"""
    return _load_html("printuser_anonymous.html")


@pytest.fixture
def printuser_anonymous_no_ip_html() -> str:
    """IP無し匿名ユーザーのprintuser HTML"""
    return _load_html("printuser_anonymous_no_ip.html")


@pytest.fixture
def printuser_guest_html() -> str:
    """ゲストユーザーのprintuser HTML"""
    return _load_html("printuser_guest.html")


@pytest.fixture
def printuser_wikidot_html() -> str:
    """Wikidotシステムユーザーのprintuser HTML"""
    return _load_html("printuser_wikidot.html")


# ============================================================
# Odate HTMLフィクスチャ
# ============================================================


@pytest.fixture
def odate_html_factory() -> Callable[[int], str]:
    """odate HTML要素ファクトリ"""

    def _make_odate(unix_timestamp: int) -> str:
        return f'<span class="odate time_{unix_timestamp} format_%25e%20%25b%20%25Y%2C%20%25H%3A%25M%7Cagohover" style="cursor: help; display: inline;">17 Dec 2025, 12:00</span>'

    return _make_odate


@pytest.fixture
def odate_html_no_time() -> str:
    """time_クラスなしのodate HTML"""
    return _load_html("odate_no_time.html")


@pytest.fixture
def odate_html_multiple_classes() -> str:
    """複数クラス付きodate HTML"""
    return _load_html("odate_multiple_classes.html")


# ============================================================
# サイトHTMLフィクスチャ
# ============================================================


@pytest.fixture
def site_html_response() -> str:
    """サイトホームページHTML"""
    return _load_html("site_homepage.html")


@pytest.fixture
def user_profile_html() -> str:
    """ユーザープロファイルHTML"""
    return _load_html("user_profile.html")


@pytest.fixture
def user_profile_not_found_html() -> str:
    """存在しないユーザーのプロファイルHTML"""
    return _load_html("user_profile_notfound.html")


# ============================================================
# Page関連フィクスチャ
# ============================================================


@pytest.fixture
def mock_page_no_http(mock_site_no_http: Site) -> Any:
    """HTTPリクエストなしでPageを作成"""
    from wikidot.module.page import Page

    return Page(
        site=mock_site_no_http,
        fullname="test-page",
        name="test-page",
        category="_default",
        title="Test Page Title",
        children_count=0,
        comments_count=0,
        size=1000,
        rating=10,
        votes_count=5,
        rating_percent=None,
        revisions_count=3,
        parent_fullname=None,
        tags=["tag1", "tag2"],
        created_by=None,
        created_at=None,
        updated_by=None,
        updated_at=None,
        commented_by=None,
        commented_at=None,
    )


@pytest.fixture
def mock_page_with_id(mock_page_no_http: Any) -> Any:
    """page_idを持つPage"""
    mock_page_no_http._id = 12345
    return mock_page_no_http


@pytest.fixture
def page_listpages_single() -> dict[str, Any]:
    """単一ページのListPagesレスポンス"""
    return _load_json("page", "listpages_single.json")


@pytest.fixture
def page_listpages_multiple() -> dict[str, Any]:
    """複数ページのListPagesレスポンス"""
    return _load_json("page", "listpages_multiple.json")


@pytest.fixture
def page_listpages_empty() -> dict[str, Any]:
    """空のListPagesレスポンス"""
    return _load_json("page", "listpages_empty.json")


@pytest.fixture
def page_viewsource() -> dict[str, Any]:
    """ソース取得レスポンス"""
    return _load_json("page", "viewsource.json")


@pytest.fixture
def page_revisionlist() -> dict[str, Any]:
    """リビジョン一覧レスポンス"""
    return _load_json("page", "revisionlist.json")


@pytest.fixture
def page_whorated() -> dict[str, Any]:
    """投票者一覧レスポンス"""
    return _load_json("page", "whorated.json")


@pytest.fixture
def page_pageedit_locked() -> dict[str, Any]:
    """ロック済みページレスポンス"""
    return _load_json("page", "pageedit_locked.json")


@pytest.fixture
def page_pageedit_success() -> dict[str, Any]:
    """ロック取得成功レスポンス（新規ページ）"""
    return _load_json("page", "pageedit_success.json")


@pytest.fixture
def page_pageedit_existing() -> dict[str, Any]:
    """ロック取得成功レスポンス（既存ページ）"""
    return _load_json("page", "pageedit_existing.json")


@pytest.fixture
def page_savepage_success() -> dict[str, Any]:
    """ページ保存成功レスポンス"""
    return _load_json("page", "savepage_success.json")


@pytest.fixture
def page_savetags_success() -> dict[str, Any]:
    """タグ保存成功レスポンス"""
    return _load_json("page", "savetags_success.json")


@pytest.fixture
def page_setparent_success() -> dict[str, Any]:
    """親設定成功レスポンス"""
    return _load_json("page", "setparent_success.json")


@pytest.fixture
def page_rename_success() -> dict[str, Any]:
    """名前変更成功レスポンス"""
    return _load_json("page", "rename_success.json")


@pytest.fixture
def page_delete_success() -> dict[str, Any]:
    """削除成功レスポンス"""
    return _load_json("page", "delete_success.json")


@pytest.fixture
def page_ratepage_success() -> dict[str, Any]:
    """投票成功レスポンス"""
    return _load_json("page", "ratepage_success.json")


@pytest.fixture
def page_ratepage_pm_success() -> dict[str, Any]:
    """PM投票成功レスポンス"""
    return _load_json("page", "ratepage_pm_success.json")


@pytest.fixture
def page_cancelvote_success() -> dict[str, Any]:
    """投票キャンセル成功レスポンス"""
    return _load_json("page", "cancelvote_success.json")


@pytest.fixture
def page_listpages_pm_rating() -> dict[str, Any]:
    """PM評価システムのListPagesレスポンス"""
    return _load_json("page", "listpages_pm_rating.json")


@pytest.fixture
def page_listpages_missing_fields() -> dict[str, Any]:
    """オプションフィールドが空のListPagesレスポンス"""
    return _load_json("page", "listpages_missing_fields.json")


@pytest.fixture
def page_listpages_invalid() -> dict[str, Any]:
    """不正なListPagesレスポンス（必須要素欠損）"""
    return _load_json("page", "listpages_invalid.json")


# ============================================================
# ForumCategory関連フィクスチャ
# ============================================================


@pytest.fixture
def mock_forum_category_no_http(mock_site_no_http: Site) -> Any:
    """HTTPリクエストなしでForumCategoryを作成"""
    from wikidot.module.forum_category import ForumCategory

    return ForumCategory(
        site=mock_site_no_http,
        id=1001,
        title="Test Category",
        description="Test category description",
        threads_count=10,
        posts_count=50,
    )


@pytest.fixture
def forum_start() -> dict[str, Any]:
    """フォーラムカテゴリ一覧レスポンス"""
    return _load_json("forum", "forum_start.json")


@pytest.fixture
def forum_start_empty() -> dict[str, Any]:
    """空のフォーラムカテゴリ一覧レスポンス"""
    return _load_json("forum", "forum_start_empty.json")


@pytest.fixture
def forum_newthread_success() -> dict[str, Any]:
    """スレッド作成成功レスポンス"""
    return _load_json("forum", "newthread_success.json")


# ============================================================
# ForumThread関連フィクスチャ
# ============================================================


@pytest.fixture
def mock_forum_thread_no_http(mock_forum_category_no_http: Any) -> Any:
    """HTTPリクエストなしでForumThreadを作成"""
    from wikidot.module.forum_thread import ForumThread

    return ForumThread(
        site=mock_forum_category_no_http.site,
        id=3001,
        title="Test Thread",
        description="Test thread description",
        created_by=None,
        created_at=None,
        post_count=5,
        category=mock_forum_category_no_http,
    )


@pytest.fixture
def forum_threads_in_category() -> dict[str, Any]:
    """カテゴリ内スレッド一覧レスポンス"""
    return _load_json("forum", "threads_in_category.json")


@pytest.fixture
def forum_thread_detail() -> dict[str, Any]:
    """スレッド詳細レスポンス"""
    return _load_json("forum", "thread_detail.json")


# ============================================================
# ForumPost関連フィクスチャ
# ============================================================


@pytest.fixture
def mock_forum_post_no_http(mock_forum_thread_no_http: Any) -> Any:
    """HTTPリクエストなしでForumPostを作成"""
    from bs4 import BeautifulSoup

    from wikidot.module.forum_post import ForumPost

    # elementはダミーのTag
    html = BeautifulSoup('<div class="post" id="post-5001"></div>', "lxml")
    element = html.select_one("div.post")

    return ForumPost(
        thread=mock_forum_thread_no_http,
        id=5001,
        title="Test Post Title",
        text="<p>Test post content</p>",
        element=element,
        created_by=None,
        created_at=None,
        edited_by=None,
        edited_at=None,
        _parent_id=None,
    )


@pytest.fixture
def forum_posts_in_thread() -> dict[str, Any]:
    """スレッド内投稿一覧レスポンス"""
    return _load_json("forum", "posts_in_thread.json")


@pytest.fixture
def forum_posts_nested() -> dict[str, Any]:
    """ネスト投稿レスポンス"""
    return _load_json("forum", "posts_nested.json")


@pytest.fixture
def forum_posts_with_pseudo_post() -> dict[str, Any]:
    """疑似ポストを含む投稿レスポンス"""
    return _load_json("forum", "posts_with_pseudo_post.json")


@pytest.fixture
def forum_editpost_form() -> dict[str, Any]:
    """投稿編集フォームレスポンス"""
    return _load_json("forum", "editpost_form.json")


@pytest.fixture
def forum_savepost_success() -> dict[str, Any]:
    """投稿保存成功レスポンス"""
    return _load_json("forum", "savepost_success.json")


@pytest.fixture
def forum_post_revisions() -> dict[str, Any]:
    """ポストリビジョン一覧レスポンス"""
    return _load_json("forum", "post_revisions.json")


@pytest.fixture
def forum_post_revisions_single() -> dict[str, Any]:
    """ポストリビジョン一覧レスポンス（1件）"""
    return _load_json("forum", "post_revisions_single.json")


@pytest.fixture
def forum_post_revision_content() -> dict[str, Any]:
    """ポストリビジョンコンテンツレスポンス"""
    return _load_json("forum", "post_revision_content.json")


# ============================================================
# QuickModule関連フィクスチャ
# ============================================================


@pytest.fixture
def quickmodule_member_lookup() -> dict[str, Any]:
    """メンバー検索レスポンス"""
    return _load_json("quickmodule", "member_lookup.json")


@pytest.fixture
def quickmodule_member_lookup_empty() -> dict[str, Any]:
    """メンバー検索（結果なし）レスポンス"""
    return _load_json("quickmodule", "member_lookup_empty.json")


@pytest.fixture
def quickmodule_user_lookup() -> dict[str, Any]:
    """ユーザー検索レスポンス"""
    return _load_json("quickmodule", "user_lookup.json")


@pytest.fixture
def quickmodule_user_lookup_empty() -> dict[str, Any]:
    """ユーザー検索（結果なし）レスポンス"""
    return _load_json("quickmodule", "user_lookup_empty.json")


@pytest.fixture
def quickmodule_page_lookup() -> dict[str, Any]:
    """ページ検索レスポンス"""
    return _load_json("quickmodule", "page_lookup.json")


@pytest.fixture
def quickmodule_page_lookup_empty() -> dict[str, Any]:
    """ページ検索（結果なし）レスポンス"""
    return _load_json("quickmodule", "page_lookup_empty.json")


# ============================================================
# Site関連フィクスチャ
# ============================================================


@pytest.fixture
def site_invite_member_success() -> dict[str, Any]:
    """メンバー招待成功レスポンス"""
    return _load_json("site", "invite_member_success.json")


@pytest.fixture
def site_invite_member_already_invited() -> dict[str, Any]:
    """メンバー招待（既に招待済み）レスポンス"""
    return _load_json("site", "invite_member_already_invited.json")


@pytest.fixture
def site_invite_member_already_member() -> dict[str, Any]:
    """メンバー招待（既にメンバー）レスポンス"""
    return _load_json("site", "invite_member_already_member.json")


@pytest.fixture
def site_changes() -> dict[str, Any]:
    """サイト変更履歴レスポンス"""
    return _load_json("site", "site_changes.json")


@pytest.fixture
def site_changes_empty() -> dict[str, Any]:
    """サイト変更履歴（空）レスポンス"""
    return _load_json("site", "site_changes_empty.json")


@pytest.fixture
def site_applications() -> dict[str, Any]:
    """サイト参加申請レスポンス"""
    return _load_json("site", "applications.json")


@pytest.fixture
def site_applications_empty() -> dict[str, Any]:
    """サイト参加申請（空）レスポンス"""
    return _load_json("site", "applications_empty.json")
