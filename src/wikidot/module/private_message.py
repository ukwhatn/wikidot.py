"""
Wikidotのプライベートメッセージを扱うモジュール

このモジュールは、Wikidotのプライベートメッセージ（PM）に関連するクラスや機能を提供する。
メッセージの送信、受信箱・送信箱の取得、メッセージの閲覧などの操作が可能。
"""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional, cast

import httpx
from bs4 import BeautifulSoup, ResultSet, Tag

from ..common import exceptions
from ..common.decorators import login_required
from ..util.parser import odate as odate_parser
from ..util.parser import user as user_parser

if TYPE_CHECKING:
    from .client import Client
    from .user import AbstractUser, User


class PrivateMessageCollection(list["PrivateMessage"]):
    """
    プライベートメッセージのコレクションを表す基底クラス

    複数のプライベートメッセージを格納し、一括して操作するためのリスト拡張クラス。
    受信箱や送信箱など、特定のメッセージグループを表現するために継承される。
    """

    def __str__(self):
        """
        オブジェクトの文字列表現

        Returns
        -------
        str
            メッセージコレクションの文字列表現
        """
        return f"{self.__class__.__name__}({len(self)} messages)"

    def __iter__(self) -> Iterator["PrivateMessage"]:
        """
        コレクション内のメッセージを順に返すイテレータ

        Returns
        -------
        Iterator[PrivateMessage]
            メッセージオブジェクトのイテレータ
        """
        return super().__iter__()

    def find(self, id: int) -> Optional["PrivateMessage"]:
        """
        指定IDのメッセージを取得する

        Parameters
        ----------
        id : int
            取得するメッセージのID

        Returns
        -------
        PrivateMessage | None
            取得したメッセージオブジェクト。見つからない場合はNone
        """
        for message in self:
            if message.id == id:
                return message

        return None

    @staticmethod
    @login_required
    def from_ids(client: "Client", message_ids: list[int]) -> "PrivateMessageCollection":
        """
        メッセージIDのリストからメッセージオブジェクトのコレクションを取得する

        指定されたIDのメッセージを一括で取得し、コレクションとして返す。

        Parameters
        ----------
        client : Client
            クライアントインスタンス
        message_ids : list[int]
            取得するメッセージIDのリスト

        Returns
        -------
        PrivateMessageCollection
            取得したメッセージのコレクション

        Raises
        ------
        LoginRequiredException
            ログインしていない場合
        ForbiddenException
            メッセージにアクセスする権限がない場合
        """
        bodies = []

        for message_id in message_ids:
            bodies.append(
                {
                    "item": message_id,
                    "moduleName": "dashboard/messages/DMViewMessageModule",
                }
            )

        responses: tuple[httpx.Response | Exception] = client.amc_client.request(bodies, return_exceptions=True)

        messages = []

        for index, response in enumerate(responses):
            if isinstance(response, exceptions.WikidotStatusCodeException):
                if response.status_code == "no_message":
                    raise exceptions.ForbiddenException(f"Failed to get message: {message_ids[index]}") from response

            if isinstance(response, Exception):
                raise response

            html = BeautifulSoup(response.json()["body"], "lxml")

            sender, recipient = html.select("div.pmessage div.header span.printuser")

            subject_element = html.select_one("div.pmessage div.header span.subject")
            body_element = html.select_one("div.pmessage div.body")
            odate_element = html.select_one("div.header span.odate")

            messages.append(
                PrivateMessage(
                    client=client,
                    id=message_ids[index],
                    sender=user_parser(client, sender),
                    recipient=user_parser(client, recipient),
                    subject=subject_element.get_text() if subject_element else "",
                    body=body_element.get_text() if body_element else "",
                    created_at=(odate_parser(odate_element) if odate_element else datetime.fromtimestamp(0)),
                )
            )

        return PrivateMessageCollection(messages)

    @staticmethod
    @login_required
    def _acquire(client: "Client", module_name: str):
        """
        特定のモジュールからプライベートメッセージを取得する内部メソッド

        受信箱や送信箱などのメッセージ一覧を取得するための共通メソッド。
        ページネーションが存在する場合は、すべてのページから取得する。

        Parameters
        ----------
        client : Client
            クライアントインスタンス
        module_name : str
            メッセージを取得するモジュール名

        Returns
        -------
        PrivateMessageCollection
            取得したメッセージのコレクション

        Raises
        ------
        LoginRequiredException
            ログインしていない場合
        """
        # pager取得
        response: httpx.Response = cast(httpx.Response, client.amc_client.request([{"moduleName": module_name}])[0])

        html = BeautifulSoup(response.json()["body"], "lxml")
        # pagerの最後から2番目の要素を取得
        # pageが存在しない場合は1ページのみ
        pager: ResultSet[Tag] = html.select("div.pager span.target")
        max_page: int = int(pager[-2].get_text()) if len(pager) > 2 else 1

        if max_page > 1:
            # メッセージ取得
            bodies = [{"page": page, "moduleName": module_name} for page in range(1, max_page + 1)]

            responses: tuple[httpx.Response] = cast(
                tuple[httpx.Response],
                client.amc_client.request(bodies, return_exceptions=False),
            )
        else:
            responses = (response,)

        message_ids = []
        for response in responses:
            html = BeautifulSoup(response.json()["body"], "lxml")
            # tr.messageのdata-href末尾の数字を取得
            message_ids.extend([int(str(tr["data-href"]).split("/")[-1]) for tr in html.select("tr.message")])

        return PrivateMessageCollection.from_ids(client, message_ids)


