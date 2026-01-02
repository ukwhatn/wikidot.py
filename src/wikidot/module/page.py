import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

import httpx
from bs4 import BeautifulSoup

if sys.version_info >= (3, 12):
    from typing import TypedDict, Unpack
else:
    from typing_extensions import TypedDict, Unpack

from ..common import exceptions
from ..util.parser import odate as odate_parser
from ..util.parser import user as user_parser
from ..util.requestutil import RequestUtil
from .page_revision import PageRevision, PageRevisionCollection
from .page_source import PageSource
from .page_votes import PageVote, PageVoteCollection

if TYPE_CHECKING:
    from .forum_thread import ForumThread
    from .page_file import PageFileCollection
    from .site import Site
    from .user import User


class PageConstants:
    """
    A class for centrally managing constants used in the page module

    Attributes
    ----------
    DEFAULT_PER_PAGE : int
        Default number of items per page for ListPagesModule
    """

    DEFAULT_PER_PAGE: int = 250


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


class SearchPagesQueryParams(TypedDict, total=False):
    """
    A TypedDict defining page search query parameters

    Used for type definition of keyword arguments in SitePagesAccessor.search()
    and SearchPagesQuery.__init__(). Enables IDE autocomplete and type checking.

    Attributes
    ----------
    pagetype : str
        Page type (e.g., "normal", "admin", etc.). Default: "*"
    category : str
        Category name. Default: "*"
    tags : str | list[str]
        Tags to search for (string or list of strings)
    parent : str
        Parent page name
    link_to : str
        Linked page name
    created_at : str
        Creation date condition (e.g., "> -86400 86400")
    updated_at : str
        Update date condition
    created_by : User | str
        Filter by creator
    rating : str
        Filter by rating value
    votes : str
        Filter by vote count
    name : str
        Filter by page name
    fullname : str
        Filter by fullname (exact match)
    range : str
        Range specification
    order : str
        Sort order (e.g., "created_at desc", "title asc"). Default: "created_at desc"
    offset : int
        Starting position for retrieval. Default: 0
    limit : int
        Limit on number of items to retrieve
    perPage : int
        Number of items displayed per page. Default: 250
    separate : str
        Whether to display separately. Default: "no"
    wrapper : str
        Whether to display wrapper element. Default: "no"
    """

    pagetype: str
    category: str
    tags: "str | list[str]"
    parent: str
    link_to: str
    created_at: str
    updated_at: str
    created_by: "User | str"
    rating: str
    votes: str
    name: str
    fullname: str
    range: str
    order: str
    offset: int
    limit: int
    perPage: int
    separate: str
    wrapper: str


