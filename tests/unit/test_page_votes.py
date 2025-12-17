"""PageVotesモジュールのユニットテスト"""

from unittest.mock import MagicMock

import pytest

from wikidot.module.page_votes import PageVote, PageVoteCollection


class TestPageVoteCollection:
    """PageVoteCollectionのテスト"""

    def test_init_with_page_and_votes(self):
        """ページと投票リストで初期化"""
        page = MagicMock()
        vote1 = MagicMock(spec=PageVote)
        vote2 = MagicMock(spec=PageVote)

        collection = PageVoteCollection(page, [vote1, vote2])

        assert collection.page == page
        assert len(collection) == 2

    def test_init_with_empty_votes(self):
        """空の投票リストで初期化"""
        page = MagicMock()

        collection = PageVoteCollection(page, [])

        assert collection.page == page
        assert len(collection) == 0

    def test_iter(self):
        """イテレーション"""
        page = MagicMock()
        user1 = MagicMock()
        user1.id = 1
        user2 = MagicMock()
        user2.id = 2
        vote1 = PageVote(page=page, user=user1, value=1)
        vote2 = PageVote(page=page, user=user2, value=-1)

        collection = PageVoteCollection(page, [vote1, vote2])

        votes = list(collection)
        assert len(votes) == 2
        assert votes[0].value == 1
        assert votes[1].value == -1

    def test_find_existing_vote(self):
        """存在する投票を検索"""
        page = MagicMock()
        user1 = MagicMock()
        user1.id = 12345
        user2 = MagicMock()
        user2.id = 67890
        vote1 = PageVote(page=page, user=user1, value=1)
        vote2 = PageVote(page=page, user=user2, value=-1)

        collection = PageVoteCollection(page, [vote1, vote2])

        search_user = MagicMock()
        search_user.id = 12345

        result = collection.find(search_user)

        assert result.value == 1
        assert result.user.id == 12345

    def test_find_nonexistent_vote_raises(self):
        """存在しない投票の検索でValueError"""
        page = MagicMock()
        page.__str__ = lambda x: "TestPage"
        user1 = MagicMock()
        user1.id = 12345
        vote1 = PageVote(page=page, user=user1, value=1)

        collection = PageVoteCollection(page, [vote1])

        search_user = MagicMock()
        search_user.id = 99999
        search_user.__str__ = lambda x: "UnknownUser"

        with pytest.raises(ValueError, match="has not voted"):
            collection.find(search_user)


class TestPageVote:
    """PageVoteのテスト"""

    def test_init(self):
        """初期化"""
        page = MagicMock()
        user = MagicMock()

        vote = PageVote(page=page, user=user, value=1)

        assert vote.page == page
        assert vote.user == user
        assert vote.value == 1

    def test_positive_vote(self):
        """正の投票"""
        page = MagicMock()
        user = MagicMock()

        vote = PageVote(page=page, user=user, value=1)

        assert vote.value == 1

    def test_negative_vote(self):
        """負の投票"""
        page = MagicMock()
        user = MagicMock()

        vote = PageVote(page=page, user=user, value=-1)

        assert vote.value == -1

    def test_numeric_vote(self):
        """数値投票（5段階評価など）"""
        page = MagicMock()
        user = MagicMock()

        vote = PageVote(page=page, user=user, value=5)

        assert vote.value == 5
