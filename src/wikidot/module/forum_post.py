"""
Wikidotフォーラムの投稿を扱うモジュール

このモジュールは、Wikidotサイトのフォーラム投稿（スレッド内の各メッセージ）に関連する
クラスや機能を提供する。投稿の情報取得や表示などの操作が可能。
"""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from .forum_thread import ForumThread
    from .user import AbstractUser


class ForumPostCollection(list["ForumPost"]):
    """
    フォーラム投稿のコレクションを表すクラス

    フォーラムスレッド内の複数の投稿を格納し、一括して操作するためのリスト拡張クラス。
    """

    def __init__(
        self,
        thread: Optional["ForumThread"] = None,
        posts: Optional[list["ForumPost"]] = None,
    ):
        """
        初期化メソッド

        Parameters
        ----------
        thread : ForumThread | None, default None
            投稿が属するスレッド。Noneの場合は最初の投稿から推測する
        posts : list[ForumPost] | None, default None
            格納する投稿のリスト
        """
        super().__init__(posts or [])

        if thread is not None:
            self.thread = thread
        else:
            self.thread = self[0].thread

    def __iter__(self) -> Iterator["ForumPost"]:
        """
        コレクション内の投稿を順に返すイテレータ

        Returns
        -------
        Iterator[ForumPost]
            投稿オブジェクトのイテレータ
        """
        return super().__iter__()

    def find(self, id: int) -> Optional["ForumPost"]:
        """
        指定したIDの投稿を取得する

        Parameters
        ----------
        id : int
            取得する投稿のID

        Returns
        -------
        ForumPost | None
            指定したIDの投稿。存在しない場合はNone
        """
        for post in self:
            if post.id == id:
                return post
        return None

    # @staticmethod
    # def _parse(thread: "ForumThread", html: BeautifulSoup) -> list["ForumPost"]:
    #     pass


@dataclass
class ForumPost:
    """
    Wikidotフォーラムの投稿を表すクラス

    フォーラムスレッド内の個別の投稿（メッセージ）に関する情報を保持する。
    投稿のタイトル、本文、作成者、作成日時などの情報を提供する。

    Attributes
    ----------
    thread : ForumThread
        投稿が属するスレッド
    id : int
        投稿ID
    title : str
        投稿のタイトル
    text : str
        投稿の本文（HTMLテキスト）
    element : BeautifulSoup
        投稿のHTML要素（解析用）
    created_by : AbstractUser
        投稿の作成者
    created_at : datetime
        投稿の作成日時
    edited_by : AbstractUser | None, default None
        投稿の編集者（編集されていない場合はNone）
    edited_at : datetime | None, default None
        投稿の編集日時（編集されていない場合はNone）
    _parent : ForumPost | None, default None
        親投稿（返信元の投稿）
    _source : str | None, default None
        投稿のソース（Wikidot記法）
    """

    thread: "ForumThread"
    id: int
    title: str
    text: str
    element: BeautifulSoup
    created_by: "AbstractUser"
    created_at: datetime
    edited_by: Optional["AbstractUser"] = None
    edited_at: Optional[datetime] = None
    _parent: Optional["ForumPost"] = None
    _source: Optional[str] = None

    def __str__(self):
        """
        オブジェクトの文字列表現

        Returns
        -------
        str
            投稿の文字列表現
        """
        return (
            f"ForumPost(thread={self.thread}, id={self.id}, title={self.title}, "
            f"text={self.text}, created_by={self.created_by}, created_at={self.created_at}, "
            f"edited_by={self.edited_by}, edited_at={self.edited_at})"
        )
