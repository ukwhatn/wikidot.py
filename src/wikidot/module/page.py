import re
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional, Union

import httpx
from bs4 import BeautifulSoup

from ..common import exceptions
from ..util.parser import odate as odate_parser
from ..util.parser import user as user_parser
from ..util.requestutil import RequestUtil
from .page_revision import PageRevision, PageRevisionCollection
from .page_source import PageSource
from .page_votes import PageVote, PageVoteCollection

if TYPE_CHECKING:
    from .site import Site
    from .user import User

DEFAULT_MODULE_BODY = [
    "fullname",  # ページのフルネーム(str)
    "category",  # カテゴリ(str)
    "name",  # ページ名(str)
    "title",  # タイトル(str)
    "created_at",  # 作成日時(odate element)
    "created_by_linked",  # 作成者(user element)
    "updated_at",  # 更新日時(odate element)
    "updated_by_linked",  # 更新者(user element)
    "commented_at",  # コメント日時(odate element)
    "commented_by_linked",  # コメントしたユーザ(user element)
    "parent_fullname",  # 親ページのフルネーム(str)
    "comments",  # コメント数(int)
    "size",  # サイズ(int)
    "children",  # 子ページ数(int)
    "rating_votes",  # 投票数(int)
    "rating",  # レーティング(int or float)
    "rating_percent",  # 5つ星レーティング(%)
    "revisions",  # リビジョン数(int)
    "tags",  # タグのリスト(list of str)
    "_tags",  # 隠しタグのリスト(list of str)
]


@dataclass
class SearchPagesQuery:
    """
    ページ検索クエリを表すクラス

    Wikidotのページ検索に使用される各種検索条件を定義する。
    ListPagesModuleに渡すためのクエリパラメータをカプセル化している。

    Attributes
    ----------
    pagetype : str, default "*"
        ページタイプ（例: "normal", "admin"等）
    category : str, default "*"
        カテゴリ名
    tags : str | list[str] | None, default None
        検索対象のタグ（文字列または文字列のリスト）
    parent : str | None, default None
        親ページ名
    link_to : str | None, default None
        リンク先ページ名
    created_at : str | None, default None
        作成日時の条件
    updated_at : str | None, default None
        更新日時の条件
    created_by : User | str | None, default None
        作成者による絞り込み
    rating : str | None, default None
        評価値による絞り込み
    votes : str | None, default None
        投票数による絞り込み
    name : str | None, default None
        ページ名による絞り込み
    fullname : str | None, default None
        フルネームによる絞り込み（完全一致）
    range : str | None, default None
        範囲指定
    order : str, default "created_at desc"
        ソート順（例: "created_at desc", "title asc"等）
    offset : int, default 0
        取得開始位置
    limit : int | None, default None
        取得件数制限
    perPage : int, default 250
        1ページあたりの表示件数
    separate : str, default "no"
        個別表示するかどうか
    wrapper : str, default "no"
        ラッパー要素を表示するかどうか
    """

    # selecting pages
    pagetype: Optional[str] = "*"
    category: Optional[str] = "*"
    tags: Optional[str | list[str]] = None
    parent: Optional[str] = None
    link_to: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[Union["User", str]] = None
    rating: Optional[str] = None
    votes: Optional[str] = None
    name: Optional[str] = None
    fullname: Optional[str] = None
    range: Optional[str] = None

    # ordering
    order: str = "created_at desc"

    # pagination
    offset: Optional[int] = 0
    limit: Optional[int] = None
    perPage: Optional[int] = 250
    # layout
    separate: Optional[str] = "no"
    wrapper: Optional[str] = "no"

    def as_dict(self) -> dict[str, Any]:
        """
        クエリパラメータを辞書形式に変換する

        タグがリスト形式の場合は空白区切りの文字列に変換する。

        Returns
        -------
        dict[str, Any]
            APIリクエスト用の辞書形式パラメータ
        """
        res = {k: v for k, v in asdict(self).items() if v is not None}
        if "tags" in res and isinstance(res["tags"], list):
            res["tags"] = " ".join(res["tags"])
        return res