class SearchPagesQuery:
    """
    A class representing a page search query

    Defines various search conditions used for Wikidot page searches.
    Encapsulates query parameters to pass to ListPagesModule.

    Attributes
    ----------
    pagetype : str, default "*"
        Page type (e.g., "normal", "admin", etc.)
    category : str, default "*"
        Category name
    tags : str | list[str] | None, default None
        Tags to search for (string or list of strings)
    parent : str | None, default None
        Parent page name
    link_to : str | None, default None
        Linked page name
    created_at : str | None, default None
        Creation date condition
    updated_at : str | None, default None
        Update date condition
    created_by : User | str | None, default None
        Filter by creator
    rating : str | None, default None
        Filter by rating value
    votes : str | None, default None
        Filter by vote count
    name : str | None, default None
        Filter by page name
    fullname : str | None, default None
        Filter by fullname (exact match)
    range : str | None, default None
        Range specification
    order : str, default "created_at desc"
        Sort order (e.g., "created_at desc", "title asc", etc.)
    offset : int, default 0
        Starting position for retrieval
    limit : int | None, default None
        Limit on number of items to retrieve
    perPage : int, default 250
        Number of items displayed per page
    separate : str, default "no"
        Whether to display separately
    wrapper : str, default "no"
        Whether to display wrapper element

    Raises
    ------
    ValueError
        When invalid keyword arguments are passed
    """

    # 有効なフィールド名のセット
    _VALID_FIELDS = {
        "pagetype",
        "category",
        "tags",
        "parent",
        "link_to",
        "created_at",
        "updated_at",
        "created_by",
        "rating",
        "votes",
        "name",
        "fullname",
        "range",
        "order",
        "offset",
        "limit",
        "perPage",
        "separate",
        "wrapper",
    }

    def __init__(self, **kwargs: Unpack[SearchPagesQueryParams]) -> None:
        """
        Initialize SearchPagesQuery

        Parameters
        ----------
        **kwargs : Unpack[SearchPagesQueryParams]
            Search condition keyword arguments. See SearchPagesQueryParams for details.

        Raises
        ------
        ValueError
            When invalid keyword arguments are included
        """
        # 無効なキーのチェック
        invalid_keys = set(kwargs.keys()) - self._VALID_FIELDS
        if invalid_keys:
            raise ValueError(
                f"Invalid query parameters: {', '.join(sorted(invalid_keys))}. "
                f"Valid parameters are: {', '.join(sorted(self._VALID_FIELDS))}"
            )

        # デフォルト値の設定
        # selecting pages
        self.pagetype: str | None = kwargs.get("pagetype", "*")
        self.category: str | None = kwargs.get("category", "*")
        self.tags: str | list[str] | None = kwargs.get("tags")
        self.parent: str | None = kwargs.get("parent")
        self.link_to: str | None = kwargs.get("link_to")
        self.created_at: str | None = kwargs.get("created_at")
        self.updated_at: str | None = kwargs.get("updated_at")
        self.created_by: User | str | None = kwargs.get("created_by")
        self.rating: str | None = kwargs.get("rating")
        self.votes: str | None = kwargs.get("votes")
        self.name: str | None = kwargs.get("name")
        self.fullname: str | None = kwargs.get("fullname")
        self.range: str | None = kwargs.get("range")

        # ordering
        self.order: str = kwargs.get("order", "created_at desc")

        # pagination
        self.offset: int | None = kwargs.get("offset", 0)
        self.limit: int | None = kwargs.get("limit")
        self.perPage: int | None = kwargs.get("perPage", PageConstants.DEFAULT_PER_PAGE)
        # layout
        self.separate: str | None = kwargs.get("separate", "no")
        self.wrapper: str | None = kwargs.get("wrapper", "no")

    def as_dict(self) -> dict[str, Any]:
        """
        Convert query parameters to dictionary format

        If tags are in list format, converts them to a space-separated string.

        Returns
        -------
        dict[str, Any]
            Dictionary format parameters for API requests
        """
        res = {k: v for k, v in self.__dict__.items() if v is not None and k in self._VALID_FIELDS}

        if "tags" in res and isinstance(res["tags"], list):
            res["tags"] = " ".join(res["tags"])
        return res


