import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

import httpx

from ..common import exceptions
from ..common.decorators import login_required
from ..util.quick_module import QMCUser, QuickModule
from .forum_category import ForumCategoryCollection
from .forum_thread import ForumThread, ForumThreadCollection
from .page import Page, PageCollection, SearchPagesQuery
from .site_application import SiteApplication
from .site_member import SiteMember

if TYPE_CHECKING:
    from .client import Client
    from .user import User


class SitePagesMethods:
    """
    サイト内のページコレクションに対する操作を提供するクラス

    ページの検索機能など、複数のページに対する操作を提供する。
    Site.pagesプロパティを通じてアクセスする。
    """

    def __init__(self, site: "Site"):
        """
        初期化メソッド

        Parameters
        ----------
        site : Site
            親サイトインスタンス
        """
        self.site = site

    def search(self, **kwargs) -> "PageCollection":
        """
        サイト内のページを検索する

        キーワード引数を受け取り、SearchPagesQueryオブジェクトに変換して検索を実行する。

        Parameters
        ----------
        **kwargs
            SearchPagesQueryに渡す検索条件。以下のパラメータが利用可能:

            ページ選択パラメータ:
            - pagetype: str - ページタイプ（例: "normal", "admin"等）
            - category: str - カテゴリ名
            - tags: list[str] | str - タグリスト（リストまたは空白区切り文字列）
            - parent: str - 親ページ名
            - link_to: str - リンク先ページ名
            - created_at: str - 作成日時の条件（例: "> -86400 86400"）
            - updated_at: str - 更新日時の条件
            - created_by: User | str - 作成者（ユーザーオブジェクトまたはユーザー名）
            - rating: str - 評価値による絞り込み
            - votes: str - 投票数による絞り込み
            - name: str - ページ名による絞り込み
            - fullname: str - フルネームによる絞り込み（完全一致）
            - range: str - 範囲指定

            ソートパラメータ:
            - order: str - ソート順（例: "created_at desc", "title asc"）

            ページネーションパラメータ:
            - offset: int - 取得開始位置
            - limit: int - 取得件数制限
            - perPage: int - 1ページあたりの表示件数

            レイアウトパラメータ:
            - separate: str - 個別表示するかどうか
            - wrapper: str - ラッパー要素を表示するかどうか

        Returns
        -------
        PageCollection
            検索結果のページコレクション
        """
        query = SearchPagesQuery(**kwargs)
        return PageCollection.search_pages(self.site, query)


