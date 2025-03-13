"""
Wikidotサイトのメンバーを扱うモジュール

このモジュールは、Wikidotサイトのメンバーに関連するクラスや機能を提供する。
メンバーの情報取得や権限変更などの操作が可能。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

from ..common.exceptions import (
    TargetErrorException,
    WikidotStatusCodeException,
)
from ..util.parser import odate as odate_parser
from ..util.parser import user as user_parser

if TYPE_CHECKING:
    from .site import Site
    from .user import AbstractUser


@dataclass
class SiteMember:
    """
    Wikidotサイトのメンバーを表すクラス

    サイトのメンバー情報を保持し、権限変更などの操作機能を提供する。

    Attributes
    ----------
    site : Site
        メンバーが所属するサイト
    user : AbstractUser
        メンバーユーザー
    joined_at : datetime | None
        サイトへの参加日時（取得できない場合はNone）
    """

    site: "Site"
    user: "AbstractUser"
    joined_at: datetime | None

    @staticmethod
    def _parse(site: "Site", html: BeautifulSoup) -> list["SiteMember"]:
        """
        メンバーリストページのHTMLからメンバー情報を抽出する内部メソッド

        Parameters
        ----------
        site : Site
            メンバーが所属するサイト
        html : BeautifulSoup
            解析対象のHTML

        Returns
        -------
        list[SiteMember]
            抽出されたメンバーのリスト
        """
        members: list["SiteMember"] = []

        for row in html.select("table tr"):
            tds = row.select("td")
            user_elem = tds[0].select_one(".printuser")

            if user_elem is None:
                continue

            user = user_parser(site.client, user_elem)

            # tdsが2つあったら加入日時がある
            if len(tds) == 2:
                joined_at_elem = tds[1].select_one(".odate")
                if joined_at_elem is None:
                    joined_at = None
                else:
                    joined_at = odate_parser(joined_at_elem)
            else:
                joined_at = None

            members.append(SiteMember(site, user, joined_at))

        return members

    @staticmethod
    def get(site: "Site", group: str | None = None) -> list["SiteMember"]:
        """
        サイトのメンバーリストを取得する

        指定したグループ（管理者、モデレーターなど）のメンバー一覧を取得する。

        Parameters
        ----------
        site : Site
            メンバーリストを取得するサイト
        group : str | None, default None
            取得するメンバーのグループ（"admins", "moderators", または "" で全メンバー）

        Returns
        -------
        list[SiteMember]
            メンバーのリスト

        Raises
        ------
        ValueError
            無効なグループが指定された場合
        """
        if group is None:
            group = ""

        if group not in ["admins", "moderators", ""]:
            raise ValueError("Invalid group")

        members: list["SiteMember"] = []

        first_response = site.amc_request(
            [
                {
                    "moduleName": "membership/MembersListModule",
                    "page": 1,
                    "group": group,
                }
            ]
        )[0]

        first_body = first_response.json()["body"]
        first_html = BeautifulSoup(first_body, "lxml")

        members.extend(SiteMember._parse(site, first_html))

        pager = first_html.select_one("div.pager")
        if pager is None:
            return members

        last_page = int(pager.select("a")[-2].text)
        if last_page == 1:
            return members

        responses = site.amc_request(
            [
                {
                    "moduleName": "membership/MembersListModule",
                    "page": page,
                    "group": group,
                }
                for page in range(2, last_page + 1)
            ]
        )

        for response in responses:
            body = response.json()["body"]
            html = BeautifulSoup(body, "lxml")
            members.extend(SiteMember._parse(site, html))

        return members

    def _change_group(self, event: str):
        """
        メンバーのグループ（権限）を変更する内部メソッド

        モデレーターや管理者への昇格、または降格を行う共通メソッド。

        Parameters
        ----------
        event : str
            変更イベント（"toModerators", "removeModerator", "toAdmins", "removeAdmin"）

        Raises
        ------
        ValueError
            無効なイベントが指定された場合
        ForbiddenException
            権限不足の場合
        TargetErrorException
            ユーザーが既に指定された権限を持っている、または持っていない場合
        WikidotStatusCodeException
            その他のエラーが発生した場合
        """
        if event not in [
            "toModerators",
            "removeModerator",
            "toAdmins",
            "removeAdmin",
        ]:
            raise ValueError("Invalid event")

        try:
            self.site.amc_request(
                [
                    {
                        "action": "ManageSiteMembershipAction",
                        "event": event,
                        "user_id": self.user.id,
                        "moduleName": "",
                    }
                ]
            )
        except WikidotStatusCodeException as e:
            if e.status_code == "not_already":
                raise TargetErrorException(f"User is not moderator/admin: {self.user.name}") from e

            if e.status_code in ("already_admin", "already_moderator"):
                raise TargetErrorException(
                    f"User is already {e.status_code.removeprefix('already_')}: {self.user.name}"
                ) from e

            raise e

    def to_moderator(self):
        """
        メンバーをモデレーターに昇格させる

        Raises
        ------
        ForbiddenException
            権限不足の場合
        TargetErrorException
            ユーザーが既にモデレーターである場合
        WikidotStatusCodeException
            その他のエラーが発生した場合
        """
        self._change_group("toModerators")

    def remove_moderator(self):
        """
        メンバーのモデレーター権限を削除する

        Raises
        ------
        ForbiddenException
            権限不足の場合
        TargetErrorException
            ユーザーがモデレーターでない場合
        WikidotStatusCodeException
            その他のエラーが発生した場合
        """
        self._change_group("removeModerator")

    def to_admin(self):
        """
        メンバーを管理者に昇格させる

        Raises
        ------
        ForbiddenException
            権限不足の場合
        TargetErrorException
            ユーザーが既に管理者である場合
        WikidotStatusCodeException
            その他のエラーが発生した場合
        """
        self._change_group("toAdmins")

    def remove_admin(self):
        """
        メンバーの管理者権限を削除する

        Raises
        ------
        ForbiddenException
            権限不足の場合
        TargetErrorException
            ユーザーが管理者でない場合
        WikidotStatusCodeException
            その他のエラーが発生した場合
        """
        self._change_group("removeAdmin")
