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
from ..connector.ajax import require_body
from ..util.amc_body import omit_falsy
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

            html = BeautifulSoup(require_body(response, "dashboard/messages/DMViewMessageModule"), "lxml")

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

        html = BeautifulSoup(require_body(response, module_name), "lxml")
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
            html = BeautifulSoup(require_body(response, module_name), "lxml")
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

    @staticmethod
    @login_required
    def mark_as_read(client: "Client", message_ids: list[int]) -> None:
        """
        Mark messages as read

        Wraps `DashboardMessageAction/setAsReaded` (the misspelling is
        Wikidot's own event name on the wire and is intentionally kept
        as-is here; only this Python method name uses correct spelling).

        Parameters
        ----------
        client : Client
            Client instance
        message_ids : list[int]
            IDs of the messages to mark as read

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        client.amc_client.request(
            [
                {
                    "action": "DashboardMessageAction",
                    "event": "setAsReaded",
                    "selected": message_ids,
                    "moduleName": "Empty",
                }
            ]
        )

    @staticmethod
    @login_required
    def mark_as_unread(client: "Client", message_ids: list[int]) -> None:
        """
        Mark messages as unread

        Wraps `DashboardMessageAction/setAsUnreaded`.

        Parameters
        ----------
        client : Client
            Client instance
        message_ids : list[int]
            IDs of the messages to mark as unread

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        client.amc_client.request(
            [
                {
                    "action": "DashboardMessageAction",
                    "event": "setAsUnreaded",
                    "selected": message_ids,
                    "moduleName": "Empty",
                }
            ]
        )

    @staticmethod
    @login_required
    def remove_messages(client: "Client", message_ids: list[int]) -> None:
        """
        Delete messages

        Wraps `DashboardMessageAction/removeMessages`.

        Parameters
        ----------
        client : Client
            Client instance
        message_ids : list[int]
            IDs of the messages to delete

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        client.amc_client.request(
            [
                {
                    "action": "DashboardMessageAction",
                    "event": "removeMessages",
                    "messages": message_ids,
                    "moduleName": "Empty",
                }
            ]
        )


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

    @staticmethod
    @login_required
    def save_draft(client: "Client", subject: str, body: str, recipient: Optional["User"] = None) -> None:
        """
        Save a private message draft

        Parameters
        ----------
        client : Client
            Client instance
        subject : str
            Draft subject
        body : str
            Draft body
        recipient : User | None, default None
            Intended recipient. May be omitted (the real form allows a
            draft with no recipient selected yet)

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        client.amc_client.request(
            [
                {
                    "action": "DashboardMessageAction",
                    "event": "saveDraft",
                    "source": body,
                    "subject": subject,
                    "moduleName": "Empty",
                    **omit_falsy(to_user_id=recipient.id if recipient is not None else False),
                }
            ]
        )

    @staticmethod
    @login_required
    def check_can_send(client: "Client", user: "AbstractUser") -> None:
        """
        Check whether the account is allowed to send a private message to a user

        Wraps `DashboardMessageAction/checkCan`. Does not return a boolean:
        only the generic no_permission rejection path was confirmed during
        the investigation, so other rejection reasons (e.g. the recipient's
        receive-messages setting) may surface as a plain
        WikidotStatusCodeException instead of ForbiddenException. Treat "no
        exception raised" as "allowed".

        Parameters
        ----------
        client : Client
            Client instance
        user : AbstractUser
            Prospective recipient

        Raises
        ------
        LoginRequiredException
            If not logged in
        ForbiddenException
            If sending is not allowed
        WikidotStatusCodeException
            If sending is not allowed for a reason other than no_permission
        """
        client.amc_client.request(
            [
                {
                    "action": "DashboardMessageAction",
                    "event": "checkCan",
                    "userId": user.id,
                    "moduleName": "Empty",
                }
            ]
        )

    @staticmethod
    @login_required
    def preview(client: "Client", subject: str, body: str, recipient: Optional["User"] = None) -> str:
        """
        Render a preview of a private message without sending it

        Wraps the `dashboard/messages/DMPreviewModule` module.

        Parameters
        ----------
        client : Client
            Client instance
        subject : str
            Message subject
        body : str
            Message body
        recipient : User | None, default None
            Intended recipient

        Returns
        -------
        str
            Rendered HTML preview

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        response = client.amc_client.request(
            [
                {
                    "moduleName": "dashboard/messages/DMPreviewModule",
                    "source": body,
                    "subject": subject,
                    **omit_falsy(to_user_id=recipient.id if recipient is not None else False),
                }
            ]
        )[0]
        return require_body(response, "dashboard/messages/DMPreviewModule")

    @staticmethod
    @login_required
    def fetch_reply_form_html(client: "Client", reply_message_id: int) -> str:
        """
        Fetch the pre-filled "new message" form HTML for replying to a message

        Wraps the `dashboard/messages/DMNewMessageModule` module with
        `replyMessageId` set, which renders the form with the original
        sender pre-filled as recipient (`toUserId`/`toUserName` in the
        rendered HTML). Returns the raw body since the investigation
        captured the request/response shape but not the specific markup
        used to extract those pre-filled values.

        Parameters
        ----------
        client : Client
            Client instance
        reply_message_id : int
            ID of the message being replied to

        Returns
        -------
        str
            Raw rendered HTML body

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        response = client.amc_client.request(
            [{"moduleName": "dashboard/messages/DMNewMessageModule", "replyMessageId": reply_message_id}]
        )[0]
        return require_body(response, "dashboard/messages/DMNewMessageModule")

    def mark_as_read(self) -> None:
        """
        Mark this message as read

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        PrivateMessageCollection.mark_as_read(self.client, [self.id])

    def mark_as_unread(self) -> None:
        """
        Mark this message as unread

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        PrivateMessageCollection.mark_as_unread(self.client, [self.id])

    def delete(self) -> None:
        """
        Delete this message

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        PrivateMessageCollection.remove_messages(self.client, [self.id])


# ----------------------------------------------------------------------
# Site invitations / applications / contacts (/account/messages tabs)
#
# These represent the account's own outgoing/incoming relationships to
# sites and other users, rendered by dashboard/messages/DM*Module. Row
# markup for DMApplicationsModule/DMContactsModule was measured 2026-07-29
# and is parsed into SiteJoinApplication/Contact below (DMApplicationsModule
# rows follow the same tr.message[data-href] pattern as inbox/sent). Row
# markup for DMInvitationsModule was not captured (no invitations existed on
# the investigation account), so its listing function still returns raw
# rendered HTML.
# ----------------------------------------------------------------------


@login_required
def get_invitations_html(client: "Client", page: int = 1) -> str:
    """
    Fetch a page of the account's pending site invitations (raw HTML)

    Wraps `dashboard/messages/DMInvitationsModule`.

    Parameters
    ----------
    client : Client
        Client instance
    page : int, default 1
        Page number

    Returns
    -------
    str
        Raw rendered HTML body

    Raises
    ------
    LoginRequiredException
        If not logged in
    """
    response = client.amc_client.request([{"moduleName": "dashboard/messages/DMInvitationsModule", "page": page}])[0]
    return require_body(response, "dashboard/messages/DMInvitationsModule")


@login_required
def get_invitation_detail_html(client: "Client", item: int) -> str:
    """
    Fetch the detail HTML of a single site invitation

    Wraps `dashboard/messages/DMViewInvitationModule`.

    Parameters
    ----------
    client : Client
        Client instance
    item : int
        Invitation ID

    Returns
    -------
    str
        Raw rendered HTML body

    Raises
    ------
    LoginRequiredException
        If not logged in
    """
    response = client.amc_client.request([{"moduleName": "dashboard/messages/DMViewInvitationModule", "item": item}])[0]
    return require_body(response, "dashboard/messages/DMViewInvitationModule")


@dataclass
class SiteJoinApplication:
    """
    A row of the account's own outgoing site-join applications
    (dashboard/messages/DMApplicationsModule)

    Distinct from SiteApplication (site_application.py), which is a site
    admin's view of incoming applications to their own site.

    Row markup was measured 2026-07-29 (see `70_account.md` "一覧モジュールの
    行マークアップ" / "行の属性"): each row is `tr.message` with
    `data-href="#/applications/<item_id>"` (the same pattern as the inbox/sent
    `tr.message[data-href]`), plus `span.from` / `span.subject` /
    `span.preview` / `span.date > span.odate`. The row does not carry a
    site_id, so this object cannot drive
    `DashboardSitesAction/removeApplication` (which takes a site_id, not this
    item_id) directly; use `ClientSiteAccessor.remove_application(site_id)`
    with a site_id obtained elsewhere if you need to withdraw an application.
    Extracting a site_id from `DMViewApplicationModule`'s response was not
    attempted since that response's structure is unmeasured.

    Attributes
    ----------
    client : Client
        Client instance
    item_id : int
        Application ID (tail of `tr.message`'s data-href), usable as the
        `item` parameter of `DMViewApplicationModule`
    from_site : str
        Text of span.from (the site the application was submitted to)
    subject : str
        Text of span.subject
    preview : str
        Text of span.preview
    submitted_at : datetime
        Submission date and time (span.date > span.odate)
    """

    client: "Client"
    item_id: int
    from_site: str
    subject: str
    preview: str
    submitted_at: datetime

    def __str__(self) -> str:
        """
        String representation of the object

        Returns
        -------
        str
            String representation of the application
        """
        return f"SiteJoinApplication(item_id={self.item_id}, from_site={self.from_site}, subject={self.subject})"

    def fetch_detail_html(self) -> str:
        """
        Fetch the detail HTML of this application (DMViewApplicationModule)

        Returns
        -------
        str
            Raw rendered HTML body

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        return get_application_detail_html(self.client, self.item_id)

    @staticmethod
    def _parse_row(client: "Client", row: Tag) -> "SiteJoinApplication | None":
        """
        Internal method to parse a single DMApplicationsModule row

        Parameters
        ----------
        client : Client
            Client instance
        row : bs4.Tag
            `tr.message` element to parse

        Returns
        -------
        SiteJoinApplication | None
            Parsed row, or None if a required element is missing
        """
        data_href = row.get("data-href")
        from_elem = row.select_one("span.from")
        if data_href is None or from_elem is None:
            return None

        item_id_text = str(data_href).split("/")[-1]
        if not item_id_text.isdigit():
            return None

        subject_elem = row.select_one("span.subject")
        preview_elem = row.select_one("span.preview")
        odate_elem = row.select_one("span.date span.odate")

        return SiteJoinApplication(
            client=client,
            item_id=int(item_id_text),
            from_site=from_elem.get_text().strip(),
            subject=subject_elem.get_text().strip() if subject_elem else "",
            preview=preview_elem.get_text().strip() if preview_elem else "",
            submitted_at=(odate_parser(odate_elem) if odate_elem else datetime.fromtimestamp(0)),
        )


@login_required
def get_applications(client: "Client") -> list["SiteJoinApplication"]:
    """
    Get all of the account's pending outgoing site join applications

    Wraps `dashboard/messages/DMApplicationsModule`, fetching all pages.

    Parameters
    ----------
    client : Client
        Client instance

    Returns
    -------
    list[SiteJoinApplication]
        All pending applications

    Raises
    ------
    LoginRequiredException
        If not logged in
    """
    module_name = "dashboard/messages/DMApplicationsModule"
    first_response = client.amc_client.request([{"moduleName": module_name}])[0]
    first_html = BeautifulSoup(require_body(first_response, module_name), "lxml")

    pager: ResultSet[Tag] = first_html.select("div.pager span.target")
    max_page: int = int(pager[-2].get_text()) if len(pager) > 2 else 1

    applications: list[SiteJoinApplication] = []
    for row in first_html.select("tr.message"):
        application = SiteJoinApplication._parse_row(client, row)
        if application is not None:
            applications.append(application)

    if max_page > 1:
        bodies = [{"page": page, "moduleName": module_name} for page in range(2, max_page + 1)]
        for response in client.amc_client.request(bodies):
            html = BeautifulSoup(require_body(response, module_name), "lxml")
            for row in html.select("tr.message"):
                application = SiteJoinApplication._parse_row(client, row)
                if application is not None:
                    applications.append(application)

    return applications


@login_required
def get_application_detail_html(client: "Client", item: int) -> str:
    """
    Fetch the detail HTML of a single site join application

    Wraps `dashboard/messages/DMViewApplicationModule`.

    Parameters
    ----------
    client : Client
        Client instance
    item : int
        Application ID

    Returns
    -------
    str
        Raw rendered HTML body

    Raises
    ------
    LoginRequiredException
        If not logged in
    """
    response = client.amc_client.request([{"moduleName": "dashboard/messages/DMViewApplicationModule", "item": item}])[
        0
    ]
    return require_body(response, "dashboard/messages/DMViewApplicationModule")


@dataclass
class Contact:
    """
    A row of the account's contact list (dashboard/messages/DMContactsModule)

    Row markup was measured 2026-07-29 (see `70_account.md` "一覧モジュールの
    行マークアップ"): each row is a `tr` with
    `td > span.printuser.avatarhover > a > img.small` and a delete button
    (`td > a.awesome.red.small`). The user is parsed via the existing
    printuser parser rather than the delete button, since removal only needs
    the user ID (ContactsAction/removeContact), which the printuser element
    already carries.

    Attributes
    ----------
    client : Client
        Client instance
    user : AbstractUser
        The contact
    """

    client: "Client"
    user: "AbstractUser"

    def __str__(self) -> str:
        """
        String representation of the object

        Returns
        -------
        str
            String representation of the contact
        """
        return f"Contact(user={self.user})"

    def remove(self) -> None:
        """
        Remove this user from the account's contact list

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        remove_contact(self.client, self.user)


@login_required
def get_contacts(client: "Client") -> list["Contact"]:
    """
    Get the account's contact list

    Wraps `dashboard/messages/DMContactsModule` (single request; this module
    is not paginated).

    Parameters
    ----------
    client : Client
        Client instance

    Returns
    -------
    list[Contact]
        All contacts

    Raises
    ------
    LoginRequiredException
        If not logged in
    """
    response = client.amc_client.request([{"moduleName": "dashboard/messages/DMContactsModule"}])[0]
    html = BeautifulSoup(require_body(response, "dashboard/messages/DMContactsModule"), "lxml")

    contacts: list[Contact] = []
    for row in html.select("tr"):
        printuser_elem = row.select_one("span.printuser")
        if printuser_elem is None:
            continue
        contacts.append(Contact(client=client, user=user_parser(client, printuser_elem)))

    return contacts


@login_required
def get_contacts_list_html(client: "Client") -> str:
    """
    Fetch the contact picker used when composing a new message (raw HTML)

    Wraps `dashboard/messages/DMContactsListModule`.

    Parameters
    ----------
    client : Client
        Client instance

    Returns
    -------
    str
        Raw rendered HTML body

    Raises
    ------
    LoginRequiredException
        If not logged in
    """
    response = client.amc_client.request([{"moduleName": "dashboard/messages/DMContactsListModule"}])[0]
    return require_body(response, "dashboard/messages/DMContactsListModule")


@login_required
def add_contact(client: "Client", user: "AbstractUser") -> None:
    """
    Add a user to the account's contact list

    Wraps `ContactsAction/addContact`.

    Parameters
    ----------
    client : Client
        Client instance
    user : AbstractUser
        User to add

    Raises
    ------
    LoginRequiredException
        If not logged in
    """
    client.amc_client.request(
        [{"action": "ContactsAction", "event": "addContact", "userId": user.id, "moduleName": "Empty"}]
    )


@login_required
def remove_contact(client: "Client", user: "AbstractUser") -> None:
    """
    Remove a user from the account's contact list

    Wraps `ContactsAction/removeContact`.

    Parameters
    ----------
    client : Client
        Client instance
    user : AbstractUser
        User to remove

    Raises
    ------
    LoginRequiredException
        If not logged in
    """
    client.amc_client.request(
        [{"action": "ContactsAction", "event": "removeContact", "userId": user.id, "moduleName": "Empty"}]
    )


@login_required
def add_contact_via_profile(client: "Client", user: "AbstractUser") -> str:
    """
    Add a user to the account's contact list from their profile page

    Wraps `userinfo/UserAddToContactsModule`, a second (module-render-as-
    action) path to add a contact distinct from ContactsAction/addContact,
    used from a user's profile ("user:info") page rather than the messages
    dashboard.

    Parameters
    ----------
    client : Client
        Client instance
    user : AbstractUser
        User to add

    Returns
    -------
    str
        Raw rendered HTML body

    Raises
    ------
    LoginRequiredException
        If not logged in
    """
    response = client.amc_client.request([{"moduleName": "userinfo/UserAddToContactsModule", "userId": user.id}])[0]
    return require_body(response, "userinfo/UserAddToContactsModule")
