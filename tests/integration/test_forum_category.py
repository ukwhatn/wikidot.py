"""フォーラムカテゴリの統合テスト"""

from __future__ import annotations


class TestForumCategory:
    """フォーラムカテゴリ操作テスト"""

    def test_1_get_forum_categories(self, site):
        """1. フォーラムカテゴリ一覧取得"""
        categories = site.forum.categories
        assert categories is not None
        # カテゴリがなくても空のコレクションが返る
        assert isinstance(categories, list)

    def test_2_category_properties(self, site):
        """2. カテゴリプロパティ確認"""
        categories = site.forum.categories

        # カテゴリがある場合はプロパティを確認
        if len(categories) > 0:
            category = categories[0]
            assert category.id is not None
            assert category.title is not None
            assert category.site is not None

    def test_3_category_threads(self, site):
        """3. カテゴリのスレッド一覧取得"""
        categories = site.forum.categories

        # カテゴリがある場合はスレッドを取得
        if len(categories) > 0:
            category = categories[0]
            threads = category.threads
            assert threads is not None
            assert isinstance(threads, list)