class PrivateMessageInbox(PrivateMessageCollection):
    """
    受信したプライベートメッセージのコレクションを表すクラス

    受信箱内のプライベートメッセージを格納し、操作するための
    PrivateMessageCollectionの特殊化クラス。
    """

    @staticmethod
    def from_ids(client: "Client", message_ids: list[int]) -> "PrivateMessageInbox":
        """
        メッセージIDのリストから受信箱のメッセージコレクションを取得する

        Parameters
        ----------
        client : Client
            クライアントインスタンス
        message_ids : list[int]
            取得するメッセージIDのリスト

        Returns
        -------
        PrivateMessageInbox
            受信箱メッセージのコレクション
        """
        return PrivateMessageInbox(PrivateMessageCollection.from_ids(client, message_ids))

    @staticmethod
    def acquire(client: "Client"):
        """
        ログイン中のユーザーの受信箱メッセージをすべて取得する

        Parameters
        ----------
        client : Client
            クライアントインスタンス

        Returns
        -------
        PrivateMessageInbox
            受信箱メッセージのコレクション

        Raises
        ------
        LoginRequiredException
            ログインしていない場合
        """
        return PrivateMessageInbox(PrivateMessageCollection._acquire(client, "dashboard/messages/DMInboxModule"))


class PrivateMessageSentBox(PrivateMessageCollection):
    """
    送信したプライベートメッセージのコレクションを表すクラス

    送信箱内のプライベートメッセージを格納し、操作するための
    PrivateMessageCollectionの特殊化クラス。
    """

    @staticmethod
    def from_ids(client: "Client", message_ids: list[int]) -> "PrivateMessageSentBox":
        """
        メッセージIDのリストから送信箱のメッセージコレクションを取得する

        Parameters
        ----------
        client : Client
            クライアントインスタンス
        message_ids : list[int]
            取得するメッセージIDのリスト

        Returns
        -------
        PrivateMessageSentBox
            送信箱メッセージのコレクション
        """
        return PrivateMessageSentBox(PrivateMessageCollection.from_ids(client, message_ids))

    @staticmethod
    def acquire(client: "Client") -> "PrivateMessageSentBox":
        """
        ログイン中のユーザーの送信箱メッセージをすべて取得する

        Parameters
        ----------
        client : Client
            クライアントインスタンス

        Returns
        -------
        PrivateMessageSentBox
            送信箱メッセージのコレクション

        Raises
        ------
        LoginRequiredException
            ログインしていない場合
        """
        return PrivateMessageSentBox(PrivateMessageCollection._acquire(client, "dashboard/messages/DMSentModule"))


@dataclass
class PrivateMessage:
    """
    Wikidotプライベートメッセージを表すクラス

    ユーザー間でやりとりされるプライベートメッセージの情報を保持する。
    メッセージの送信者、受信者、件名、本文などの基本情報を提供する。

    Attributes
    ----------
    client : Client
        クライアントインスタンス
    id : int
        メッセージID
    sender : AbstractUser
        メッセージの送信者
    recipient : AbstractUser
        メッセージの受信者
    subject : str
        メッセージの件名
    body : str
        メッセージの本文
    created_at : datetime
        メッセージの作成日時
    """

    client: "Client"
    id: int
    sender: "AbstractUser"
    recipient: "AbstractUser"
    subject: str
    body: str
    created_at: datetime

    def __str__(self):
        """
        オブジェクトの文字列表現

        Returns
        -------
        str
            メッセージの文字列表現
        """
        return f"PrivateMessage(id={self.id}, sender={self.sender}, recipient={self.recipient}, subject={self.subject})"

    @staticmethod
    def from_id(client: "Client", message_id: int) -> "PrivateMessage":
        """
        メッセージIDからメッセージオブジェクトを取得する

        Parameters
        ----------
        client : Client
            クライアントインスタンス
        message_id : int
            取得するメッセージID

        Returns
        -------
        PrivateMessage
            取得したメッセージオブジェクト

        Raises
        ------
        LoginRequiredException
            ログインしていない場合
        ForbiddenException
            メッセージにアクセスする権限がない場合
        IndexError
            メッセージが見つからない場合
        """
        return PrivateMessageCollection.from_ids(client, [message_id])[0]

    @staticmethod
    @login_required
    def send(client: "Client", recipient: "User", subject: str, body: str) -> None:
        """
        プライベートメッセージを送信する

        Parameters
        ----------
        client : Client
            クライアントインスタンス
        recipient : User
            メッセージの受信者
        subject : str
            メッセージの件名
        body : str
            メッセージの本文

        Raises
        ------
        LoginRequiredException
            ログインしていない場合
        """
        client.amc_client.request(
            [
                {
                    "source": body,
                    "subject": subject,
                    "to_user_id": recipient.id,
                    "action": "DashboardMessageAction",
                    "event": "send",
                    "moduleName": "Empty",
                }
            ]
        )
