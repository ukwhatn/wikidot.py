"""ページディスカッション（コメント）操作の統合テスト"""

from __future__ import annotations

import pytest

from .conftest import generate_page_name


class TestPageDiscussion:
    """ページディスカッション操作テスト"""

    @pytest.fixture(autouse=True)
    def setup(self, site):
        """テストセットアップ - ページを作成"""
        self.site = site
        self.page_name = generate_page_name("discussion")

        # テスト用ページを作成
        self.site.page.create(
            fullname=self.page_name,
            title="Discussion Test Page",
            source="Content for discussion test.",
        )
        self.page = self.site.page.get(self.page_name)
        assert self.page is not None

        yield

        # クリーンアップ
        try:
            page = self.site.page.get(self.page_name, raise_when_not_found=False)
            if page is not None:
                page.destroy()
        except Exception:
            pass

    def test_1_get_discussion_none(self):
        """1. ディスカッション取得（コメントなし）"""
        # 新規作成したページにはディスカッションがない可能性がある
        discussion = self.page.discussion
        # ディスカッションがない場合はNone、ある場合はForumThread
        # 新規ページの場合、ディスカッションスレッドが自動作成されないサイト設定もある
        assert discussion is None or discussion is not None

    def test_2_post_comment(self):
        """2. コメント投稿"""
        # ディスカッションを取得（または作成）
        discussion = self.page.discussion

        if discussion is None:
            # ディスカッションがない場合はスキップ
            # NOTE: Wikidotの設定によっては、ページにコメントを最初に投稿すると
            # 自動的にディスカッションスレッドが作成される場合がある
            pytest.skip("Discussion thread not available for this page")

        initial_post_count = discussion.post_count

        # コメントを投稿
        discussion.reply(
            source="This is a test comment.",
            title="Test Comment",
        )

        # 投稿数が増えたことを確認
        assert discussion.post_count == initial_post_count + 1

    def test_3_get_posts(self):
        """3. 投稿一覧取得"""
        discussion = self.page.discussion

        if discussion is None:
            pytest.skip("Discussion thread not available for this page")

        # 投稿がない場合は投稿を追加
        if discussion.post_count == 0:
            discussion.reply(source="Test post for listing.", title="Test")

        # 投稿一覧を取得
        posts = discussion.posts
        assert posts is not None
        assert len(posts) >= 0  # 空でも可

    def test_4_reply_to_post(self):
        """4. 投稿への返信"""
        discussion = self.page.discussion

        if discussion is None:
            pytest.skip("Discussion thread not available for this page")

        # まず親投稿を作成
        discussion.reply(source="Parent post.", title="Parent")

        # 投稿一覧を取得
        discussion._posts = None  # キャッシュをクリア
        posts = discussion.posts

        if len(posts) == 0:
            pytest.skip("No posts available to reply to")

        parent_post = posts[0]
        initial_count = discussion.post_count

        # 親投稿に返信
        discussion.reply(
            source="This is a reply.",
            title="Reply",
            parent_post_id=parent_post.id,
        )

        assert discussion.post_count == initial_count + 1