class PageCollection(list["Page"]):
    """
    A class representing a collection of page objects

    Stores multiple page objects and provides functionality for batch operations.
    Consolidates features such as page search, batch retrieval, and batch operations.
    """

    site: "Site"

    def __init__(self, site: Optional["Site"] = None, pages: list["Page"] | None = None):
        """
        Initialize method

        Parameters
        ----------
        site : Site | None, default None
            Site to which pages belong. If None, inferred from the first page
        pages : list[Page] | None, default None
            List of pages to store
        """
        super().__init__(pages or [])

        if site is not None:
            self.site = site
        else:
            self.site = self[0].site

    def __iter__(self) -> Iterator["Page"]:
        """
        An iterator that returns pages in the collection sequentially

        Returns
        -------
        Iterator[Page]
            Iterator of page objects
        """
        return super().__iter__()

    def find(self, fullname: str) -> Optional["Page"]:
        """
        Get a page with the specified fullname

        Parameters
        ----------
        fullname : str
            Fullname of the page to retrieve

        Returns
        -------
        Page | None
            Page with the specified fullname. None if it does not exist
        """
        for page in self:
            if page.fullname == fullname:
                return page
        return None

    @staticmethod
    def _parse(site: "Site", html_body: BeautifulSoup) -> "PageCollection":
        """
        Parse ListPagesModule responses and generate a list of page objects

        Parameters
        ----------
        site : Site
            Site to which pages belong
        html_body : BeautifulSoup
            HTML to parse

        Returns
        -------
        PageCollection
            Page collection from parsing results

        Raises
        ------
        NoElementException
            When required elements are not found
        """
        pages = []

        for page_element in html_body.select("div.page"):
            page_params: dict[str, Any] = {}

            # レーティング方式を判定
            is_5star_rating = page_element.select_one("span.rating span.page-rate-list-pages-start") is not None

            # 各値を取得
            for set_element in page_element.select("span.set"):
                key_element = set_element.select_one("span.name")
                if key_element is None:
                    page_name = page_params.get("fullname", "unknown")
                    raise exceptions.NoElementException(f"Cannot find key element in set for page: {page_name}")
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
    def search_pages(site: "Site", query: SearchPagesQuery | None = None) -> "PageCollection":
        """
        Search for pages within a site

        Searches for pages within a site based on the specified query and returns the results.
        Executes the search using Wikidot's "ListPagesModule".

        Parameters
        ----------
        site : Site
            Site to search
        query : SearchPagesQuery | None, default None
            Search conditions. If None, default search conditions are used.

        Returns
        -------
        PageCollection
            Page collection of search results

        Raises
        ------
        ForbiddenException
            When access is denied on a private site
        WikidotStatusCodeException
            When other API errors occur
        NoElementException
            When page information cannot be extracted from the response
        """
        if query is None:
            query = SearchPagesQuery()
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
                _query_dict["offset"] = i * (query.perPage or PageConstants.DEFAULT_PER_PAGE)
                request_bodies.append(_query_dict)

            responses = site.amc_request(request_bodies)
            html_bodies.extend([BeautifulSoup(response.json()["body"], "lxml") for response in responses])

        pages: list[Page] = []
        for html_body in html_bodies:
            pages.extend(PageCollection._parse(site, html_body))

        return PageCollection(site, pages)

    @staticmethod
    def _acquire_page_ids(site: "Site", pages: list["Page"]) -> list["Page"]:
        """
        Internal method to retrieve page IDs

        Batch retrieves unacquired page IDs. Accesses pages with norender/noredirect options
        and extracts IDs from page source.

        Parameters
        ----------
        site : Site
            Site to which pages belong
        pages : list[Page]
            List of target pages

        Returns
        -------
        list[Page]
            List of pages with updated ID information

        Raises
        ------
        UnexpectedException
            When page ID is not found or response type is unexpected
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

    def get_page_ids(self) -> "PageCollection":
        """
        Get IDs for all pages in the collection

        Batch retrieves IDs for pages that do not have IDs set.

        Returns
        -------
        PageCollection
            Self (for method chaining)
        """
        PageCollection._acquire_page_ids(self.site, self)
        return self

    @staticmethod
    def _acquire_page_sources(site: "Site", pages: list["Page"]) -> list["Page"]:
        """
        Internal method to retrieve page sources

        Batch retrieves source code (Wikidot markup) for specified pages.

        Parameters
        ----------
        site : Site
            Site to which pages belong
        pages : list[Page]
            List of target pages

        Returns
        -------
        list[Page]
            List of pages with updated source information

        Raises
        ------
        NoElementException
            When source elements are not found
        """
        if len(pages) == 0:
            return pages

        responses = site.amc_request(
            [{"moduleName": "viewsource/ViewSourceModule", "page_id": page.id} for page in pages]
        )

        for page, response in zip(pages, responses, strict=True):
            body = response.json()["body"]
            # nbspをスペースに置換
            body = body.replace("&nbsp;", " ")
            html = BeautifulSoup(body, "lxml")
            source_element = html.select_one("div.page-source")
            if source_element is None:
                raise exceptions.NoElementException(
                    f"Cannot find source element for page: {page.fullname} (id={page.id})"
                )
            source = source_element.get_text().strip().removeprefix("\t")
            page.source = PageSource(page, source)
        return pages

    def get_page_sources(self) -> "PageCollection":
        """
        Get source code for all pages in the collection

        Batch retrieves source code (Wikidot markup) for pages and sets the source property for each page.

        Returns
        -------
        PageCollection
            Self (for method chaining)
        """
        PageCollection._acquire_page_sources(self.site, self)
        return self

    @staticmethod
    def _acquire_page_revisions(site: "Site", pages: list["Page"]) -> list["Page"]:
        """
        Internal method to retrieve page revision history

        Batch retrieves revisions (edit history) for specified pages.

        Parameters
        ----------
        site : Site
            Site to which pages belong
        pages : list[Page]
            List of target pages

        Returns
        -------
        list[Page]
            List of pages with updated revision information

        Raises
        ------
        NoElementException
            When required elements are not found
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

        for page, response in zip(pages, responses, strict=True):
            body = response.json()["body"]
            revs = []
            body_html = BeautifulSoup(body, "lxml")
            for rev_element in body_html.select("table.page-history > tr[id^=revision-row-]"):
                rev_id = int(str(rev_element["id"]).removeprefix("revision-row-"))

                tds = rev_element.select("td")
                rev_no = int(tds[0].text.strip().removesuffix("."))
                created_by_elem = tds[4].select_one("span.printuser")
                if created_by_elem is None:
                    raise exceptions.NoElementException(
                        f"Cannot find created by element for page: {page.fullname}, revision: {rev_id}"
                    )
                created_by = user_parser(page.site.client, created_by_elem)

                created_at_elem = tds[5].select_one("span.odate")
                if created_at_elem is None:
                    raise exceptions.NoElementException(
                        f"Cannot find created at element for page: {page.fullname}, revision: {rev_id}"
                    )
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

    def get_page_revisions(self) -> "PageCollection":
        """
        Get revision history for all pages in the collection

        Batch retrieves revisions (edit history) for pages and sets the revisions property for each page.

        Returns
        -------
        PageCollection
            Self (for method chaining)
        """
        PageCollection._acquire_page_revisions(self.site, self)
        return self

    @staticmethod
    def _acquire_page_votes(site: "Site", pages: list["Page"]) -> list["Page"]:
        """
        Internal method to retrieve vote information for pages

        Batch retrieves vote (rating) information for specified pages.

        Parameters
        ----------
        site : Site
            Site to which pages belong
        pages : list[Page]
            List of target pages

        Returns
        -------
        list[Page]
            List of pages with updated vote information

        Raises
        ------
        UnexpectedException
            When the number of user elements and vote value elements do not match
        """
        if len(pages) == 0:
            return pages

        responses = site.amc_request(
            [{"moduleName": "pagerate/WhoRatedPageModule", "pageId": page.id} for page in pages]
        )

        for page, response in zip(pages, responses, strict=True):
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

            votes = [PageVote(page, user, vote) for user, vote in zip(users, values, strict=True)]
            page._votes = PageVoteCollection(page, votes)

        return pages

    def get_page_votes(self) -> "PageCollection":
        """
        Get vote information for all pages in the collection

        Batch retrieves vote (rating) information for pages and sets the votes property for each page.

        Returns
        -------
        PageCollection
            Self (for method chaining)
        """
        PageCollection._acquire_page_votes(self.site, self)
        return self

    @staticmethod
    def _acquire_page_files(site: "Site", pages: list["Page"]) -> list["Page"]:
        """
        Internal method to retrieve file attachments for pages

        Batch retrieves file attachments for specified pages.

        Parameters
        ----------
        site : Site
            Site to which pages belong
        pages : list[Page]
            List of target pages

        Returns
        -------
        list[Page]
            List of pages with updated file information
        """
        if len(pages) == 0:
            return pages

        from .page_file import PageFileCollection

        responses = site.amc_request([{"moduleName": "files/PageFilesModule", "page_id": page.id} for page in pages])

        for page, response in zip(pages, responses, strict=True):
            body = response.json()["body"]
            html = BeautifulSoup(body, "lxml")
            files = PageFileCollection._parse_from_html(page, html)
            page._files = PageFileCollection(page=page, files=files)

        return pages

    def get_page_files(self) -> "PageCollection":
        """
        Get file attachments for all pages in the collection

        Batch retrieves file attachments for pages and sets the files property for each page.

        Returns
        -------
        PageCollection
            Self (for method chaining)
        """
        PageCollection._acquire_page_files(self.site, self)
        return self


