"""
Wikidotページの投票（レーティング）を扱うモジュール

このモジュールは、Wikidotページの投票（レーティング）に関連するクラスや機能を提供する。
ページへの投票情報の取得や表示などの操作が可能。
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .page import Page
    from .user import AbstractUser


class PageVoteCollection(list["PageVote"]):
    """
    ページ投票のコレクションを表すクラス

    ページに対する複数の投票（レーティング）を格納し、一括して操作するための
    リスト拡張クラス。
    """

    def __init__(self, page: "Page", votes: list["PageVote"]):
        """
        初期化メソッド

        Parameters
        ----------
        page : Page
            投票が属するページ
        votes : list[PageVote]
            格納する投票のリスト
        """
        super().__init__(votes)
        self.page = page

    def __iter__(self) -> Iterator["PageVote"]:
        """
        コレクション内の投票を順に返すイテレータ

        Returns
        -------
        Iterator[PageVote]
            投票オブジェクトのイテレータ
        """
        return super().__iter__()

    def find(self, user: "AbstractUser") -> "PageVote":
        """
        指定ユーザーの投票を取得する

        Parameters
        ----------
        user : AbstractUser
            投票を行ったユーザー

        Returns
        -------
        PageVote
            ユーザーの投票情報
        """
        for vote in self:
            if vote.user.id == user.id:
                return vote
        raise ValueError(f"User {user} has not voted on page {self.page}")


@dataclass
class PageVote:
    """
    ページへの投票（レーティング）を表すクラス

    ユーザーがページに対して行った投票（評価）の情報を保持する。

    Attributes
    ----------
    page : Page
        投票が属するページ
    user : AbstractUser
        投票を行ったユーザー
    value : int
        投票値（+1/-1 または 数値）
    """

    page: "Page"
    user: "AbstractUser"
    value: int
