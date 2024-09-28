import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

import httpx

from wikidot.common import exceptions
from wikidot.common.decorators import login_required
from wikidot.module.forum import Forum
from wikidot.module.page import Page, PageCollection, SearchPagesQuery
from wikidot.module.site_application import SiteApplication

if TYPE_CHECKING:
    from wikidot.module.client import Client
    from wikidot.module.user import User


class SitePagesMethods:
    def __init__(self, site: "Site"):
        self.site = site

    def search(self, **kwargs) -> "PageCollection":
        """ページを検索する

        Parameters
        ----------
        site: Site
            サイト
        query: SearchPagesQuery
            検索クエリ

        Returns
        -------
        PageCollection
            ページのコレクション
        """

        query = SearchPagesQuery(**kwargs)
        return PageCollection.search_pages(self.site, query)


class SitePageMethods:
    def __init__(self, site: "Site"):
        self.site = site

    def get(self, fullname: str, raise_when_not_found: bool = True) -> Optional["Page"]:
        """フルネームからページを取得する

        Parameters
        ----------
        fullname: str
            ページのフルネーム
        raise_when_not_found: bool
            ページが見つからなかった場合に例外を発生させるかどうか させない場合はNoneを返す

        Returns
        -------
        Page
            ページオブジェクト
        """
        res = PageCollection.search_pages(
            self.site, SearchPagesQuery(fullname=fullname)
        )
        if len(res) == 0:
            if raise_when_not_found:
                raise exceptions.NotFoundException(f"Page is not found: {fullname}")
            return None
        return res[0]

    def create(
        self,
        fullname: str,
        title: str = "",
        source: str = "",
        comment: str = "",
        force_edit: bool = False,
    ) -> None:
        """ページを作成する

        Parameters
        ----------
        fullname: str
            ページのフルネーム
        title: str
            ページのタイトル
        source: str
            ページのソース
        comment: str
            コメント
        force_edit: bool
            ページが存在する場合に上書きするかどうか
        """
        return Page.create_or_edit(
            site=self.site,
            fullname=fullname,
            title=title,
            source=source,
            comment=comment,
            force_edit=force_edit,
            raise_on_exists=True,
        )


@dataclass
class Site:
    """サイトオブジェクト

    Attributes
    ----------
    id: int
        サイトID
    title: str
        サイトのタイトル
    unix_name: str
        サイトのUNIX名
    domain: str
        サイトのドメイン
    ssl_supported: bool
        SSL対応しているかどうか

    Raises
    ------
    NotFoundException
        サイトが存在しない場合
    UnexpectedException
        予期しないエラーが発生した場合
    """

    client: "Client"

    id: int
    title: str
    unix_name: str
    domain: str
    ssl_supported: bool

    def __post_init__(self):
        self.pages = SitePagesMethods(self)
        self.page = SitePageMethods(self)
        self.forum = Forum(self)

    def __str__(self):
        return f"Site(id={self.id}, title={self.title}, unix_name={self.unix_name})"

    @staticmethod
    def from_unix_name(client: "Client", unix_name: str) -> "Site":
        """UNIX名からサイトオブジェクトを取得する

        Parameters
        ----------
        client: Client
            クライアント
        unix_name: str
            サイトのUNIX名

        Returns
        -------
        Site
            サイトオブジェクト
        """
        # サイト情報を取得
        # リダイレクトには従う
        response = httpx.get(
            f"http://{unix_name}.wikidot.com",
            follow_redirects=True,
            timeout=client.amc_client.config.request_timeout,
        )

        # サイトが存在しない場合
        if response.status_code == httpx.codes.NOT_FOUND:
            raise exceptions.NotFoundException(
                f"Site is not found: {unix_name}.wikidot.com"
            )

        # サイトが存在する場合
        source = response.text

        # id : WIKIREQUEST.info.siteId = xxxx;
        id_match = re.search(r"WIKIREQUEST\.info\.siteId = (\d+);", source)
        if id_match is None:
            raise exceptions.UnexpectedException(
                f"Cannot find site id: {unix_name}.wikidot.com"
            )
        site_id = int(id_match.group(1))

        # title : titleタグ
        title_match = re.search(r"<title>(.*?)</title>", source)
        if title_match is None:
            raise exceptions.UnexpectedException(
                f"Cannot find site title: {unix_name}.wikidot.com"
            )
        title = title_match.group(1)

        # unix_name : WIKIREQUEST.info.siteUnixName = "xxxx";
        unix_name_match = re.search(
            r'WIKIREQUEST\.info\.siteUnixName = "(.*?)";', source
        )
        if unix_name_match is None:
            raise exceptions.UnexpectedException(
                f"Cannot find site unix_name: {unix_name}.wikidot.com"
            )
        unix_name = unix_name_match.group(1)

        # domain :WIKIREQUEST.info.domain = "xxxx";
        domain_match = re.search(r'WIKIREQUEST\.info\.domain = "(.*?)";', source)
        if domain_match is None:
            raise exceptions.UnexpectedException(
                f"Cannot find site domain: {unix_name}.wikidot.com"
            )
        domain = domain_match.group(1)

        # SSL対応チェック
        ssl_supported = str(response.url).startswith("https")

        return Site(
            client=client,
            id=site_id,
            title=title,
            unix_name=unix_name,
            domain=domain,
            ssl_supported=ssl_supported,
        )

    def amc_request(self, bodies: list[dict], return_exceptions: bool = False):
        """このサイトに対してAMCリクエストを実行する"""
        return self.client.amc_client.request(
            bodies, return_exceptions, self.unix_name, self.ssl_supported
        )

    def get_applications(self):
        """サイトへの未処理の参加申請を取得する"""
        return SiteApplication.acquire_all(self)

    @login_required
    def invite_user(self, user: "User", text: str):
        """ユーザーをサイトに招待する"""
        try:
            self.amc_request(
                [
                    {
                        "action": "ManageSiteMembershipAction",
                        "event": "inviteMember",
                        "user_id": user.id,
                        "text": text,
                        "moduleName": "Empty",
                    }
                ]
            )
        except exceptions.WikidotStatusCodeException as e:
            if e.status_code == "already_invited":
                raise exceptions.TargetErrorException(
                    f"User is already invited to {self.unix_name}: {user.name}"
                ) from e
            elif e.status_code == "already_member":
                raise exceptions.TargetErrorException(
                    f"User is already a member of {self.unix_name}: {user.name}"
                ) from e
            else:
                raise e

    def get_url(self):
        """サイトのURLを取得する"""
        return f'http{"s" if self.ssl_supported else ""}://{self.domain}'
