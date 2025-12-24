"""ページメタ操作の統合テスト"""

from __future__ import annotations

import pytest

from .conftest import generate_page_name


class TestPageMeta:
    """ページメタ操作テスト"""

    @pytest.fixture(autouse=True)
    def setup(self, site):
        """テストセットアップ - ページを作成"""
        self.site = site
        self.page_name = generate_page_name("meta")

        # テスト用ページを作成
        self.site.page.create(
            fullname=self.page_name,
            title="Meta Test Page",
            source="Content for meta test.",
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

    def test_1_set_meta(self):
        """1. メタ設定"""
        self.page.metas = {"description": "Test description"}

        # 再取得して確認
        updated_page = self.site.page.get(self.page_name)
        assert updated_page is not None
        assert "description" in updated_page.metas
        assert updated_page.metas["description"] == "Test description"

    def test_2_get_meta(self):
        """2. メタ取得"""
        # まずメタを設定
        self.page.metas = {"keywords": "test, integration"}

        # 再取得
        updated_page = self.site.page.get(self.page_name)
        assert updated_page is not None

        # メタ取得
        metas = updated_page.metas
        assert "keywords" in metas
        assert metas["keywords"] == "test, integration"

    def test_3_update_meta(self):
        """3. メタ更新"""
        # まずメタを設定
        self.page.metas = {"description": "Original description"}

        # 再取得
        self.page = self.site.page.get(self.page_name)
        assert self.page is not None
        assert self.page.metas["description"] == "Original description"

        # メタを更新
        self.page.metas = {"description": "Updated description"}

        # 確認
        updated_page = self.site.page.get(self.page_name)
        assert updated_page is not None
        assert updated_page.metas["description"] == "Updated description"

    def test_4_delete_meta(self):
        """4. メタ削除"""
        # まずメタを設定
        self.page.metas = {"description": "To be deleted"}

        # 再取得
        self.page = self.site.page.get(self.page_name)
        assert self.page is not None
        assert "description" in self.page.metas

        # メタを削除（空の辞書を設定）
        self.page.metas = {}

        # 確認
        updated_page = self.site.page.get(self.page_name)
        assert updated_page is not None
        assert "description" not in updated_page.metas

    def test_5_multiple_metas(self):
        """5. 複数メタの設定"""
        self.page.metas = {
            "description": "Page description",
            "keywords": "keyword1, keyword2",
            "author": "Test Author",
        }

        # 確認
        updated_page = self.site.page.get(self.page_name)
        assert updated_page is not None
        assert updated_page.metas["description"] == "Page description"
        assert updated_page.metas["keywords"] == "keyword1, keyword2"
        assert updated_page.metas["author"] == "Test Author"
