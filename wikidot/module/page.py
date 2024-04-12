from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Union

from wikidot.common import exceptions

if TYPE_CHECKING:
    from wikidot.module.site import Site
    from wikidot.module.user import User

# TODO: Pageクラスに合わせて変更する
DEFAULT_MODULE_BODY = [
    "fullname",
    "category",
    "name",
    "title",
    "created_at",
    "created_by_linked",
    "updated_at",
    "updated_by_linked",
    "commented_at",
    "commented_by_linked",
    "parent_fullname",
    "comments",
    "size",
    "rating_votes",
    "rating",
    "revisions",
    "tags",
    "_tags"
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
    # pagination
    offset: Optional[int] = 0
    limit: Optional[int] = None
    perPage: Optional[int] = 250
    # layout
    separate: Optional[str] = "no"
    wrapper: Optional[str] = "no"

    # body

    def to_dict(self):
        query = {
            'pagetype': self.pagetype,
            'category': self.category,
            'tags': self.tags,
            'parent': self.parent,
            'link_to': self.link_to,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'created_by': self.created_by,
            'rating': self.rating,
            'votes': self.votes,
            'name': self.name,
            'fullname': self.fullname,
            'range': self.range,
            'offset': self.offset,
            'limit': self.limit,
            'perPage': self.perPage,
            'separate': self.separate,
            'wrapper': self.wrapper
        }

        return {k: v for k, v in query.items() if v is not None}


class PageCollection(list):
    @staticmethod
    def search_pages(
            site: 'Site',
            query: SearchPagesQuery = SearchPagesQuery()
    ):
        # 初回実行
        query_dict = query.to_dict()
        query_dict["moduleName"] = "list/ListPagesModule"
        query_dict["module_body"] = "<page>" + "".join(
            [f"<set><n> {key} </n><v> %%{key}%% </v></set>" for key in DEFAULT_MODULE_BODY]) + "</page>"

        try:
            response = site.amc_request([query_dict])[0]
        except exceptions.WikidotStatusCodeException as e:
            if e.status_code == "not_ok":
                raise exceptions.ForbiddenException("Failed to get pages, target site may be private") from e
            raise e

        print(response.json())


@dataclass
class Page:
    """ページオブジェクト

    Attributes
    ----------
    site: Site
        サイト
    id: int
        ページID
    fullname: str
        ページのフルネーム
    name: str
        ページ名
    category: str
        カテゴリ
    title: str
        タイトル
    parent_fullname: str
        親ページのフルネーム
    tags: list[str]
        タグのリスト（隠しタグを含む）
    children_count: int
        子ページ数
    comments_count: int
        コメント数
    size: int
        サイズ
    rating: float
        レーティング
    votes: int
        投票数
    revisions: int
        リビジョン数
    created_by: User
        作成者
    created_at: datetime
        作成日時
    updated_by: User
        更新者
    updated_at: datetime
        更新日時
    commented_by: Optional[User]
        コメントしたユーザ
    commented_at: datetime | None
        コメント日時
    """
    site: 'Site'
    id: int
    fullname: str
    name: str
    category: str
    title: str
    parent_fullname: str
    tags: list[str]
    children_count: int
    comments_count: int
    size: int
    rating: float
    votes: int
    revisions: int
    created_by: 'User'
    created_at: datetime
    updated_by: 'User'
    updated_at: datetime
    commented_by: Optional['User']
    commented_at: datetime | None
