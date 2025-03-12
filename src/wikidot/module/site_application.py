"""
Wikidotサイトへの参加申請を扱うモジュール

このモジュールは、Wikidotサイトへの参加申請に関連するクラスや機能を提供する。
申請の取得、承認、拒否などの操作が可能。
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

from ..common import exceptions
from ..common.decorators import login_required
from ..util.parser import user as user_parser

if TYPE_CHECKING:
    from ..module.site import Site
    from ..module.user import AbstractUser


@dataclass
class SiteApplication:
    """
    Wikidotサイトへの参加申請を表すクラス

    ユーザーからサイトへの参加申請情報を保持し、申請の承認や拒否などの
    処理機能を提供する。

    Attributes
    ----------
    site : Site
        申請先のサイト
    user : AbstractUser
        申請者
    text : str
        申請メッセージ
    """

    site: "Site"
    user: "AbstractUser"
    text: str

    def __str__(self):
        """
        オブジェクトの文字列表現

        Returns
        -------
        str
            申請の文字列表現
        """
        return f"SiteApplication(user={self.user}, site={self.site}, text={self.text})"

    @staticmethod
    @login_required
    def acquire_all(site: "Site") -> list["SiteApplication"]:
        """
        サイトへの未処理の参加申請をすべて取得する

        Parameters
        ----------
        site : Site
            参加申請を取得するサイト

        Returns
        -------
        list[SiteApplication]
            参加申請のリスト

        Raises
        ------
        LoginRequiredException
            ログインしていない場合
        ForbiddenException
            サイトの参加申請を管理する権限がない場合
        UnexpectedException
            応答の解析に失敗した場合
        """
        response = site.amc_request([{"moduleName": "managesite/ManageSiteMembersApplicationsModule"}])[0]

        body = response.json()["body"]

        if "WIKIDOT.page.listeners.loginClick(event)" in body:
            raise exceptions.ForbiddenException("You are not allowed to access this page")

        html = BeautifulSoup(response.json()["body"], "lxml")

        applications = []

        user_elements = html.select("h3 span.printuser")
        text_wrapper_elements = html.select("table")

        if len(user_elements) != len(text_wrapper_elements):
            raise exceptions.UnexpectedException("Length of user_elements and text_wrapper_elements are different")

        for i in range(len(user_elements)):
            user_element = user_elements[i]
            text_wrapper_element = text_wrapper_elements[i]

            user = user_parser(site.client, user_element)
            text = text_wrapper_element.select("td")[1].text.strip()

            applications.append(SiteApplication(site, user, text))

        return applications

    @login_required
    def _process(self, action: str):
        """
        参加申請を処理する内部メソッド

        承認または拒否の処理を行う共通メソッド。

        Parameters
        ----------
        action : str
            処理の種類 ("accept" または "decline")

        Raises
        ------
        LoginRequiredException
            ログインしていない場合
        ValueError
            無効なアクションが指定された場合
        NotFoundException
            指定された申請が見つからない場合
        WikidotStatusCodeException
            その他のエラーが発生した場合
        """
        if action not in ["accept", "decline"]:
            raise ValueError(f"Invalid action: {action}")

        try:
            self.site.amc_request(
                [
                    {
                        "action": "ManageSiteMembershipAction",
                        "event": "acceptApplication",
                        "user_id": self.user.id,
                        "text": f"your application has been {action}ed",
                        "type": action,
                        "moduleName": "Empty",
                    }
                ]
            )
        except exceptions.WikidotStatusCodeException as e:
            if e.status_code == "no_application":
                raise exceptions.NotFoundException(f"Application not found: {self.user}") from e
            else:
                raise e

    def accept(self):
        """
        参加申請を承認する

        申請者をサイトのメンバーとして追加する。

        Raises
        ------
        LoginRequiredException
            ログインしていない場合
        NotFoundException
            指定された申請が見つからない場合
        WikidotStatusCodeException
            その他のエラーが発生した場合
        """
        self._process("accept")

    def decline(self):
        """
        参加申請を拒否する

        申請者の参加を拒否し、申請を削除する。

        Raises
        ------
        LoginRequiredException
            ログインしていない場合
        NotFoundException
            指定された申請が見つからない場合
        WikidotStatusCodeException
            その他のエラーが発生した場合
        """
        self._process("decline")
