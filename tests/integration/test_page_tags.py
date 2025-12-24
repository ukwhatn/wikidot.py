"""ページタグ操作の統合テスト"""

from __future__ import annotations

import pytest

from .conftest import generate_page_name


class TestPageTags:
    """ページタグ操作テスト"""

    @pytest.fixture(autouse=True)
    def setup(self, site):
        """テストセットアップ - ページを作成"""
        self.site = site
        self.page_name = generate_page_name("tags")

        # テスト用ページを作成
        self.site.page.create(
            fullname=self.page_name,
            title="Tags Test Page",
            source="Content for tags test.",
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

    def test_1_add_tags(self):
        """1. タグ追加"""
        self.page.tags = ["test-tag-1", "test-tag-2"]
        self.page.commit_tags()

        # 再取得して確認
        updated_page = self.site.page.get(self.page_name)
        assert updated_page is not None
        assert "test-tag-1" in updated_page.tags
        assert "test-tag-2" in updated_page.tags

    def test_2_update_tags(self):
        """2. タグ更新"""
        # まずタグを追加
        self.page.tags = ["test-tag-1", "test-tag-2"]
        self.page.commit_tags()

        # 再取得
        self.page = self.site.page.get(self.page_name)
        assert self.page is not None

        # タグを更新
        self.page.tags = ["test-tag-updated"]
        self.page.commit_tags()

        # 確認
        updated_page = self.site.page.get(self.page_name)
        assert updated_page is not None
        assert "test-tag-updated" in updated_page.tags
        assert "test-tag-1" not in updated_page.tags
        assert "test-tag-2" not in updated_page.tags

    def test_3_remove_all_tags(self):
        """3. タグ全削除"""
        # まずタグを追加
        self.page.tags = ["test-tag-1"]
        self.page.commit_tags()

        # 再取得
        self.page = self.site.page.get(self.page_name)
        assert self.page is not None

        # タグを全削除
        self.page.tags = []
        self.page.commit_tags()

        # 確認
        updated_page = self.site.page.get(self.page_name)
        assert updated_page is not None
        assert len(updated_page.tags) == 0

    def test_4_tags_with_special_chars(self):
        """4. 特殊文字を含むタグ"""
        # Wikidotのタグは小文字、数字、ハイフンのみ
        self.page.tags = ["test-tag", "another-tag-123"]
        self.page.commit_tags()

        updated_page = self.site.page.get(self.page_name)
        assert updated_page is not None
        assert "test-tag" in updated_page.tags
        assert "another-tag-123" in updated_page.tags
