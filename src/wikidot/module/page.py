import re
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional, Union

from bs4 import BeautifulSoup

from wikidot.common import exceptions
from wikidot.module.forum_thread import ForumThread
from wikidot.module.page_revision import PageRevision, PageRevisionCollection
from wikidot.module.page_source import PageSource
from wikidot.module.page_votes import PageVote, PageVoteCollection
from wikidot.util.parser import odate as odate_parser
from wikidot.util.parser import user as user_parser
from wikidot.util.requestutil import RequestUtil

if TYPE_CHECKING:
    from wikidot.module.site import Site
    from wikidot.module.user import User

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
        res = {k: v for k, v in asdict(self).items() if v is not None}
        if "tags" in res and isinstance(res["tags"], list):
            res["tags"] = " ".join(res["tags"])
        return res


class PageCollection(list["Page"]):
    def __init__(self, site: "Site" = None, pages: list["Page"] = None):
        super().__init__(pages or [])

        if site is not None:
            self.site = site
        else:
            self.site = self[0].site

    def __iter__(self) -> Iterator["Page"]:
        return super().__iter__()

    @staticmethod
    def _parse(site: "Site", html_body: BeautifulSoup):
        pages = []

        for page_element in html_body.select("div.page"):
            page_params = {}

            # レーティング方式を判定
            is_5star_rating = (
                page_element.select_one("span.rating span.page-rate-list-pages-start")
                is not None
            )

            # 各値を取得
            for set_element in page_element.select("span.set"):
                key = set_element.select_one("span.name").text.strip()
                value_element = set_element.select_one("span.value")

                if value_element is None:
                    value = None

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
                raise exceptions.ForbiddenException(
                    "Failed to get pages, target site may be private"
                ) from e
            raise e

        body = response.json()["body"]

        first_page_html_body = BeautifulSoup(body, "lxml")

        total = 1
        html_bodies = [first_page_html_body]
        # pagerが存在する
        if first_page_html_body.select_one("div.pager") is not None:
            # span.target[-2] > a から最大ページ数を取得
            total = int(
                first_page_html_body.select("div.pager span.target")[-2]
                .select_one("a")
                .text
            )

        if total > 1:
            request_bodies = []
            for i in range(1, total):
                _query_dict = query_dict.copy()
                _query_dict["offset"] = i * query.perPage
                request_bodies.append(_query_dict)

            responses = site.amc_request(request_bodies)
            html_bodies.extend(
                [
                    BeautifulSoup(response.json()["body"], "lxml")
                    for response in responses
                ]
            )

        pages = []
        for html_body in html_bodies:
            pages.extend(PageCollection._parse(site, html_body))

        return PageCollection(site, pages)

    @staticmethod
    def _acquire_page_ids(site: "Site", pages: list["Page"]):
        # pagesからidが設定されていないものを抽出
        target_pages = [page for page in pages if not page.is_id_acquired()]

        # なければ終了
        if len(target_pages) == 0:
            return pages

        # norender, noredirectでアクセス
        responses = RequestUtil.request(
            site.client,
            "GET",
            [
                f"{page.get_url()}/norender/true/noredirect/true"
                for page in target_pages
            ],
        )

        # "WIKIREQUEST.info.pageId = xxx;"の値をidに設定
        for index, response in enumerate(responses):
            source = response.text

            id_match = re.search(r"WIKIREQUEST\.info\.pageId = (\d+);", source)
            if id_match is None:
                raise exceptions.UnexpectedException(
                    f"Cannot find page id: {target_pages[index].fullname}"
                )
            target_pages[index].id = int(id_match.group(1))

        return pages

    def get_page_ids(self):
        return PageCollection._acquire_page_ids(self.site, self)

    @staticmethod
    def _acquire_page_sources(site: "Site", pages: list["Page"]):
        if len(pages) == 0:
            return pages

        responses = site.amc_request(
            [
                {"moduleName": "viewsource/ViewSourceModule", "page_id": page.id}
                for page in pages
            ]
        )

        for page, responses in zip(pages, responses):
            body = responses.json()["body"]
            source = (
                BeautifulSoup(body, "lxml")
                .select_one("div.page-source")
                .text.strip()
                .removeprefix("\t")
            )
            page.source = PageSource(page, source)
        return pages

    def get_page_sources(self):
        return PageCollection._acquire_page_sources(self.site, self)

    @staticmethod
    def _acquire_page_revisions(site: "Site", pages: list["Page"]):
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
            for rev_element in body_html.select(
                "table.page-history > tr[id^=revision-row-]"
            ):
                rev_id = int(rev_element["id"].removeprefix("revision-row-"))

                tds = rev_element.select("td")
                rev_no = int(tds[0].text.strip().removesuffix("."))
                created_by = user_parser(
                    page.site.client, tds[4].select_one("span.printuser")
                )
                created_at = odate_parser(tds[5].select_one("span.odate"))
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
            page.revisions = revs

        return pages

    def get_page_revisions(self):
        return PageCollection._acquire_page_revisions(self.site, self)

    @staticmethod
    def _acquire_page_votes(site: "Site", pages: list["Page"]):
        if len(pages) == 0:
            return pages

        responses = site.amc_request(
            [
                {"moduleName": "pagerate/WhoRatedPageModule", "pageId": page.id}
                for page in pages
            ]
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
                value = value.text.strip()
                if value == "+":
                    values.append(1)
                elif value == "-":
                    values.append(-1)
                else:
                    values.append(int(value))

            votes = [PageVote(page, user, vote) for user, vote in zip(users, values)]
            page._votes = PageVoteCollection(page.site, votes)

        return pages

    def get_page_votes(self):
        return PageCollection._acquire_page_votes(self.site, self)

    def _acquire_page_discuss(site: "Site", pages: list["Page"]):
        target_pages = [page for page in pages if not page.is_discuss_acquired()]

        if len(target_pages) == 0:
            return pages

        responses = site.amc_request(
            [
                {
                    "action": "ForumAction",
                    "event": "createPageDiscussionThread",
                    "page_id": page.id,
                    "moduleName": "Empty",
                }
                for page in target_pages
            ]
        )

        for page, response in zip(pages, responses):
            page._discuss = ForumThread(site, response.json()["thread_id"], page=page)

    def get_page_discuss(self):
        return PageCollection._acquire_page_discuss(self.site, self)


@dataclass
class Page:
    """ページオブジェクト

    Attributes
    ----------
    site: Site
        ページが存在するサイト
    fullname: str
        ページのフルネーム
    name: str
        ページ名
    category: str
        カテゴリ
    title: str
        タイトル
    children_count: int
        子ページ数
    comments_count: int
        コメント数
    size: int
        サイズ
    rating: int | float
        レーティング +/-ならint、5つ星ならfloat
    votes_count: int
        vote数
    rating_percent: float
        5つ星レーティングにおけるパーセンテージ
    revisions_count: int
        リビジョン数
    parent_fullname: str | None
        親ページのフルネーム 存在しない場合はNone
    tags: list[str]
        タグのリスト
    created_by: User
        作成者
    created_at: datetime
        作成日時
    updated_by: Optional[User]
        更新者
    updated_at: datetime | None
        更新日時
    commented_by: Optional[User]
        コメントしたユーザ
    commented_at: datetime
        コメント日時
    _id: int
        ページID
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
    commented_at: datetime
    _id: int = None
    _source: Optional[PageSource] = None
    _revisions: list["PageRevision"] = None
    _votes: PageVoteCollection = None
    _discuss: ForumThread = None

    @property
    def discuss(self):
        if self._discuss is None:
            PageCollection(self.site, [self]).get_page_discuss()
        self._discuss.update()
        return self._discuss

    @discuss.setter
    def discuss(self, value: ForumThread):
        self._discuss = value

    def is_discuss_acquired(self) -> bool:
        return self._discuss is not None

    def get_url(self) -> str:
        return f"{self.site.get_url()}/{self.fullname}"

    @property
    def id(self) -> int:
        """ページID（必要であれば取得）

        Returns
        -------
        int
            ページID
        """
        if self._id is None:
            PageCollection(self.site, [self]).get_page_ids()
        return self._id

    @id.setter
    def id(self, value: int):
        self._id = value

    def is_id_acquired(self) -> bool:
        return self._id is not None

    @property
    def source(self) -> PageSource:
        if self._source is None:
            PageCollection(self.site, [self]).get_page_sources()
        return self._source

    @source.setter
    def source(self, value: PageSource):
        self._source = value

    @property
    def revisions(self) -> PageRevisionCollection["PageRevision"]:
        if self._revisions is None:
            PageCollection(self.site, [self]).get_page_revisions()
        return PageRevisionCollection(self, self._revisions)

    @revisions.setter
    def revisions(
        self, value: list["PageRevision"] | PageRevisionCollection["PageRevision"]
    ):
        self._revisions = value

    @property
    def latest_revision(self) -> PageRevision:
        # revision_countとrev_noが一致するものを取得
        for revision in self.revisions:
            if revision.rev_no == self.revisions_count:
                return revision

        raise exceptions.NotFoundException("Cannot find latest revision")

    @property
    def votes(self) -> PageVoteCollection:
        if self._votes is None:
            PageCollection(self.site, [self]).get_page_votes()
        return self._votes

    @votes.setter
    def votes(self, value: PageVoteCollection):
        self._votes = value

    def destroy(self):
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

    def get_metas(self) -> dict[str, str]:
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

        return metas

    def set_meta(self, name: str, value: str):
        self.site.client.login_check()
        self.site.amc_request(
            [
                {
                    "metaName": name,
                    "metaContent": value,
                    "action": "WikiPageAction",
                    "event": "saveMetaTag",
                    "pageId": self.id,
                    "moduleName": "edit/EditMetaModule",
                }
            ]
        )

    def delete_meta(self, name: str):
        self.site.client.login_check()
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
    ):
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

        if (
            "locked" in page_lock_response_data
            or "other_locks" in page_lock_response_data
        ):
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

        return response.json()

    def edit(
        self,
        title: str = None,
        source: str = None,
        comment: str = None,
        force_edit: bool = False,
    ):
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

    def set_tags(self, tags: list[str]):
        # TODO: setter/getterにする
        self.site.client.login_check()
        self.site.amc_request(
            [
                {
                    "tags": " ".join(tags),
                    "action": "WikiPageAction",
                    "event": "saveTags",
                    "pageId": self.id,
                    "moduleName": "Empty",
                }
            ]
        )