class PageCollection(list["Page"]):
    """
    ページオブジェクトのコレクションを表すクラス

    複数のページオブジェクトを格納し、一括して操作するための機能を提供する。
    ページの検索、一括取得、一括操作などの機能を集約している。
    """

    def __init__(self, site: Optional["Site"] = None, pages: Optional[list["Page"]] = None):
        """
        初期化メソッド

        Parameters
        ----------
        site : Site | None, default None
            ページが属するサイト。Noneの場合は最初のページから推測する
        pages : list[Page] | None, default None
            格納するページのリスト
        """
        super().__init__(pages or [])

        if site is not None:
            self.site = site
        else:
            self.site = self[0].site

    def __iter__(self) -> Iterator["Page"]:
        """
        コレクション内のページを順に返すイテレータ

        Returns
        -------
        Iterator[Page]
            ページオブジェクトのイテレータ
        """
        return super().__iter__()

    def find(self, fullname: str) -> Optional["Page"]:
        """
        指定したフルネームのページを取得する

        Parameters
        ----------
        fullname : str
            取得するページのフルネーム

        Returns
        -------
        Page | None
            指定したフルネームのページ。存在しない場合はNone
        """
        for page in self:
            if page.fullname == fullname:
                return page
        return None

    @staticmethod
    def _parse(site: "Site", html_body: BeautifulSoup):
        """
        ListPagesModuleのレスポンスをパースしてページオブジェクトのリストを生成する

        Parameters
        ----------
        site : Site
            ページが属するサイト
        html_body : BeautifulSoup
            パース対象のHTML

        Returns
        -------
        PageCollection
            パース結果のページコレクション

        Raises
        ------
        NoElementException
            必要な要素が見つからない場合
        """
        pages = []

        for page_element in html_body.select("div.page"):
            page_params = {}

            # レーティング方式を判定
            is_5star_rating = page_element.select_one("span.rating span.page-rate-list-pages-start") is not None

            # 各値を取得
            for set_element in page_element.select("span.set"):
                key_element = set_element.select_one("span.name")
                if key_element is None:
                    raise exceptions.NoElementException("Cannot find key element")
                key = key_element.text.strip()
                value_element = set_element.select_one("span.value")

                if value_element is None:
                    value: Any = None

                elif key in ["created_at", "updated_at", "commented_at"]:
                    odate_element = value_element.select_one("span.odate")
                    if odate_element is None:
                        value = None
                    else:
                        value = odate_parser(odate_element)

                elif key in [
                    "created_by_linked",
                    "updated_by_linked",
                    "commented_by_linked",
                ]:
                    printuser_element = value_element.select_one("span.printuser")
                    if printuser_element is None:
                        value = None
                    else:
                        value = user_parser(site.client, printuser_element)

                elif key in ["tags", "_tags"]:
                    value = value_element.text.split()

                elif key in ["rating_votes", "comments", "size", "revisions"]:
                    value = int(value_element.text.strip())

                elif key in ["rating"]:
                    if is_5star_rating:
                        value = float(value_element.text.strip())
                    else:
                        value = int(value_element.text.strip())

                elif key in ["rating_percent"]:
                    if is_5star_rating:
                        value = float(value_element.text.strip()) / 100
                    else:
                        value = None

                else:
                    value = value_element.text.strip()

                # keyを変換
                if "_linked" in key:
                    key = key.replace("_linked", "")
                elif key in ["comments", "children", "revisions"]:
                    key = f"{key}_count"
                elif key in ["rating_votes"]:
                    key = "votes_count"

                page_params[key] = value

            # タグのリストを統合
            for key in ["tags", "_tags"]:
                if key not in page_params or page_params[key] is None:
                    page_params[key] = []

            page_params["tags"] = page_params["tags"] + page_params["_tags"]
            del page_params["_tags"]

            # ページオブジェクトを作成
            pages.append(Page(site, **page_params))

        return PageCollection(site, pages)

    @staticmethod
    def search_pages(site: "Site", query: SearchPagesQuery = SearchPagesQuery()):
        """
        サイト内のページを検索する

        指定されたクエリに基づいてサイト内のページを検索し、結果を返す。
        Wikidotの「ListPagesModule」を使用して検索を実行する。

        Parameters
        ----------
        site : Site
            検索対象のサイト
        query : SearchPagesQuery, default SearchPagesQuery()
            検索条件

        Returns
        -------
        PageCollection
            検索結果のページコレクション

        Raises
        ------
        ForbiddenException
            プライベートサイトでアクセスが拒否された場合
        WikidotStatusCodeException
            その他のAPIエラーが発生した場合
        NoElementException
            レスポンスからページ情報を抽出できない場合
        """
        # 初回実行
        query_dict = query.as_dict()
        query_dict["moduleName"] = "list/ListPagesModule"
        query_dict["module_body"] = (
            '[[div class="page"]]\n'
            + "".join(
                [
                    f'[[span class="set {key}"]]'
                    f'[[span class="name"]] {key} [[/span]]'
                    f'[[span class="value"]] %%{key}%% [[/span]]'
                    f"[[/span]]"
                    for key in DEFAULT_MODULE_BODY
                ]
            )
            + "\n[[/div]]"
        )

        try:
            response = site.amc_request([query_dict])[0]
        except exceptions.WikidotStatusCodeException as e:
            if e.status_code == "not_ok":
                raise exceptions.ForbiddenException("Failed to get pages, target site may be private") from e
            raise e

        body = response.json()["body"]

        first_page_html_body = BeautifulSoup(body, "lxml")

        total = 1
        html_bodies = [first_page_html_body]
        # pagerが存在する
        if first_page_html_body.select_one("div.pager") is not None:
            # span.target[-2] > a から最大ページ数を取得
            last_pager_element = first_page_html_body.select("div.pager span.target")[-2]
            last_pager_link_element = last_pager_element.select_one("a")
            if last_pager_link_element is None:
                raise exceptions.NoElementException("Cannot find last pager link")
            total = int(last_pager_link_element.text.strip())

        if total > 1:
            request_bodies = []
            for i in range(1, total):
                _query_dict = query_dict.copy()
                _query_dict["offset"] = i * (query.perPage or 250)
                request_bodies.append(_query_dict)

            responses = site.amc_request(request_bodies)
            html_bodies.extend([BeautifulSoup(response.json()["body"], "lxml") for response in responses])

        pages = []
        for html_body in html_bodies:
            pages.extend(PageCollection._parse(site, html_body))

        return PageCollection(site, pages)

    @staticmethod
    def _acquire_page_ids(site: "Site", pages: list["Page"]):
        """
        ページIDを取得する内部メソッド

        未取得のページIDを一括で取得する。norender/noredirectオプション付きで
        ページにアクセスし、ページソースからIDを抽出する。

        Parameters
        ----------
        site : Site
            ページが属するサイト
        pages : list[Page]
            対象ページのリスト

        Returns
        -------
        list[Page]
            ID情報が更新されたページのリスト

        Raises
        ------
        UnexpectedException
            ページIDが見つからない場合や、予期しないレスポンスタイプの場合
        """
        # pagesからidが設定されていないものを抽出
        target_pages = [page for page in pages if not page.is_id_acquired()]

        # なければ終了
        if len(target_pages) == 0:
            return pages

        # norender, noredirectでアクセス
        responses = RequestUtil.request(
            site.client,
            "GET",
            [f"{page.get_url()}/norender/true/noredirect/true" for page in target_pages],
        )

        # "WIKIREQUEST.info.pageId = xxx;"の値をidに設定
        for index, response in enumerate(responses):
            if not isinstance(response, httpx.Response):
                raise exceptions.UnexpectedException(f"Unexpected response type: {type(response)}")
            source = response.text

            id_match = re.search(r"WIKIREQUEST\.info\.pageId = (\d+);", source)
            if id_match is None:
                raise exceptions.UnexpectedException(f"Cannot find page id: {target_pages[index].fullname}")
            target_pages[index].id = int(id_match.group(1))

        return pages

    def get_page_ids(self):
        """
        コレクション内の全ページのIDを取得する

        IDが設定されていないページについて、一括でIDを取得する。

        Returns
        -------
        PageCollection
            自身（メソッドチェーン用）
        """
        return PageCollection._acquire_page_ids(self.site, self)

    @staticmethod
    def _acquire_page_sources(site: "Site", pages: list["Page"]):
        """
        ページソースを取得する内部メソッド

        指定されたページのソースコード（Wikidot記法）を一括で取得する。

        Parameters
        ----------
        site : Site
            ページが属するサイト
        pages : list[Page]
            対象ページのリスト

        Returns
        -------
        list[Page]
            ソース情報が更新されたページのリスト

        Raises
        ------
        NoElementException
            ソース要素が見つからない場合
        """
        if len(pages) == 0:
            return pages

        responses = site.amc_request(
            [{"moduleName": "viewsource/ViewSourceModule", "page_id": page.id} for page in pages]
        )

        for page, responses in zip(pages, responses):
            body = responses.json()["body"]
            html = BeautifulSoup(body, "lxml")
            source_element = html.select_one("div.page-source")
            if source_element is None:
                raise exceptions.NoElementException("Cannot find source element")
            source = source_element.text.strip().removeprefix("\t")
            page.source = PageSource(page, source)
        return pages

    def get_page_sources(self):
        """
        コレクション内の全ページのソースコードを取得する

        ページのソースコード（Wikidot記法）を一括で取得し、各ページのsourceプロパティに設定する。

        Returns
        -------
        PageCollection
            自身（メソッドチェーン用）
        """
        return PageCollection._acquire_page_sources(self.site, self)

    @staticmethod
    def _acquire_page_revisions(site: "Site", pages: list["Page"]):
        """
        ページリビジョン履歴を取得する内部メソッド

        指定されたページのリビジョン（編集履歴）を一括で取得する。

        Parameters
        ----------
        site : Site
            ページが属するサイト
        pages : list[Page]
            対象ページのリスト

        Returns
        -------
        list[Page]
            リビジョン情報が更新されたページのリスト

        Raises
        ------
        NoElementException
            必要な要素が見つからない場合
        """
        if len(pages) == 0:
            return pages

        responses = site.amc_request(
            [
                {
                    "moduleName": "history/PageRevisionListModule",
                    "page_id": page.id,
                    "options": {"all": True},
                    "perpage": 100000000,  # pagerを使わずに全て取得
                }
                for page in pages
            ]
        )

        for page, response in zip(pages, responses):
            body = response.json()["body"]
            revs = []
            body_html = BeautifulSoup(body, "lxml")
            for rev_element in body_html.select("table.page-history > tr[id^=revision-row-]"):
                rev_id = int(str(rev_element["id"]).removeprefix("revision-row-"))

                tds = rev_element.select("td")
                rev_no = int(tds[0].text.strip().removesuffix("."))
                created_by_elem = tds[4].select_one("span.printuser")
                if created_by_elem is None:
                    raise exceptions.NoElementException("Cannot find created by element")
                created_by = user_parser(page.site.client, created_by_elem)

                created_at_elem = tds[5].select_one("span.odate")
                if created_at_elem is None:
                    raise exceptions.NoElementException("Cannot find created at element")
                created_at = odate_parser(created_at_elem)

                comment = tds[6].text.strip()

                revs.append(
                    PageRevision(
                        page=page,
                        id=rev_id,
                        rev_no=rev_no,
                        created_by=created_by,
                        created_at=created_at,
                        comment=comment,
                    )
                )
            page.revisions = PageRevisionCollection(page, revs)

        return pages

    def get_page_revisions(self):
        """
        コレクション内の全ページのリビジョン履歴を取得する

        ページのリビジョン（編集履歴）を一括で取得し、各ページのrevisionsプロパティに設定する。

        Returns
        -------
        PageCollection
            自身（メソッドチェーン用）
        """
        return PageCollection._acquire_page_revisions(self.site, self)

    @staticmethod
    def _acquire_page_votes(site: "Site", pages: list["Page"]):
        """
        ページへの投票情報を取得する内部メソッド

        指定されたページへの投票（レーティング）情報を一括で取得する。

        Parameters
        ----------
        site : Site
            ページが属するサイト
        pages : list[Page]
            対象ページのリスト

        Returns
        -------
        list[Page]
            投票情報が更新されたページのリスト

        Raises
        ------
        UnexpectedException
            ユーザー要素と投票値要素の数が一致しない場合
        """
        if len(pages) == 0:
            return pages

        responses = site.amc_request(
            [{"moduleName": "pagerate/WhoRatedPageModule", "pageId": page.id} for page in pages]
        )

        for page, response in zip(pages, responses):
            body = response.json()["body"]
            html = BeautifulSoup(body, "lxml")
            user_elems = html.select("span.printuser")
            value_elems = html.select("span[style^='color']")

            if len(user_elems) != len(value_elems):
                raise exceptions.UnexpectedException("User and value count mismatch")

            users = [user_parser(site.client, user_elem) for user_elem in user_elems]
            values = []
            for value in value_elems:
                _v = value.text.strip()
                if _v == "+":
                    values.append(1)
                elif _v == "-":
                    values.append(-1)
                else:
                    values.append(int(_v))

            votes = [PageVote(page, user, vote) for user, vote in zip(users, values)]
            page._votes = PageVoteCollection(page, votes)

        return pages

    def get_page_votes(self):
        """
        コレクション内の全ページの投票情報を取得する

        ページへの投票（レーティング）情報を一括で取得し、各ページのvotesプロパティに設定する。

        Returns
        -------
        PageCollection
            自身（メソッドチェーン用）
        """
        return PageCollection._acquire_page_votes(self.site, self)


