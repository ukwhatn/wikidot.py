"""ページリビジョン（編集履歴）の統合テスト"""

from __future__ import annotations

import pytest

from .conftest import generate_page_name


class TestPageRevision:
    """ページリビジョン操作テスト"""

    @pytest.fixture(autouse=True)
    def setup(self, site):
        """テストセットアップ - ページを作成して編集"""
        self.site = site
        self.page_name = generate_page_name("revision")

        # テスト用ページを作成
        self.site.page.create(
            fullname=self.page_name,
            title="Revision Test Page",
            source="Initial content.",
        )
        self.page = self.site.page.get(self.page_name)
        assert self.page is not None

        # 編集してリビジョンを作成
        self.page.edit(
            source="Updated content.",
            comment="First edit",
        )

        yield

        # クリーンアップ
        try:
            page = self.site.page.get(self.page_name, raise_when_not_found=False)
            if page is not None:
                page.destroy()
        except Exception:
            pass

    def test_1_get_revisions(self):
        """1. リビジョン一覧取得"""
        # 再取得
        page = self.site.page.get(self.page_name)
        assert page is not None

        revisions = page.revisions
        assert revisions is not None
        # 作成 + 編集で少なくとも1つ以上のリビジョンがある
        assert len(revisions) >= 1

    def test_2_revision_properties(self):
        """2. リビジョンプロパティ確認"""
        page = self.site.page.get(self.page_name)
        assert page is not None

        revisions = page.revisions
        assert len(revisions) >= 1

        latest_rev = revisions[-1]  # 最新リビジョン
        assert latest_rev.id is not None
        assert latest_rev.rev_no is not None
        assert latest_rev.created_by is not None
        assert latest_rev.created_at is not None

    def test_3_get_latest_revision(self):
        """3. 最新リビジョン取得"""
        page = self.site.page.get(self.page_name)
        assert page is not None

        latest = page.latest_revision
        assert latest is not None
        assert latest.rev_no == page.revisions_count

    def test_4_revision_source(self):
        """4. リビジョンソース取得"""
        page = self.site.page.get(self.page_name)
        assert page is not None

        revisions = page.revisions
        assert len(revisions) >= 1

        # 最新リビジョンのソースを取得
        latest_rev = revisions[-1]
        source = latest_rev.source
        assert source is not None
        assert source.wiki_text is not None
