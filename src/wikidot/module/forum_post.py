"""
Wikidotフォーラムの投稿を扱うモジュール

このモジュールは、Wikidotサイトのフォーラム投稿（スレッド内の各メッセージ）に関連する
クラスや機能を提供する。投稿の情報取得や表示などの操作が可能。
"""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from bs4 import BeautifulSoup, Tag

from ..common.exceptions import NoElementException
from ..util.parser import odate as odate_parser
from ..util.parser import user as user_parser

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
        posts: list["ForumPost"] | None = None,
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

    @staticmethod
    def _parse(thread: "ForumThread", html: BeautifulSoup) -> list["ForumPost"]:
        """
        HTMLから投稿リストをパースする

        Parameters
        ----------
        thread : ForumThread
            投稿が属するスレッド
        html : BeautifulSoup
            パース対象のHTML

        Returns
        -------
        list[ForumPost]
            パースされた投稿のリスト

        Raises
        ------
        NoElementException
            必要な要素が見つからない場合
        """
        posts: list[ForumPost] = []
        post_elements = html.select("div.post")

        for post_elem in post_elements:
            post_id_attr = post_elem.get("id")
            if post_id_attr is None:
                raise NoElementException("Post ID attribute is not found.")
            post_id = int(str(post_id_attr).removeprefix("post-"))

            # 親投稿IDの取得
            parent_id: int | None = None
            parent_container = post_elem.parent
            if parent_container is not None:
                grandparent = parent_container.parent
                if grandparent is not None and grandparent.name != "body":
                    grandparent_class = grandparent.get("class")
                    if isinstance(grandparent_class, list) and "post-container" in grandparent_class:
                        parent_post = grandparent.find("div", class_="post", recursive=False)
                        if parent_post is not None:
                            parent_id_attr = parent_post.get("id")
                            if parent_id_attr is not None:
                                parent_id = int(str(parent_id_attr).removeprefix("post-"))

            # タイトルと本文の取得
            wrapper = post_elem.select_one("div.long")
            if wrapper is None:
                raise NoElementException("Post wrapper element is not found.")

            head = wrapper.select_one("div.head")
            if head is None:
                raise NoElementException("Post head element is not found.")

            title_elem = head.select_one("div.title")
            if title_elem is None:
                raise NoElementException("Post title element is not found.")
            title = title_elem.get_text().strip()

            content_elem = wrapper.select_one("div.content")
            if content_elem is None:
                raise NoElementException("Post content element is not found.")
            text = str(content_elem)

            # 投稿者と日時
            info_elem = head.select_one("div.info")
            if info_elem is None:
                raise NoElementException("Post info element is not found.")

            user_elem = info_elem.select_one("span.printuser")
            if user_elem is None:
                raise NoElementException("Post user element is not found.")
            created_by = user_parser(thread.site.client, user_elem)

            odate_elem = info_elem.select_one("span.odate")
            if odate_elem is None:
                raise NoElementException("Post odate element is not found.")
            created_at = odate_parser(odate_elem)

            # 編集情報（存在する場合）
            edited_by = None
            edited_at = None
            changes_elem = wrapper.select_one("div.changes")
            if changes_elem is not None:
                edit_user_elem = changes_elem.select_one("span.printuser")
                edit_odate_elem = changes_elem.select_one("span.odate")
                if edit_user_elem is not None and edit_odate_elem is not None:
                    edited_by = user_parser(thread.site.client, edit_user_elem)
                    edited_at = odate_parser(edit_odate_elem)

            post = ForumPost(
                thread=thread,
                id=post_id,
                title=title,
                text=text,
                element=post_elem,
                created_by=created_by,
                created_at=created_at,
                edited_by=edited_by,
                edited_at=edited_at,
                _parent_id=parent_id,
            )
            posts.append(post)

        return posts

    @staticmethod
    def acquire_all_in_thread(thread: "ForumThread") -> "ForumPostCollection":
        """
        スレッド内の全投稿を取得する

        指定されたスレッド内のすべての投稿を取得する。
        ページネーションが存在する場合は、すべてのページを巡回する。

        Parameters
        ----------
        thread : ForumThread
            投稿を取得するスレッド

        Returns
        -------
        ForumPostCollection
            スレッド内のすべての投稿を含むコレクション

        Raises
        ------
        NoElementException
            HTML要素の解析に失敗した場合
        """
        posts: list[ForumPost] = []

        first_response = thread.site.amc_request(
            [
                {
                    "moduleName": "forum/ForumViewThreadPostsModule",
                    "pageNo": "1",
                    "t": str(thread.id),
                }
            ]
        )[0]

        first_body = first_response.json()["body"]
        first_html = BeautifulSoup(first_body, "lxml")

        posts.extend(ForumPostCollection._parse(thread, first_html))

        # ページネーション確認
        pager = first_html.select_one("div.pager")
        if pager is None:
            return ForumPostCollection(thread=thread, posts=posts)

        pager_targets = pager.select("span.target")
        if len(pager_targets) < 2:
            return ForumPostCollection(thread=thread, posts=posts)

        last_page = int(pager_targets[-2].get_text().strip())
        if last_page <= 1:
            return ForumPostCollection(thread=thread, posts=posts)

        # 残りのページを取得
        responses = thread.site.amc_request(
            [
                {
                    "moduleName": "forum/ForumViewThreadPostsModule",
                    "pageNo": str(page),
                    "t": str(thread.id),
                }
                for page in range(2, last_page + 1)
            ]
        )

        for response in responses:
            body = response.json()["body"]
            html = BeautifulSoup(body, "lxml")
            posts.extend(ForumPostCollection._parse(thread, html))

        return ForumPostCollection(thread=thread, posts=posts)


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
    element : Tag
        投稿のHTML要素（解析用）
    created_by : AbstractUser
        投稿の作成者
    created_at : datetime
        投稿の作成日時
    edited_by : AbstractUser | None, default None
        投稿の編集者（編集されていない場合はNone）
    edited_at : datetime | None, default None
        投稿の編集日時（編集されていない場合はNone）
    _parent_id : int | None, default None
        親投稿のID（返信元の投稿ID）
    _source : str | None, default None
        投稿のソース（Wikidot記法）
    """

    thread: "ForumThread"
    id: int
    title: str
    text: str
    element: Tag
    created_by: "AbstractUser"
    created_at: datetime
    edited_by: Optional["AbstractUser"] = None
    edited_at: datetime | None = None
    _parent_id: int | None = None
    _source: str | None = None

    def __str__(self) -> str:
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

    @property
    def parent_id(self) -> int | None:
        """
        親投稿のIDを取得する

        Returns
        -------
        int | None
            親投稿のID。親がない場合はNone
        """
        return self._parent_id

    @property
    def source(self) -> str:
        """
        投稿のソース（Wikidot記法）を取得する

        ソースが未取得の場合は自動的に取得処理を行う。

        Returns
        -------
        str
            投稿のソース（Wikidot記法）

        Raises
        ------
        NoElementException
            ソース要素が見つからない場合
        """
        if self._source is None:
            response = self.thread.site.amc_request(
                [
                    {
                        "moduleName": "forum/sub/ForumEditPostFormModule",
                        "threadId": self.thread.id,
                        "postId": self.id,
                    }
                ]
            )[0]

            html = BeautifulSoup(response.json()["body"], "lxml")
            source_elem = html.select_one("textarea[name='source']")
            if source_elem is None:
                raise NoElementException("Source textarea is not found.")
            self._source = source_elem.get_text()

        return self._source

    def edit(self, source: str, title: str | None = None) -> "ForumPost":
        """
        投稿を編集する

        投稿の内容を更新する。タイトルを指定しない場合は現在のタイトルを維持する。

        Parameters
        ----------
        source : str
            新しいソース（Wikidot記法）
        title : str | None, default None
            新しいタイトル（Noneの場合は現在のタイトルを維持）

        Returns
        -------
        ForumPost
            自身（メソッドチェーン用）

        Raises
        ------
        LoginRequiredException
            ログインしていない場合
        WikidotStatusCodeException
            編集に失敗した場合
        NoElementException
            リビジョンID要素が見つからない場合
        """
        self.thread.site.client.login_check()

        # 現在のリビジョンIDを取得
        form_response = self.thread.site.amc_request(
            [
                {
                    "moduleName": "forum/sub/ForumEditPostFormModule",
                    "threadId": self.thread.id,
                    "postId": self.id,
                }
            ]
        )[0]

        html = BeautifulSoup(form_response.json()["body"], "lxml")
        revision_elem = html.select_one("input[name='currentRevisionId']")
        if revision_elem is None:
            raise NoElementException("Current revision ID input is not found.")
        current_revision_id = int(str(revision_elem["value"]))

        # 編集を保存
        self.thread.site.amc_request(
            [
                {
                    "action": "ForumAction",
                    "event": "saveEditPost",
                    "moduleName": "Empty",
                    "postId": self.id,
                    "currentRevisionId": current_revision_id,
                    "title": title if title is not None else self.title,
                    "source": source,
                }
            ]
        )

        # ローカル状態を更新
        if title is not None:
            self.title = title
        self._source = source

        return self
