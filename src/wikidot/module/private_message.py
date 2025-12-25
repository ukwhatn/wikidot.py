"""
Module for handling Wikidot private messages

This module provides classes and functionality related to Wikidot private messages (PM).
It enables operations such as sending messages, retrieving inbox/sent box, and viewing messages.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from bs4 import BeautifulSoup, ResultSet, Tag
from typing_extensions import Self

from ..common import exceptions
from ..common.decorators import login_required
from ..util.parser import odate as odate_parser
from ..util.parser import user as user_parser

if TYPE_CHECKING:
    from .client import Client
    from .user import AbstractUser, User


class PrivateMessageCollection(list["PrivateMessage"]):
    """
    Base class representing a collection of private messages

    A list extension class for storing multiple private messages and performing batch operations.
    Inherited to represent specific message groups such as inbox or sent box.
    """

    def __str__(self) -> str:
        """
        String representation of the object

        Returns
        -------
        str
            String representation of the message collection
        """
        return f"{self.__class__.__name__}({len(self)} messages)"

    def __iter__(self) -> Iterator["PrivateMessage"]:
        """
        Iterator that returns messages in the collection sequentially

        Returns
        -------
        Iterator[PrivateMessage]
            Iterator of message objects
        """
        return super().__iter__()

    def find(self, id: int) -> Optional["PrivateMessage"]:
        """
        Retrieve a message with the specified ID

        Parameters
        ----------
        id : int
            The ID of the message to retrieve

        Returns
        -------
        PrivateMessage | None
            The retrieved message object, or None if not found
        """
        for message in self:
            if message.id == id:
                return message

        return None

    @staticmethod
    @login_required
    def from_ids(client: "Client", message_ids: list[int]) -> "PrivateMessageCollection":
        """
        Retrieve a collection of message objects from a list of message IDs

        Batch retrieves messages with the specified IDs and returns them as a collection.

        Parameters
        ----------
        client : Client
            Client instance
        message_ids : list[int]
            List of message IDs to retrieve

        Returns
        -------
        PrivateMessageCollection
            Collection of retrieved messages

        Raises
        ------
        LoginRequiredException
            If not logged in
        ForbiddenException
            If no permission to access the message
        """
        bodies = []

        for message_id in message_ids:
            bodies.append(
                {
                    "item": message_id,
                    "moduleName": "dashboard/messages/DMViewMessageModule",
                }
            )

        responses = client.amc_client.request(bodies, return_exceptions=True)

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
    def _acquire(client: "Client", module_name: str) -> "PrivateMessageCollection":
        """
        Internal method to retrieve private messages from a specific module

        Common method for retrieving message lists such as inbox or sent box.
        If pagination exists, retrieves from all pages.

        Parameters
        ----------
        client : Client
            Client instance
        module_name : str
            Module name to retrieve messages from

        Returns
        -------
        PrivateMessageCollection
            Collection of retrieved messages

        Raises
        ------
        LoginRequiredException
            If not logged in
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
            bodies = [{"page": page, "moduleName": module_name} for page in range(1, max_page + 1)]

            responses = client.amc_client.request(bodies, return_exceptions=False)
        else:
            responses = (response,)

        message_ids = []
        for response in responses:
            html = BeautifulSoup(response.json()["body"], "lxml")
            # tr.messageのdata-href末尾の数字を取得
            message_ids.extend([int(str(tr["data-href"]).split("/")[-1]) for tr in html.select("tr.message")])

        return PrivateMessageCollection.from_ids(client, message_ids)

    @classmethod
    def _factory_from_ids(cls, client: "Client", message_ids: list[int]) -> Self:
        """
        Generic factory method to retrieve message collection from a list of message IDs

        Parameters
        ----------
        client : Client
            Client instance
        message_ids : list[int]
            List of message IDs to retrieve

        Returns
        -------
        cls
            Instance of the calling class
        """
        return cls(PrivateMessageCollection.from_ids(client, message_ids))

    @classmethod
    def _factory_acquire(cls, client: "Client", module_name: str) -> Self:
        """
        Generic factory method to retrieve messages from a specified module

        Parameters
        ----------
        client : Client
            Client instance
        module_name : str
            Module name to use for retrieval

        Returns
        -------
        cls
            Instance of the calling class

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        return cls(PrivateMessageCollection._acquire(client, module_name))


class PrivateMessageInbox(PrivateMessageCollection):
    """
    Class representing a collection of received private messages

    A specialized class of PrivateMessageCollection for storing and operating
    on private messages in the inbox.
    """

    @classmethod
    def from_ids(cls, client: "Client", message_ids: list[int]) -> "PrivateMessageInbox":
        """
        Retrieve inbox message collection from a list of message IDs

        Parameters
        ----------
        client : Client
            Client instance
        message_ids : list[int]
            List of message IDs to retrieve

        Returns
        -------
        PrivateMessageInbox
            Collection of inbox messages
        """
        return cls._factory_from_ids(client, message_ids)

    @classmethod
    def acquire(cls, client: "Client") -> "PrivateMessageInbox":
        """
        Retrieve all inbox messages for the logged-in user

        Parameters
        ----------
        client : Client
            Client instance

        Returns
        -------
        PrivateMessageInbox
            Collection of inbox messages

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        return cls._factory_acquire(client, "dashboard/messages/DMInboxModule")