class SitePageMethods:
    """
    サイト内の個別ページに対する操作を提供するクラス

    ページの取得や作成などの個別ページ操作を提供する。
    Site.pageプロパティを通じてアクセスする。
    """

    def __init__(self, site: "Site"):
        """
        初期化メソッド

        Parameters
        ----------
        site : Site
            親サイトインスタンス
        """
        self.site = site

    def get(self, fullname: str, raise_when_not_found: bool = True) -> Optional["Page"]:
        """
        フルネームからページを取得する

        Parameters
        ----------
        fullname : str
            ページのフルネーム（例: "コンポーネント:scp-173"）
        raise_when_not_found : bool, default True
            ページが見つからなかった場合に例外を発生させるかどうか
            Falseの場合、ページが見つからなければNoneを返す

        Returns
        -------
        Page | None
            ページオブジェクト、または見つからない場合はNone

        Raises
        ------
        NotFoundException
            raise_when_not_foundがTrueでページが見つからない場合
        """
        res = PageCollection.search_pages(self.site, SearchPagesQuery(fullname=fullname))
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
    ) -> "Page":
        """
        ページを新規作成する

        Parameters
        ----------
        fullname : str
            ページのフルネーム（例: "scp-173"）
        title : str, default ""
            ページのタイトル
        source : str, default ""
            ページのソースコード（Wikidot記法）
        comment : str, default ""
            編集コメント
        force_edit : bool, default False
            ページが既に存在する場合に上書きするかどうか

        Returns
        -------
        Page
            作成されたページオブジェクト

        Raises
        ------
        TargetErrorException
            ページが既に存在し、force_editがFalseの場合
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


class SiteForumMethods:
    """
    サイト内のフォーラム機能に対する操作を提供するクラス

    フォーラムカテゴリの取得などのフォーラム関連機能を提供する。
    Site.forumプロパティを通じてアクセスする。
    """

    def __init__(self, site: "Site"):
        """
        初期化メソッド

        Parameters
        ----------
        site : Site
            親サイトインスタンス
        """
        self.site = site

    @property
    def categories(self) -> "ForumCategoryCollection":
        """
        サイト内のフォーラムカテゴリ一覧を取得する

        Returns
        -------
        ForumCategoryCollection
            フォーラムカテゴリのコレクション
        """
        return ForumCategoryCollection.acquire_all(self.site)


@dataclass
class Site:
    """
    Wikidotサイトを表すクラス

    サイトの基本情報とサイトに対する様々な操作機能を提供する。
    ページ、フォーラム、メンバー管理などの機能にアクセスするための起点となる。

    Attributes
    ----------
    client : Client
        クライアントインスタンス
    id : int
        サイトID
    title : str
        サイトのタイトル
    unix_name : str
        サイトのUNIX名（URLの一部として使用される）
    domain : str
        サイトのドメイン（完全修飾ドメイン名）
    ssl_supported : bool
        サイトがSSL/HTTPS対応しているかどうか
    """

    client: "Client"

    id: int
    title: str
    unix_name: str
    domain: str
    ssl_supported: bool

    _members = None
    _moderators = None
    _admins = None

    def __post_init__(self):
        """
        初期化後の処理

        サイト関連の機能を提供する各サブクラスのインスタンスを初期化する。
        """
        self.pages = SitePagesMethods(self)
        self.page = SitePageMethods(self)
        self.forum = SiteForumMethods(self)

    def __str__(self):
        """
        オブジェクトの文字列表現

        Returns
        -------
        str
            サイトオブジェクトの文字列表現
        """
        return f"Site(id={self.id}, title={self.title}, unix_name={self.unix_name})"

    @staticmethod
    def from_unix_name(client: "Client", unix_name: str) -> "Site":
        """
        UNIX名からサイトオブジェクトを取得する

        指定されたUNIX名のサイトにアクセスし、サイト情報を解析してSiteオブジェクトを生成する。

        Parameters
        ----------
        client : Client
            クライアントインスタンス
        unix_name : str
            サイトのUNIX名（例: "fondation"）

        Returns
        -------
        Site
            サイトオブジェクト

        Raises
        ------
        NotFoundException
            指定されたUNIX名のサイトが存在しない場合
        UnexpectedException
            サイト情報の解析中にエラーが発生した場合
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
            raise exceptions.NotFoundException(f"Site is not found: {unix_name}.wikidot.com")

        # サイトが存在する場合
        source = response.text

        # id : WIKIREQUEST.info.siteId = xxxx;
        id_match = re.search(r"WIKIREQUEST\.info\.siteId = (\d+);", source)
        if id_match is None:
            raise exceptions.UnexpectedException(f"Cannot find site id: {unix_name}.wikidot.com")
        site_id = int(id_match.group(1))

        # title : titleタグ
        title_match = re.search(r"<title>(.*?)</title>", source)
        if title_match is None:
            raise exceptions.UnexpectedException(f"Cannot find site title: {unix_name}.wikidot.com")
        title = title_match.group(1)

        # unix_name : WIKIREQUEST.info.siteUnixName = "xxxx";
        unix_name_match = re.search(r'WIKIREQUEST\.info\.siteUnixName = "(.*?)";', source)
        if unix_name_match is None:
            raise exceptions.UnexpectedException(f"Cannot find site unix_name: {unix_name}.wikidot.com")
        unix_name = unix_name_match.group(1)

        # domain :WIKIREQUEST.info.domain = "xxxx";
        domain_match = re.search(r'WIKIREQUEST\.info\.domain = "(.*?)";', source)
        if domain_match is None:
            raise exceptions.UnexpectedException(f"Cannot find site domain: {unix_name}.wikidot.com")
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
        """
        このサイトに対してAjax Module Connectorリクエストを実行する

        Parameters
        ----------
        bodies : list[dict]
            リクエストボディのリスト
        return_exceptions : bool, default False
            例外を返すか送出するか（True: 返す, False: 送出する）

        Returns
        -------
        list | Exception
            レスポンスのリスト、またはreturn_exceptionsがTrueの場合は例外
        """
        return self.client.amc_client.request(bodies, return_exceptions, self.unix_name, self.ssl_supported)

    @property
    def applications(self):
        """
        サイトへの未処理の参加申請を取得する

        Returns
        -------
        list[SiteApplication]
            参加申請のリスト
        """
        return SiteApplication.acquire_all(self)

    @login_required
    def invite_user(self, user: "User", text: str):
        """
        ユーザーをサイトに招待する

        Parameters
        ----------
        user : User
            招待するユーザー
        text : str
            招待メッセージ

        Raises
        ------
        TargetErrorException
            ユーザーが既に招待済み、または既にメンバーの場合
        WikidotStatusCodeException
            その他のWikidot APIエラーが発生した場合
        LoginRequiredException
            ログインしていない場合（@login_required装飾子による）
        """
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

    @property
    def url(self):
        """
        サイトのURLを取得する

        Returns
        -------
        str
            サイトの完全なURL
        """
        return f"http{'s' if self.ssl_supported else ''}://{self.domain}"

    @property
    def members(self):
        """
        サイトのメンバー一覧を取得する

        Returns
        -------
        list[SiteMember]
            サイトメンバーのリスト
        """
        if self._members is None:
            self._members = SiteMember.get(self)
        return self._members

    @property
    def moderators(self):
        """
        サイトのモデレーター一覧を取得する

        Returns
        -------
        list[SiteMember]
            サイトモデレーターのリスト
        """
        if self._moderators is None:
            self._moderators = SiteMember.get(self, "moderators")
        return self._moderators

    @property
    def admins(self):
        """
        サイトの管理者一覧を取得する

        Returns
        -------
        list[SiteMember]
            サイト管理者のリスト
        """
        if self._admins is None:
            self._admins = SiteMember.get(self, "admins")
        return self._admins

    def member_lookup(self, user_name: str, user_id: int | None = None):
        """
        指定されたユーザーがサイトのメンバーかどうかを確認する

        Parameters
        ----------
        user_name : str
            確認するユーザー名
        user_id : int | None, default None
            確認するユーザーID（指定した場合はIDも一致する必要がある）

        Returns
        -------
        bool
            ユーザーがサイトメンバーである場合はTrue、そうでない場合はFalse
        """
        users: list["QMCUser"] = QuickModule.member_lookup(self.id, user_name)

        if len(users) == 0:
            return False

        for user in users:
            if user.name.strip() == user_name and (user_id is None or user.id == user_id):
                return True

        return False

    def get_thread(self, thread_id: int):
        """
        スレッドを取得する

        Parameters
        ----------
        thread_id : int
            スレッドID

        Returns
        -------
        ForumThread
            スレッドオブジェクト
        """
        return ForumThread.get_from_id(self, thread_id)

    def get_threads(self, thread_ids: list[int]):
        """
        複数のスレッドを取得する

        Parameters
        ----------
        thread_ids : list[int]
            スレッドIDのリスト

        Returns
        -------
        list[ForumThread]
            スレッドオブジェクトのリスト
        """
        return ForumThreadCollection.acquire_from_thread_ids(self, thread_ids)
