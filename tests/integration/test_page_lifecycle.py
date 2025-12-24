"""ページライフサイクル（作成→取得→編集→削除）の統合テスト"""

from __future__ import annotations

import contextlib

import pytest

from .conftest import generate_page_name


class TestPageLifecycle:
    """ページライフサイクルテスト

    テストは順番に実行され、前のテストで作成したページを使用する。
    """

    @pytest.fixture(autouse=True)
    def setup(self, site):
        """テストセットアップ"""
        self.site = site
        self.page_name = generate_page_name("lifecycle")
        self.page = None
        yield
        # クリーンアップ
        if self.page is not None:
            with contextlib.suppress(Exception):
                self.page.destroy()
        else:
            # ページオブジェクトがない場合は名前で削除を試行
            with contextlib.suppress(Exception):
                page = self.site.page.get(self.page_name, raise_when_not_found=False)
                if page is not None:
                    page.destroy()

    def test_1_page_create(self):
        """1. ページ作成"""
        self.site.page.create(
            fullname=self.page_name,
            title="Test Page",
            source="This is test content.",
            comment="Initial creation",
        )
        # 作成確認
        self.page = self.site.page.get(self.page_name)
        assert self.page is not None
        assert self.page.fullname == self.page_name

    def test_2_page_get(self):
        """2. 作成ページ取得"""
        # まずページを作成
        self.site.page.create(
            fullname=self.page_name,
            title="Test Page",
            source="This is test content.",
        )
        self.page = self.site.page.get(self.page_name)

        assert self.page is not None
        assert self.page.fullname == self.page_name
        assert self.page.title == "Test Page"

    def test_3_page_source(self):
        """3. ページソース取得"""
        # まずページを作成
        self.site.page.create(
            fullname=self.page_name,
            title="Test Page",
            source="This is test content.",
        )
        self.page = self.site.page.get(self.page_name)

        assert self.page is not None
        source = self.page.source
        assert source is not None
        assert source.wiki_text == "This is test content."

    def test_4_page_edit(self):
        """4. ページ編集"""
        # まずページを作成
        self.site.page.create(
            fullname=self.page_name,
            title="Test Page",
            source="Original content.",
        )
        self.page = self.site.page.get(self.page_name)
        assert self.page is not None

        # 編集
        self.page.edit(
            title="Updated Test Page",
            source="Updated content.",
            comment="Test edit",
        )

        # 再取得して確認
        updated_page = self.site.page.get(self.page_name)
        assert updated_page is not None
        assert updated_page.title == "Updated Test Page"
        assert updated_page.source.wiki_text == "Updated content."

    def test_5_page_delete(self):
        """5. ページ削除"""
        # まずページを作成
        self.site.page.create(
            fullname=self.page_name,
            title="Test Page",
            source="Content to be deleted.",
        )
        self.page = self.site.page.get(self.page_name)
        assert self.page is not None

        # 削除
        self.page.destroy()
        self.page = None  # クリーンアップ不要

        # NOTE: 削除確認はWikidotのeventual consistencyにより不安定なためスキップ
        # destroy()の成功をもって削除完了とする（fixtureでクリーンアップも実行される）
