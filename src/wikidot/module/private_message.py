from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

import httpx
from bs4 import BeautifulSoup, ResultSet, Tag

from wikidot.common import exceptions
from wikidot.common.decorators import login_required
from wikidot.util.parser import odate as odate_parser
from wikidot.util.parser import user as user_parser

if TYPE_CHECKING:
    from wikidot.module.client import Client
    from wikidot.module.user import AbstractUser, User


class PrivateMessageCollection(list["PrivateMessage"]):
    def __str__(self):
        return f"{self.__class__.__name__}({len(self)} messages)"

    def __iter__(self) -> Iterator["PrivateMessage"]:
        return super().__iter__()

    @staticmethod
    @login_required
    def from_ids(
        client: "Client", message_ids: list[int]
    ) -> "PrivateMessageCollection":
        """メッセージIDのリストからメッセージオブジェクトのリストを取得する

        Parameters
        ----------
        client: Client
            クライアント
        message_ids: list[int]
            メッセージIDのリスト

        Returns
        -------
        PrivateMessageCollection
            メッセージオブジェクトのリスト
        """
        bodies = []

        for message_id in message_ids:
            bodies.append(
                {
                    "item": message_id,
                    "moduleName": "dashboard/messages/DMViewMessageModule",
                }
            )

        responses: [httpx.Response | Exception] = client.amc_client.request(
            bodies, return_exceptions=True
        )

        messages = []

        for index, response in enumerate(responses):
            if isinstance(response, exceptions.WikidotStatusCodeException):
                if response.status_code == "no_message":
                    raise exceptions.ForbiddenException(
                        f"Failed to get message: {message_ids[index]}"
                    ) from response

            if isinstance(response, Exception):
                raise response

            html = BeautifulSoup(response.json()["body"], "lxml")

            sender, recipient = html.select("div.pmessage div.header span.printuser")

            messages.append(
                PrivateMessage(
                    client=client,
                    id=message_ids[index],
                    sender=user_parser(client, sender),
                    recipient=user_parser(client, recipient),
                    subject=html.select_one(
                        "div.pmessage div.header span.subject"
                    ).get_text(),
                    body=html.select_one("div.pmessage div.body").get_text(),
                    created_at=odate_parser(html.select_one("div.header span.odate")),
                )
            )

        return PrivateMessageCollection(messages)

    @staticmethod
    @login_required
    def _acquire(client: "Client", module_name: str):
        """受信・送信箱のメッセージを取得する

        Parameters
        ----------
        client: Client
            クライアント
        module_name: str
            モジュール名

        Returns
        -------
        PrivateMessageCollection
            受信箱のメッセージ
        """
        # pager取得
        response = client.amc_client.request([{"moduleName": module_name}])[0]

        html = BeautifulSoup(response.json()["body"], "lxml")
        # pagerの最後から2番目の要素を取得
        # pageが存在しない場合は1ページのみ
        pager: ResultSet[Tag] = html.select("div.pager span.target")
        max_page: int = int(pager[-2].get_text()) if len(pager) > 2 else 1

        if max_page > 1:
            # メッセージ取得
            bodies = [
                {"page": page, "moduleName": module_name}
                for page in range(1, max_page + 1)
            ]

            responses: [httpx.Response | Exception] = client.amc_client.request(
                bodies, return_exceptions=False
            )
        else:
            responses = [response]

        message_ids = []
        for response in responses:
            html = BeautifulSoup(response.json()["body"], "lxml")
            # tr.messageのdata-href末尾の数字を取得
            message_ids.extend(
                [
                    int(tr["data-href"].split("/")[-1])
                    for tr in html.select("tr.message")
                ]
            )

        return PrivateMessageCollection.from_ids(client, message_ids)


class PrivateMessageInbox(PrivateMessageCollection):
    @staticmethod
    def from_ids(client: "Client", message_ids: list[int]) -> "PrivateMessageInbox":
        """メッセージIDのリストから受信箱のメッセージオブジェクトのリストを取得する

        Parameters
        ----------
        client: Client
            クライアント
        message_ids: list[int]
            メッセージIDのリスト

        Returns
        -------
        PrivateMessageInbox
            受信箱のメッセージオブジェクトのリスト
        """
        return PrivateMessageInbox(
            PrivateMessageCollection.from_ids(client, message_ids)
        )

    @staticmethod
    def acquire(client: "Client"):
        """受信箱のメッセージを取得する

        Parameters
        ----------
        client: Client
            クライアント

        Returns
        -------
        PrivateMessageInbox
            受信箱のメッセージ
        """
        return PrivateMessageInbox(
            PrivateMessageCollection._acquire(
                client, "dashboard/messages/DMInboxModule"
            )
        )


class PrivateMessageSentBox(PrivateMessageCollection):
    @staticmethod
    def from_ids(client: "Client", message_ids: list[int]) -> "PrivateMessageSentBox":
        """メッセージIDのリストから受信箱のメッセージオブジェクトのリストを取得する

        Parameters
        ----------
        client: Client
            クライアント
        message_ids: list[int]
            メッセージIDのリスト

        Returns
        -------
        PrivateMessageSentBox
            受信箱のメッセージオブジェクトのリスト
        """
        return PrivateMessageSentBox(
            PrivateMessageCollection.from_ids(client, message_ids)
        )

    @staticmethod
    def acquire(client: "Client") -> "PrivateMessageSentBox":
        """送信箱のメッセージを取得する

        Parameters
        ----------
        client: Client
            クライアント

        Returns
        -------
        PrivateMessageSentBox
            受信箱のメッセージ
        """
        return PrivateMessageSentBox(
            PrivateMessageCollection._acquire(client, "dashboard/messages/DMSentModule")
        )


@dataclass
class PrivateMessage:
    """プライベートメッセージオブジェクト

    Attributes
    ----------
    client: Client
        クライアントクラスのインスタンス
    id: int
        メッセージID
    sender: AbstractUser
        送信者
    recipient: AbstractUser
        受信者
    subject: str
        件名
    body: str
        本文
    created_at: str
        作成日時
    """

    client: "Client"
    id: int
    sender: "AbstractUser"
    recipient: "AbstractUser"
    subject: str
    body: str
    created_at: datetime

    def __str__(self):
        return f"PrivateMessage(id={self.id}, sender={self.sender}, recipient={self.recipient}, subject={self.subject})"

    @staticmethod
    def from_id(client: "Client", message_id: int) -> "PrivateMessage":
        """メッセージIDからメッセージオブジェクトを取得する

        Parameters
        ----------
        client: Client
            クライアント
        message_id: int
            メッセージID

        Returns
        -------
        PrivateMessage
            メッセージオブジェクト
        """
        return PrivateMessageCollection.from_ids(client, [message_id])[0]

    @staticmethod
    @login_required
    def send(client: "Client", recipient: "User", subject: str, body: str) -> None:
        """メッセージを送信する

        Parameters
        ----------
        client: Client
            クライアント
        recipient: User
            受信者
        subject: str
            件名
        body: str
            本文
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