@dataclass
class Page:
    """
    Wikidotページを表すクラス

    Wikidotサイト内の単一ページに関する情報と操作機能を提供する。
    ページの基本情報、メタデータ、履歴、評価などを管理する。

    Attributes
    ----------
    site : Site
        ページが存在するサイト
    fullname : str
        ページのフルネーム（例: "コンポーネント:scp-173"）
    name : str
        ページ名（例: "scp-173"）
    category : str
        カテゴリ（例: "コンポーネント"）
    title : str
        ページのタイトル
    children_count : int
        子ページの数
    comments_count : int
        コメント数
    size : int
        ページのサイズ（バイト数）
    rating : int | float
        レーティング（+/-評価の場合はint、5つ星評価の場合はfloat）
    votes_count : int
        投票数
    rating_percent : float
        5つ星評価システムにおけるパーセンテージ値（0.0～1.0）
    revisions_count : int
        リビジョン（編集履歴）の数
    parent_fullname : str | None
        親ページのフルネーム（親がない場合はNone）
    tags : list[str]
        付けられたタグのリスト
    created_by : User
        ページの作成者
    created_at : datetime
        ページの作成日時
    updated_by : User
        最終更新者
    updated_at : datetime
        最終更新日時
    commented_by : User | None
        最後にコメントしたユーザー（コメントがない場合はNone）
    commented_at : datetime | None
        最後のコメント日時（コメントがない場合はNone）
    _id : int | None
        ページのID（内部識別子）
    _source : PageSource | None
        ページのソースコード（要求時に取得）
    _revisions : PageRevisionCollection | None
        ページのリビジョン履歴（要求時に取得）
    _votes : PageVoteCollection | None
        ページへの投票情報（要求時に取得）
    _metas : dict[str, str] | None
        ページのメタタグ情報（要求時に取得）
    """

    site: "Site"
    fullname: str
    name: str
    category: str
    title: str
    children_count: int
    comments_count: int
    size: int
    rating: int | float
    votes_count: int
    rating_percent: float
    revisions_count: int
    parent_fullname: str | None
    tags: list[str]
    created_by: "User"
    created_at: datetime
    updated_by: "User"
    updated_at: datetime
    commented_by: Optional["User"]
    commented_at: Optional[datetime]
    _id: Optional[int] = None
    _source: Optional[PageSource] = None
    _revisions: Optional[PageRevisionCollection] = None
    _votes: Optional[PageVoteCollection] = None
    _metas: Optional[dict[str, str]] = None

    def get_url(self) -> str:
        """
        ページの完全なURLを取得する

        サイトのURLとページ名から完全なページURLを生成する。

        Returns
        -------
        str
            ページの完全なURL
        """
        return f"{self.site.url}/{self.fullname}"

    @property
    def id(self) -> int:
        """
        ページIDを取得する

        IDが未取得の場合は自動的に取得処理を行う。

        Returns
        -------
        int
            ページID

        Raises
        ------
        NotFoundException
            ページIDが見つからない場合
        """
        if not self.is_id_acquired():
            PageCollection(self.site, [self]).get_page_ids()

        if self._id is None:
            raise exceptions.NotFoundException("Cannot find page id")

        return self._id

    @id.setter
    def id(self, value: int):
        """
        ページIDを設定する

        Parameters
        ----------
        value : int
            設定するページID
        """
        self._id = value

    def is_id_acquired(self) -> bool:
        """
        ページIDが既に取得済みかどうかを確認する

        Returns
        -------
        bool
            IDが取得済みの場合はTrue、未取得の場合はFalse
        """
        return self._id is not None

    @property
    def source(self) -> PageSource:
        """
        ページのソースコードを取得する

        ソースコードが未取得の場合は自動的に取得処理を行う。

        Returns
        -------
        PageSource
            ページのソースコードオブジェクト

        Raises
        ------
        NotFoundException
            ページソースが見つからない場合
        """
        if self._source is None:
            PageCollection(self.site, [self]).get_page_sources()

        if self._source is None:
            raise exceptions.NotFoundException("Cannot find page source")

        return self._source

    @source.setter
    def source(self, value: PageSource):
        """
        ページのソースコードを設定する

        Parameters
        ----------
        value : PageSource
            設定するソースコードオブジェクト
        """
        self._source = value

    @property
    def revisions(self) -> PageRevisionCollection:
        """
        ページのリビジョン履歴を取得する

        リビジョン履歴が未取得の場合は自動的に取得処理を行う。

        Returns
        -------
        PageRevisionCollection
            ページのリビジョン履歴コレクション

        Raises
        ------
        NotFoundException
            リビジョン履歴が見つからない場合
        """
        if self._revisions is None:
            PageCollection(self.site, [self]).get_page_revisions()
        return PageRevisionCollection(self, self._revisions)

    @revisions.setter
    def revisions(self, value: list["PageRevision"] | PageRevisionCollection):
        """
        ページのリビジョン履歴を設定する

        Parameters
        ----------
        value : list[PageRevision] | PageRevisionCollection
            設定するリビジョンのリストまたはコレクション
        """
        if isinstance(value, list):
            self._revisions = PageRevisionCollection(self, value)
        else:
            self._revisions = value

    @property
    def latest_revision(self) -> PageRevision:
        """
        ページの最新リビジョンを取得する

        revision_countとrev_noが一致するリビジョンを最新として返す。

        Returns
        -------
        PageRevision
            最新のリビジョンオブジェクト

        Raises
        ------
        NotFoundException
            最新リビジョンが見つからない場合
        """
        # revision_countとrev_noが一致するものを取得
        for revision in self.revisions:
            if revision.rev_no == self.revisions_count:
                return revision

        raise exceptions.NotFoundException("Cannot find latest revision")

    @property
    def votes(self) -> PageVoteCollection:
        """
        ページへの投票情報を取得する

        投票情報が未取得の場合は自動的に取得処理を行う。

        Returns
        -------
        PageVoteCollection
            ページへの投票情報コレクション

        Raises
        ------
        NotFoundException
            投票情報が見つからない場合
        """
        if self._votes is None:
            PageCollection(self.site, [self]).get_page_votes()

        if self._votes is None:
            raise exceptions.NotFoundException("Cannot find page votes")

        return self._votes

    @votes.setter
    def votes(self, value: PageVoteCollection):
        """
        ページへの投票情報を設定する

        Parameters
        ----------
        value : PageVoteCollection
            設定する投票情報コレクション
        """
        self._votes = value

    def destroy(self):
        """
        ページを削除する

        ログイン状態でのみ実行可能。ページの完全削除を行う。

        Raises
        ------
        LoginRequiredException
            ログインしていない場合
        WikidotStatusCodeException
            削除に失敗した場合
        """
        self.site.client.login_check()
        self.site.amc_request(
            [
                {
                    "action": "WikiPageAction",
                    "event": "deletePage",
                    "page_id": self.id,
                    "moduleName": "Empty",
                }
            ]
        )

    @property
    def metas(self) -> dict[str, str]:
        """
        ページのメタタグ情報を取得する

        メタタグ情報が未取得の場合は自動的に取得処理を行う。

        Returns
        -------
        dict[str, str]
            メタタグ名とその内容の辞書
        """
        if self._metas is None:
            response = self.site.amc_request(
                [
                    {
                        "pageId": self.id,
                        "moduleName": "edit/EditMetaModule",
                    }
                ]
            )

            # レスポンス解析
            body = response[0].json()["body"]

            # <meta name="xxx" content="yyy"/> を正規表現で取得
            metas = {}
            for meta in re.findall(r'&lt;meta name="([^"]+)" content="([^"]+)"/&gt;', body):
                metas[meta[0]] = meta[1]

            self._metas = metas

        return self._metas

    @metas.setter
    def metas(self, value: dict[str, str]):
        """
        ページのメタタグ情報を設定する

        現在のメタタグと比較し、削除されたものは削除、追加されたものは追加する。

        Parameters
        ----------
        value : dict[str, str]
            設定するメタタグ名とその内容の辞書

        Raises
        ------
        LoginRequiredException
            ログインしていない場合
        WikidotStatusCodeException
            メタタグの設定に失敗した場合
        """
        self.site.client.login_check()
        current_metas = self.metas
        deleted_metas = {k: v for k, v in current_metas.items() if k not in value}
        added_metas = {k: v for k, v in value.items() if k not in current_metas}

        for name, content in deleted_metas.items():
            self.site.amc_request(
                [
                    {
                        "metaName": name,
                        "action": "WikiPageAction",
                        "event": "deleteMetaTag",
                        "pageId": self.id,
                        "moduleName": "edit/EditMetaModule",
                    }
                ]
            )

        for name, content in added_metas.items():
            self.site.amc_request(
                [
                    {
                        "metaName": name,
                        "metaContent": content,
                        "action": "WikiPageAction",
                        "event": "saveMetaTag",
                        "pageId": self.id,
                        "moduleName": "edit/EditMetaModule",
                    }
                ]
            )

        self._metas = value

    @staticmethod
    def create_or_edit(
        site: "Site",
        fullname: str,
        page_id: int | None = None,
        title: str = "",
        source: str = "",
        comment: str = "",
        force_edit: bool = False,
        raise_on_exists: bool = False,
    ) -> "Page":
        """
        ページを作成または編集する

        新規ページの作成または既存ページの編集を行う。
        編集の場合はページロックの取得とページ保存の処理を行う。

        Parameters
        ----------
        site : Site
            ページが属するサイト
        fullname : str
            ページのフルネーム
        page_id : int | None, default None
            編集する場合のページID（新規作成時はNone）
        title : str, default ""
            ページのタイトル
        source : str, default ""
            ページのソースコード（Wikidot記法）
        comment : str, default ""
            編集コメント
        force_edit : bool, default False
            他のユーザーによるロックを強制的に解除するかどうか
        raise_on_exists : bool, default False
            ページが既に存在する場合に例外を送出するかどうか

        Returns
        -------
        Page
            作成または編集されたページオブジェクト

        Raises
        ------
        LoginRequiredException
            ログインしていない場合
        TargetErrorException
            ページがロックされている場合
        TargetExistsException
            ページが既に存在し、raise_on_existsがTrueの場合
        ValueError
            既存ページの編集時にpage_idが指定されていない場合
        WikidotStatusCodeException
            ページの保存に失敗した場合
        NotFoundException
            ページの作成後に検索できない場合
        """
        site.client.login_check()

        # ページロックを取得しにいく
        page_lock_request_body = {
            "mode": "page",
            "wiki_page": fullname,
            "moduleName": "edit/PageEditModule",
        }
        if force_edit:
            page_lock_request_body["force_lock"] = "yes"

        page_lock_response = site.amc_request([page_lock_request_body])[0]
        page_lock_response_data = page_lock_response.json()

        if "locked" in page_lock_response_data or "other_locks" in page_lock_response_data:
            raise exceptions.TargetErrorException(
                f"Page {fullname} is locked or other locks exist",
            )

        # ページが存在するか（page_revision_idがあるか）確認
        is_exist = "page_revision_id" in page_lock_response_data

        if raise_on_exists and is_exist:
            raise exceptions.TargetExistsException(f"Page {fullname} already exists")

        if is_exist and page_id is None:
            raise ValueError("page_id must be specified when editing existing page")

        # lock_idとlock_secret、page_revision_id（あれば）を取得
        lock_id = page_lock_response_data["lock_id"]
        lock_secret = page_lock_response_data["lock_secret"]
        page_revision_id = page_lock_response_data.get("page_revision_id")

        # ページの作成または編集
        edit_request_body = {
            "action": "WikiPageAction",
            "event": "savePage",
            "moduleName": "Empty",
            "mode": "page",
            "lock_id": lock_id,
            "lock_secret": lock_secret,
            "revision_id": page_revision_id if page_revision_id is not None else "",
            "wiki_page": fullname,
            "page_id": page_id if page_id is not None else "",
            "title": title,
            "source": source,
            "comments": comment,
        }
        response = site.amc_request([edit_request_body])[0]

        if response.json()["status"] != "ok":
            raise exceptions.WikidotStatusCodeException(
                f"Failed to create or edit page: {fullname}", response.json()["status"]
            )

        res = PageCollection.search_pages(site, SearchPagesQuery(fullname=fullname))
        if len(res) == 0:
            raise exceptions.NotFoundException(f"Page creation failed: {fullname}")

        return res[0]

    def edit(
        self,
        title: Optional[str] = None,
        source: Optional[str] = None,
        comment: Optional[str] = None,
        force_edit: bool = False,
    ) -> "Page":
        """
        このページを編集する

        既存ページの内容を更新する。指定されていないパラメータは現在の値を維持する。

        Parameters
        ----------
        title : str | None, default None
            新しいタイトル（Noneの場合は現在のタイトルを維持）
        source : str | None, default None
            新しいソースコード（Noneの場合は現在のソースを維持）
        comment : str | None, default None
            編集コメント
        force_edit : bool, default False
            他のユーザーによるロックを強制的に解除するかどうか

        Returns
        -------
        Page
            編集後のページオブジェクト

        Raises
        ------
        同上（create_or_editメソッドと同様）
        """
        # Noneならそのままにする
        title = title or self.title
        source = source or self.source.wiki_text
        comment = comment or ""

        return Page.create_or_edit(
            self.site,
            self.fullname,
            self.id,
            title,
            source,
            comment,
            force_edit,
        )

    def commit_tags(self):
        """
        ページのタグ情報を保存する

        現在のtagsプロパティの内容をWikidotに保存する。

        Returns
        -------
        Page
            自身（メソッドチェーン用）

        Raises
        ------
        LoginRequiredException
            ログインしていない場合
        WikidotStatusCodeException
            タグの保存に失敗した場合
        """
        self.site.client.login_check()
        self.site.amc_request(
            [
                {
                    "tags": " ".join(self.tags),
                    "action": "WikiPageAction",
                    "event": "saveTags",
                    "pageId": self.id,
                    "moduleName": "Empty",
                }
            ]
        )
        return self