class PrivateMessageSentBox(PrivateMessageCollection):
    """
    Class representing a collection of sent private messages

    A specialized class of PrivateMessageCollection for storing and operating
    on private messages in the sent box.
    """

    @classmethod
    def from_ids(cls, client: "Client", message_ids: list[int]) -> "PrivateMessageSentBox":
        """
        Retrieve sent box message collection from a list of message IDs

        Parameters
        ----------
        client : Client
            Client instance
        message_ids : list[int]
            List of message IDs to retrieve

        Returns
        -------
        PrivateMessageSentBox
            Collection of sent box messages
        """
        return cls._factory_from_ids(client, message_ids)

    @classmethod
    def acquire(cls, client: "Client") -> "PrivateMessageSentBox":
        """
        Retrieve all sent box messages for the logged-in user

        Parameters
        ----------
        client : Client
            Client instance

        Returns
        -------
        PrivateMessageSentBox
            Collection of sent box messages

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        return cls._factory_acquire(client, "dashboard/messages/DMSentModule")


@dataclass
class PrivateMessage:
    """
    Class representing a Wikidot private message

    Holds information about private messages exchanged between users.
    Provides basic information such as sender, recipient, subject, and body.

    Attributes
    ----------
    client : Client
        Client instance
    id : int
        Message ID
    sender : AbstractUser
        Sender of the message
    recipient : AbstractUser
        Recipient of the message
    subject : str
        Subject of the message
    body : str
        Body of the message
    created_at : datetime
        Creation date and time of the message
    """

    client: "Client"
    id: int
    sender: "AbstractUser"
    recipient: "AbstractUser"
    subject: str
    body: str
    created_at: datetime

    def __str__(self) -> str:
        """
        String representation of the object

        Returns
        -------
        str
            String representation of the message
        """
        return f"PrivateMessage(id={self.id}, sender={self.sender}, recipient={self.recipient}, subject={self.subject})"

    @staticmethod
    def from_id(client: "Client", message_id: int) -> "PrivateMessage":
        """
        Retrieve a message object from a message ID

        Parameters
        ----------
        client : Client
            Client instance
        message_id : int
            Message ID to retrieve

        Returns
        -------
        PrivateMessage
            Retrieved message object

        Raises
        ------
        LoginRequiredException
            If not logged in
        ForbiddenException
            If no permission to access the message
        IndexError
            If message not found
        """
        return PrivateMessageCollection.from_ids(client, [message_id])[0]

    @staticmethod
    @login_required
    def send(client: "Client", recipient: "User", subject: str, body: str) -> None:
        """
        Send a private message

        Parameters
        ----------
        client : Client
            Client instance
        recipient : User
            Recipient of the message
        subject : str
            Subject of the message
        body : str
            Body of the message

        Raises
        ------
        LoginRequiredException
            If not logged in
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
