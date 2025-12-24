"""ページ投票の統合テスト"""

from __future__ import annotations


class TestPageVotes:
    """ページ投票操作テスト"""

    def test_1_get_votes_from_existing_page(self, site):
        """1. 既存ページの投票情報取得"""
        # startページの投票情報を取得
        page = site.page.get("start")
        assert page is not None

        votes = page.votes
        assert votes is not None
        # 投票がなくても空のコレクションが返る
        assert isinstance(votes, list)

    def test_2_votes_properties(self, site):
        """2. 投票プロパティ確認"""
        page = site.page.get("start")
        assert page is not None

        votes = page.votes
        # 投票がある場合はプロパティを確認
        if len(votes) > 0:
            vote = votes[0]
            assert vote.page is not None
            assert vote.user is not None
            assert vote.value is not None