@dataclass
class Page:
    """
    A class representing a Wikidot page

    Provides information and operation functions for a single page within a Wikidot site.
    Manages page basic information, metadata, history, ratings, etc.

    Attributes
    ----------
    site : Site
        Site where the page exists
    fullname : str
        Fullname of the page (e.g., "component:scp-173")
    name : str
        Page name (e.g., "scp-173")
    category : str
        Category (e.g., "component")
    title : str
        Title of the page
    children_count : int
        Number of child pages
    comments_count : int
        Number of comments
    size : int
        Size of the page (in bytes)
    rating : int | float
        Rating (int for +/- rating, float for 5-star rating)
    votes_count : int
        Number of votes
    rating_percent : float
        Percentage value in 5-star rating system (0.0 to 1.0)
    revisions_count : int
        Number of revisions (edit history)
    parent_fullname : str | None
        Fullname of parent page (None if no parent)
    tags : list[str]
        List of tags attached
    created_by : User
        Creator of the page
    created_at : datetime
        Date and time the page was created
    updated_by : User
        Last updater
    updated_at : datetime
        Last update date and time
    commented_by : User | None
        User who last commented (None if no comments)
    commented_at : datetime | None
        Date and time of last comment (None if no comments)
    _id : int | None
        Page ID (internal identifier)
    _source : PageSource | None
        Source code of the page (retrieved on request)
    _revisions : PageRevisionCollection | None
        Revision history of the page (retrieved on request)
    _votes : PageVoteCollection | None
        Vote information for the page (retrieved on request)
    _metas : dict[str, str] | None
        Meta tag information for the page (retrieved on request)
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
    commented_at: datetime | None
    _id: int | None = None
    _source: PageSource | None = None
    _revisions: PageRevisionCollection | None = None
    _votes: PageVoteCollection | None = None
    _metas: dict[str, str] | None = None
    _discussion: Optional["ForumThread"] = None
    _discussion_checked: bool = False
    _files: Optional["PageFileCollection"] = None

    def get_url(self) -> str:
        """
        Get the full URL of the page

        Generates the full page URL from the site URL and page name.

        Returns
        -------
        str
            Full URL of the page
        """
        return f"{self.site.url}/{self.fullname}"

    @property
    def id(self) -> int:
        """
        Get the page ID

        Automatically performs retrieval processing if the ID has not been acquired.

        Returns
        -------
        int
            Page ID

        Raises
        ------
        NotFoundException
            When the page ID is not found
        """
        if not self.is_id_acquired():
            PageCollection(self.site, [self]).get_page_ids()

        if self._id is None:
            raise exceptions.NotFoundException("Cannot find page id")

        return self._id

    @id.setter
    def id(self, value: int) -> None:
        """
        Set the page ID

        Parameters
        ----------
        value : int
            Page ID to set
        """
        self._id = value

    def is_id_acquired(self) -> bool:
        """
        Check whether the page ID has already been acquired

        Returns
        -------
        bool
            True if the ID has been acquired, False if not acquired
        """
        return self._id is not None

    @property
    def source(self) -> PageSource:
        """
        Get the source code of the page

        Automatically performs retrieval processing if the source code has not been acquired.

        Returns
        -------
        PageSource
            Source code object of the page

        Raises
        ------
        NotFoundException
            When the page source is not found
        """
        if self._source is None:
            PageCollection(self.site, [self]).get_page_sources()

        if self._source is None:
            raise exceptions.NotFoundException("Cannot find page source")

        return self._source

    @source.setter
    def source(self, value: PageSource) -> None:
        """
        Set the source code of the page

        Parameters
        ----------
        value : PageSource
            Source code object to set
        """
        self._source = value

    @property
    def revisions(self) -> PageRevisionCollection:
        """
        Get the revision history of the page

        Automatically performs retrieval processing if the revision history has not been acquired.

        Returns
        -------
        PageRevisionCollection
            Revision history collection of the page

        Raises
        ------
        NotFoundException
            When the revision history is not found
        """
        if self._revisions is None:
            PageCollection(self.site, [self]).get_page_revisions()
        return PageRevisionCollection(self, self._revisions)

    @revisions.setter
    def revisions(self, value: list["PageRevision"] | PageRevisionCollection) -> None:
        """
        Set the revision history of the page

        Parameters
        ----------
        value : list[PageRevision] | PageRevisionCollection
            List or collection of revisions to set
        """
        if isinstance(value, list):
            self._revisions = PageRevisionCollection(self, value)
        else:
            self._revisions = value

    @property
    def latest_revision(self) -> PageRevision:
        """
        Get the latest revision of the page

        Returns the revision where revision_count and rev_no match as the latest.

        Returns
        -------
        PageRevision
            Latest revision object

        Raises
        ------
        NotFoundException
            When the latest revision is not found
        """
        # revision_countとrev_noが一致するものを取得
        for revision in self.revisions:
            if revision.rev_no == self.revisions_count:
                return revision

        raise exceptions.NotFoundException("Cannot find latest revision")

    @property
    def votes(self) -> PageVoteCollection:
        """
        Get vote information for the page

        Automatically performs retrieval processing if the vote information has not been acquired.

        Returns
        -------
        PageVoteCollection
            Vote information collection for the page

        Raises
        ------
        NotFoundException
            When the vote information is not found
        """
        if self._votes is None:
            PageCollection(self.site, [self]).get_page_votes()

        if self._votes is None:
            raise exceptions.NotFoundException("Cannot find page votes")

        return self._votes

    @votes.setter
    def votes(self, value: PageVoteCollection) -> None:
        """
        Set vote information for the page

        Parameters
        ----------
        value : PageVoteCollection
            Vote information collection to set
        """
        self._votes = value

    @property
    def discussion(self) -> Optional["ForumThread"]:
        """
        Get the discussion thread for the page

        Retrieves the forum thread (comments section) associated with the page.
        Returns None if the discussion does not exist.

        Returns
        -------
        ForumThread | None
            Discussion thread. None if it does not exist
        """
        if not self._discussion_checked:
            response = self.site.amc_request(
                [
                    {
                        "moduleName": "forum/ForumCommentsListModule",
                        "pageId": self.id,
                    }
                ]
            )[0]

            body = response.json()["body"]
            match = re.search(r"WIKIDOT\.forumThreadId = (\d+);", body)
            if match is not None:
                from .forum_thread import ForumThread

                thread_id = int(match.group(1))
                self._discussion = ForumThread.get_from_id(self.site, thread_id)
            self._discussion_checked = True

        return self._discussion

    @property
    def files(self) -> "PageFileCollection":
        """
        Get a list of files attached to the page

        Automatically performs retrieval processing if the file list has not been acquired.

        Returns
        -------
        PageFileCollection
            Collection of files attached to the page
        """
        if self._files is None:
            PageCollection(self.site, [self]).get_page_files()

        # _files should be set by get_page_files(), but provide a fallback
        if self._files is None:
            from .page_file import PageFileCollection

            self._files = PageFileCollection(page=self, files=[])
        return self._files

    def destroy(self) -> None:
        """
        Delete the page

        Can only be executed while logged in. Performs complete deletion of the page.

        Raises
        ------
        LoginRequiredException
            When not logged in
        WikidotStatusCodeException
            When deletion fails
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
        Get meta tag information for the page

        Automatically performs retrieval processing if the meta tag information has not been acquired.

        Returns
        -------
        dict[str, str]
            Dictionary of meta tag names and their contents
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
    def metas(self, value: dict[str, str]) -> None:
        """
        Set meta tag information for the page

        Compares with current meta tags, deletes removed ones, and saves added/updated ones.

        Parameters
        ----------
        value : dict[str, str]
            Dictionary of meta tag names and their contents to set

        Raises
        ------
        LoginRequiredException
            When not logged in
        WikidotStatusCodeException
            When setting meta tags fails
        """
        self.site.client.login_check()
        current_metas = self.metas
        deleted_metas = {k: v for k, v in current_metas.items() if k not in value}
        added_metas = {k: v for k, v in value.items() if k not in current_metas}
        updated_metas = {k: v for k, v in value.items() if k in current_metas and current_metas[k] != v}

        for name, _content in deleted_metas.items():
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

        for name, content in updated_metas.items():
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
        Create or edit a page

        Creates a new page or edits an existing page.
        For editing, acquires page lock and performs page save processing.

        Parameters
        ----------
        site : Site
            Site to which the page belongs
        fullname : str
            Fullname of the page
        page_id : int | None, default None
            Page ID when editing (None when creating new)
        title : str, default ""
            Title of the page
        source : str, default ""
            Source code of the page (Wikidot markup)
        comment : str, default ""
            Edit comment
        force_edit : bool, default False
            Whether to forcibly release locks by other users
        raise_on_exists : bool, default False
            Whether to raise an exception if the page already exists

        Returns
        -------
        Page
            Created or edited page object

        Raises
        ------
        LoginRequiredException
            When not logged in
        TargetErrorException
            When the page is locked
        TargetExistsException
            When the page already exists and raise_on_exists is True
        ValueError
            When page_id is not specified when editing an existing page
        WikidotStatusCodeException
            When saving the page fails
        NotFoundException
            When the page cannot be found after creation
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

        if page_lock_response_data.get("locked") or page_lock_response_data.get("other_locks"):
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
        title: str | None = None,
        source: str | None = None,
        comment: str | None = None,
        force_edit: bool = False,
    ) -> "Page":
        """
        Edit this page

        Updates the contents of an existing page. Parameters not specified maintain their current values.

        Parameters
        ----------
        title : str | None, default None
            New title (maintains current title if None)
        source : str | None, default None
            New source code (maintains current source if None)
        comment : str | None, default None
            Edit comment
        force_edit : bool, default False
            Whether to forcibly release locks by other users

        Returns
        -------
        Page
            Edited page object

        Raises
        ------
        Same as above (same as create_or_edit method)
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

    def commit_tags(self) -> "Page":
        """
        Save tag information for the page

        Saves the contents of the current tags property to Wikidot.

        Returns
        -------
        Page
            Self (for method chaining)

        Raises
        ------
        LoginRequiredException
            When not logged in
        WikidotStatusCodeException
            When saving tags fails
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

    def set_parent(self, parent_fullname: str | None) -> "Page":
        """
        Set the parent page

        Sets the specified parent page as the parent of this page.
        Specifying None or an empty string removes the parent page setting.

        Parameters
        ----------
        parent_fullname : str | None
            Fullname of the parent page. None or empty string removes the parent

        Returns
        -------
        Page
            Self (for method chaining)

        Raises
        ------
        LoginRequiredException
            When not logged in
        WikidotStatusCodeException
            When setting the parent page fails
        """
        self.site.client.login_check()
        self.site.amc_request(
            [
                {
                    "action": "WikiPageAction",
                    "event": "setParentPage",
                    "moduleName": "Empty",
                    "pageId": str(self.id),
                    "parentName": parent_fullname or "",
                }
            ]
        )
        self.parent_fullname = parent_fullname
        return self

    def rename(self, new_fullname: str) -> "Page":
        """
        Rename the page

        Changes the page's fullname to a new name.
        Must specify the complete fullname including category.

        Parameters
        ----------
        new_fullname : str
            New fullname (e.g., "component:new-name")

        Returns
        -------
        Page
            Self (for method chaining)

        Raises
        ------
        LoginRequiredException
            When not logged in
        WikidotStatusCodeException
            When renaming the page fails (e.g., when a page with the same name exists)
        """
        self.site.client.login_check()
        self.site.amc_request(
            [
                {
                    "action": "WikiPageAction",
                    "event": "renamePage",
                    "moduleName": "Empty",
                    "page_id": self.id,
                    "new_name": new_fullname,
                }
            ]
        )
        self.fullname = new_fullname
        if ":" in new_fullname:
            self.category, self.name = new_fullname.split(":", 1)
        else:
            self.category = "_default"
            self.name = new_fullname
        return self

    def vote(self, value: int) -> int:
        """
        Vote on the page

        Casts a +1 or -1 vote on the page.
        Overwrites if already voted.

        Parameters
        ----------
        value : int
            Vote value (1 or -1)

        Returns
        -------
        int
            New rating value after voting

        Raises
        ------
        LoginRequiredException
            When not logged in
        WikidotStatusCodeException
            When voting fails
        """
        self.site.client.login_check()
        response = self.site.amc_request(
            [
                {
                    "action": "RateAction",
                    "event": "ratePage",
                    "moduleName": "Empty",
                    "pageId": self.id,
                    "points": value,
                    "force": "yes",
                }
            ]
        )[0]
        new_rating = int(response.json()["points"])
        self.rating = new_rating
        return new_rating

    def cancel_vote(self) -> int:
        """
        Cancel the vote

        Cancels your vote on this page.

        Returns
        -------
        int
            New rating value after cancellation

        Raises
        ------
        LoginRequiredException
            When not logged in
        WikidotStatusCodeException
            When vote cancellation fails
        """
        self.site.client.login_check()
        response = self.site.amc_request(
            [
                {
                    "action": "RateAction",
                    "event": "cancelVote",
                    "moduleName": "Empty",
                    "pageId": self.id,
                }
            ]
        )[0]
        new_rating = int(response.json()["points"])
        self.rating = new_rating
        return new_rating
