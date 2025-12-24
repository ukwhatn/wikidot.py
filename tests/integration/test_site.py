"""サイト取得・ページ取得の統合テスト"""

from __future__ import annotations

import pytest

from wikidot.common.exceptions import NotFoundException


class TestSiteGet:
    """サイト取得テスト"""

    def test_site_get(self, site):
        """サイト取得"""
        assert site is not None
        assert site.unix_name == "ukwhatn-ci"
        assert site.id > 0

    def test_site_has_title(self, site):
        """サイトにタイトルがある"""
        assert site.title is not None
        assert len(site.title) > 0


class TestPageGet:
    """ページ取得テスト"""

    def test_get_existing_page(self, site):
        """既存ページ取得（startページ）"""
        page = site.page.get("start")
        assert page is not None
        assert page.fullname == "start"

    def test_get_nonexistent_page(self, site):
        """存在しないページ取得"""
        with pytest.raises(NotFoundException):
            site.page.get("nonexistent-page-12345678")

    def test_page_has_properties(self, site):
        """ページにプロパティがある"""
        page = site.page.get("start")
        assert page is not None

        # 基本プロパティ
        assert page.fullname is not None
        assert page.title is not None
        assert page.created_at is not None

        # 数値プロパティ
        assert page.rating is not None
        # NOTE: 初期ページはrevisions_countが0になる場合がある
        assert page.revisions_count >= 0
