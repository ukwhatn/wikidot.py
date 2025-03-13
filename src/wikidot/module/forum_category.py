"""
Wikidotフォーラムのカテゴリを扱うモジュール

このモジュールは、Wikidotサイトのフォーラムカテゴリに関連するクラスや機能を提供する。
フォーラムカテゴリの情報取得やスレッド一覧の取得などの操作が可能。
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from bs4 import BeautifulSoup

from ..common.exceptions import NoElementException
from .forum_thread import ForumThread, ForumThreadCollection

if TYPE_CHECKING:
    from .site import Site


class ForumCategoryCollection(list["ForumCategory"]):
    """
    フォーラムカテゴリのコレクションを表すクラス

    複数のフォーラムカテゴリを格納し、一括して操作するためのリスト拡張クラス。
    """

    def __init__(
        self,
        site: Optional["Site"] = None,
        categories: Optional[list["ForumCategory"]] = None,
    ):
        """
        初期化メソッド

        Parameters
        ----------
        site : Site | None, default None
            カテゴリが属するサイト。Noneの場合は最初のカテゴリから推測する
        categories : list[ForumCategory] | None, default None
            格納するカテゴリのリスト
        """
        super().__init__(categories or [])

        if site is not None:
            self.site = site
        else:
            self.site = self[0].site

    def __iter__(self) -> Iterator["ForumCategory"]:
        """
        コレクション内のカテゴリを順に返すイテレータ

        Returns
        -------
        Iterator[ForumCategory]
            カテゴリオブジェクトのイテレータ
        """
        return super().__iter__()

    def find(self, id: int) -> Optional["ForumCategory"]:
        """
        カテゴリIDでカテゴリを検索する

        指定されたIDのカテゴリが存在する場合はそのカテゴリオブジェクトを返す。

        Parameters
        ----------
        id : int
            検索するカテゴリのID

        Returns
        -------
        ForumCategory | None
            検索結果のカテゴリオブジェクト。見つからない場合はNone
        """
        for category in self:
            if category.id == id:
                return category
        return None

    @staticmethod
    def acquire_all(site: "Site"):
        """
        サイトのすべてのフォーラムカテゴリを取得する

        指定されたサイトのフォーラムページにアクセスし、
        利用可能なすべてのカテゴリ情報を取得する。

        Parameters
        ----------
        site : Site
            カテゴリを取得するサイト

        Returns
        -------
        ForumCategoryCollection
            取得したフォーラムカテゴリのコレクション

        Raises
        ------
        NoElementException
            必要なHTML要素が見つからない場合
        """
        categories = []

        response = site.amc_request([{"moduleName": "forum/ForumStartModule", "hidden": "true"}])[0]

        body = response.json()["body"]
        html = BeautifulSoup(body, "lxml")

        for row in html.select("table tr.head~tr"):
            name_elem = row.select_one("td.name")
            if name_elem is None:
                raise NoElementException("Name element is not found.")
            name_link_elem = name_elem.select_one("a")
            if name_link_elem is None:
                raise NoElementException("Name link element is not found.")
            name_link_href = name_link_elem.get("href")
            if name_link_href is None:
                raise NoElementException("Name link href is not found.")
            thread_count_elem = row.select_one("td.threads")
            if thread_count_elem is None:
                raise NoElementException("Thread count element is not found.")
            post_count_elem = row.select_one("td.posts")
            if post_count_elem is None:
                raise NoElementException("Post count element is not found.")
            category_id_match = re.search(r"c-(\d+)", str(name_link_href))
            if category_id_match is None:
                raise NoElementException("Category ID is not found.")
            category_id_str = category_id_match.group(1)
            title_elem = name_elem.select_one("a")
            if title_elem is None:
                raise NoElementException("Title element is not found.")
            description_elem = name_elem.select_one("div.description")
            if description_elem is None:
                raise NoElementException("Description element is not found.")

            category = ForumCategory(
                site=site,
                id=int(category_id_str),
                title=title_elem.text,
                description=description_elem.text,
                threads_count=int(thread_count_elem.text),
                posts_count=int(post_count_elem.text),
            )

            categories.append(category)

        return ForumCategoryCollection(site=site, categories=categories)


@dataclass
class ForumCategory:
    """
    Wikidotフォーラムのカテゴリを表すクラス

    フォーラムカテゴリの基本情報とスレッド一覧へのアクセス機能を提供する。

    Attributes
    ----------
    site : Site
        カテゴリが属するサイト
    id : int
        カテゴリID
    title : str
        カテゴリのタイトル
    description : str
        カテゴリの説明文
    threads_count : int
        カテゴリ内のスレッド数
    posts_count : int
        カテゴリ内の投稿数
    _threads : ForumThreadCollection | None
        カテゴリ内のスレッドコレクション（内部キャッシュ用）
    """

    site: "Site"
    id: int
    title: str
    description: str
    threads_count: int
    posts_count: int
    _threads: Optional[ForumThreadCollection] = None

    def __str__(self):
        """
        オブジェクトの文字列表現

        Returns
        -------
        str
            カテゴリの文字列表現
        """
        return (
            f"ForumCategory(id={self.id}, "
            f"title={self.title}, description={self.description}, "
            f"threads_count={self.threads_count}, posts_count={self.posts_count})"
        )

    @property
    def threads(self) -> ForumThreadCollection:
        """
        カテゴリ内のスレッド一覧を取得する

        スレッドリストが未取得の場合は自動的に取得処理を行う。

        Returns
        -------
        ForumThreadCollection
            カテゴリ内のスレッドコレクション
        """
        if self._threads is None:
            self._threads = ForumThreadCollection.acquire_all_in_category(self)
        return self._threads

    @threads.setter
    def threads(self, value):
        """
        カテゴリ内のスレッド一覧を設定する

        Parameters
        ----------
        value : ForumThreadCollection
            設定するスレッドコレクション
        """
        self._threads = value

    def reload_threads(self):
        """
        カテゴリ内のスレッド一覧を再取得する

        キャッシュを無視して最新のスレッド一覧を取得する。

        Returns
        -------
        ForumThreadCollection
            最新のスレッドコレクション
        """
        self._threads = ForumThreadCollection.acquire_all_in_category(self)
        return self._threads

    def create_thread(self, title: str, description: str, source: str):
        """
        カテゴリ内に新しいスレッドを作成する

        Parameters
        ----------
        title : str
            スレッドのタイトル
        description : str
            スレッドの説明文
        source : str
            スレッドの本文（Wikidot記法）

        Returns
        -------
        ForumThread
            作成したスレッドオブジェクト
        """
        self.site.client.login_check()

        # 作成リクエスト
        response = self.site.amc_request(
            [
                {
                    "moduleName": "Empty",
                    "action": "ForumAction",
                    "event": "newThread",
                    "category_id": self.id,
                    "title": title,
                    "description": description,
                    "source": source,
                }
            ]
        )[0].json()

        # responseからthreadIdを取得
        if "threadId" not in response and isinstance(response["threadId"], int):
            raise NoElementException("Thread ID is not found.")

        thread_id: int = response["threadId"]

        return ForumThread.get_from_id(self.site, thread_id, self)
