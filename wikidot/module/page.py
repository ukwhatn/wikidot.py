import re
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Union, Any

from bs4 import BeautifulSoup

from wikidot.common import exceptions
from wikidot.util.parser import user as user_parser, odate as odate_parser

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
    created_by: Optional[Union['User', str]] = None
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
        if isinstance(res["tags"], list):
            res["tags"] = " ".join(res["tags"])
        return res


class PageCollection(list):
    @staticmethod
    def _parse(site: 'Site', html_body: BeautifulSoup):
        pages = PageCollection()

        for page_element in html_body.select("span.page"):
            page_params = {}

            # レーティング方式を判定
            is_5star_rating = page_element.select_one("span.rating span.page-rate-list-pages-start") is not None

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

                elif key in ["created_by_linked", "updated_by_linked", "commented_by_linked"]:
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
                elif key in ["comments", "children"]:
                    key = f"{key}_count"
                elif key in ["rating_votes"]:
                    key = "votes"

                page_params[key] = value

            # タグのリストを統合
            for key in ["tags", "_tags"]:
                if page_params[key] is None:
                    page_params[key] = []

            page_params["tags"] = page_params["tags"] + page_params["_tags"]
            del page_params["_tags"]

            # ページオブジェクトを作成
            pages.append(Page(site, **page_params))

        return pages

    @staticmethod
    def search_pages(
            site: 'Site',
            query: SearchPagesQuery = SearchPagesQuery()
    ):
        # 初回実行
        query_dict = query.as_dict()
        query_dict["moduleName"] = "list/ListPagesModule"
        query_dict["module_body"] = '[[span class="page"]]' + "".join(
            [
                f'[[span class="set {key}"]]'
                f'[[span class="name"]] {key} [[/span]]'
                f'[[span class="value"]] %%{key}%% [[/span]]'
                f'[[/span]]'
                for key in DEFAULT_MODULE_BODY
            ]
        ) + "[[/span]]"

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
            total = int(first_page_html_body.select("div.pager span.target")[-2].select_one("a").text)

        if total > 1:
            request_bodies = []
            for i in range(1, total):
                _query_dict = query_dict.copy()
                _query_dict["offset"] = i * query.perPage
                request_bodies.append(_query_dict)

            responses = site.amc_request(request_bodies)
            html_bodies.extend([BeautifulSoup(response.json()["body"], "lxml") for response in responses])

        pages = PageCollection()
        for html_body in html_bodies:
            pages.extend(PageCollection._parse(site, html_body))

        return pages

    @staticmethod
    def _acquire_page_ids(
            pages: list['Page']
    ):
        # pagesからidが設定されていないものを抽出
        target_pages = [page for page in pages if page.id is None]

        # なければ終了
        if len(target_pages) == 0:
            return pages

        # norender, noredirectでアクセス
        request_datas = [
            {
                "url": f"{page.get_url()}/norender/true/noredirect/true"
            } for page in target_pages
        ]
        responses = target_pages[0].site.client.amc_client.get(request_datas)

        # "WIKIREQUEST.info.pageId = xxx;"の値をidに設定
        for index, response in enumerate(responses):
            source = response.text

            id_match = re.search(r'WIKIREQUEST\.info\.pageId = (\d+);', source)
            if id_match is None:
                raise exceptions.UnexpectedException(f'Cannot find page id: {target_pages[index].fullname}')
            target_pages[index].id = int(id_match.group(1))

        return pages

    def get_page_ids(self):
        return PageCollection._acquire_page_ids(self)


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
    votes: int
        vote数
    rating_percent: float
        5つ星レーティングにおけるパーセンテージ
    revisions: int
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
    id: int
        ページID
    """
    site: 'Site'
    fullname: str
    name: str
    category: str
    title: str
    children_count: int
    comments_count: int
    size: int
    rating: int | float
    votes: int
    rating_percent: float
    revisions: int
    parent_fullname: str | None
    tags: list[str]
    created_by: 'User'
    created_at: datetime
    updated_by: 'User'
    updated_at: datetime
    commented_by: Optional['User']
    commented_at: datetime
    id: int = None

    def get_url(self) -> str:
        return f"{self.site.get_url()}/{self.fullname}"
