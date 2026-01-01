"""フォーラムポストリビジョンの統合テスト"""

from __future__ import annotations

from wikidot.module.forum_post_revision import ForumPostRevisionCollection


class TestForumPostRevision:
    """フォーラムポストリビジョン操作テスト"""

    def test_1_get_revisions_from_edited_post(self, site) -> None:
        """1. 編集済みポストからリビジョン取得"""
        categories = site.forum.categories
        if len(categories) == 0:
            print("No forum categories found, skipping test")
            return

        # カテゴリ内のスレッドを探す
        for category in categories:
            threads = category.threads
            if len(threads) == 0:
                continue

            # スレッド内のポストを探す
            for thread in threads:
                posts = thread.posts
                # 編集済みのポストを探す
                for post in posts:
                    if post.has_revisions:
                        revisions = post.revisions
                        assert isinstance(revisions, ForumPostRevisionCollection)
                        assert len(revisions) > 1
                        assert revisions[0].rev_no == 0
                        assert revisions[-1].rev_no == len(revisions) - 1

                        # リビジョンのプロパティを確認
                        for revision in revisions:
                            assert revision.id is not None
                            assert revision.rev_no >= 0
                            assert revision.created_by is not None
                            assert revision.created_at is not None

                        return  # テスト成功

        print("No edited posts found in forum, skipping test")

    def test_2_get_revisions_from_unedited_post(self, site) -> None:
        """2. 未編集ポストからリビジョン取得"""
        categories = site.forum.categories
        if len(categories) == 0:
            print("No forum categories found, skipping test")
            return

        # カテゴリ内のスレッドを探す
        for category in categories:
            threads = category.threads
            if len(threads) == 0:
                continue

            # スレッド内のポストを探す
            for thread in threads:
                posts = thread.posts
                # 未編集のポストを探す
                for post in posts:
                    if not post.has_revisions:
                        revisions = post.revisions
                        assert isinstance(revisions, ForumPostRevisionCollection)
                        assert len(revisions) == 1
                        assert revisions[0].rev_no == 0

                        return  # テスト成功

        print("No unedited posts found in forum, skipping test")

    def test_3_get_revision_html(self, site) -> None:
        """3. リビジョンHTML取得"""
        categories = site.forum.categories
        if len(categories) == 0:
            print("No forum categories found, skipping test")
            return

        # カテゴリ内のスレッドを探す
        for category in categories:
            threads = category.threads
            if len(threads) == 0:
                continue

            # スレッド内のポストを探す
            for thread in threads:
                posts = thread.posts
                if len(posts) == 0:
                    continue

                post = posts[0]
                revisions = post.revisions
                if len(revisions) == 0:
                    continue

                # 最初のリビジョンのHTMLを取得
                html = revisions[0].html
                assert html is not None
                assert isinstance(html, str)
                assert len(html) > 0

                return  # テスト成功

        print("No posts found in forum, skipping test")

    def test_4_verify_collection_methods(self, site) -> None:
        """4. コレクションメソッドの検証"""
        categories = site.forum.categories
        if len(categories) == 0:
            print("No forum categories found, skipping test")
            return

        # カテゴリ内のスレッドを探す
        for category in categories:
            threads = category.threads
            if len(threads) == 0:
                continue

            # スレッド内のポストを探す
            for thread in threads:
                posts = thread.posts
                # 編集済みのポストを探す
                for post in posts:
                    if post.has_revisions:
                        revisions = post.revisions
                        if len(revisions) < 2:
                            continue

                        # findById相当（find）のテスト
                        first_revision = revisions[0]
                        found = revisions.find(first_revision.id)
                        assert found is not None
                        assert found.id == first_revision.id

                        # find_by_rev_noのテスト
                        found_by_rev_no = revisions.find_by_rev_no(0)
                        assert found_by_rev_no is not None
                        assert found_by_rev_no.rev_no == 0

                        return  # テスト成功

        print("No edited posts found in forum, skipping test")
