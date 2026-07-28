from types import TracebackType
from typing import Any, Optional

from ..common import wd_logger
from ..common.exceptions import LoginRequiredException
from ..connector.ajax import AjaxModuleConnectorClient, AjaxModuleConnectorConfig
from . import private_message as pm
from .account import ClientAccountAccessor
from .auth import HTTPAuthentication
from .dashboard_site import DashboardSite, DashboardSites, NewSitePrivacy, NewSiteTemplate
from .private_message import (
    PrivateMessage,
    PrivateMessageCollection,
    PrivateMessageInbox,
    PrivateMessageSentBox,
)
from .site import Site
from .user import AbstractUser, User, UserCollection


class ClientUserAccessor:
    """
    A class that provides user-related operations

    Associated with a client instance, provides methods for retrieving and manipulating Wikidot users.
    Access through the Client.user property.
    """

    def __init__(self, client: "Client"):
        """
        Initialize method

        Parameters
        ----------
        client : Client
            Parent client instance
        """
        self.client = client

    def get(self, name: str, raise_when_not_found: bool = False) -> Optional["AbstractUser"]:
        """
        Get a user object from a username

        Parameters
        ----------
        name : str
            Username
        raise_when_not_found : bool, default False
            Whether to raise an exception when a user is not found (True: raise, False: do not raise)
            By default, returns None without raising

        Returns
        -------
        AbstractUser
            User object
        """
        return User.from_name(self.client, name, raise_when_not_found)

    def get_bulk(self, names: list[str], raise_when_not_found: bool = False) -> UserCollection:
        """
        Get a collection of user objects from multiple usernames

        Parameters
        ----------
        names : list[str]
            List of usernames
        raise_when_not_found : bool, default False
            Whether to raise an exception when a user is not found (True: raise, False: do not raise)
            By default, returns None without raising

        Returns
        -------
        UserCollection
            Collection of user objects
        """
        return UserCollection.from_names(self.client, names, raise_when_not_found)


class ClientPrivateMessageAccessor:
    """
    A class that provides private message-related operations

    Associated with a client instance, provides methods for sending and retrieving Wikidot private messages.
    Access through the Client.private_message property.
    """

    def __init__(self, client: "Client"):
        """
        Initialize method

        Parameters
        ----------
        client : Client
            Parent client instance
        """
        self.client = client

    def send(self, recipient: User, subject: str, body: str) -> None:
        """
        Send a private message

        Parameters
        ----------
        recipient : User
            Recipient
        subject : str
            Subject
        body : str
            Message body
        """
        PrivateMessage.send(self.client, recipient, subject, body)

    @property
    def inbox(self) -> PrivateMessageInbox:
        """
        Get the inbox

        Returns
        -------
        PrivateMessageInbox
            Inbox object
        """
        return PrivateMessageInbox.acquire(self.client)

    @property
    def sentbox(self) -> PrivateMessageSentBox:
        """
        Get the sent box

        Returns
        -------
        PrivateMessageSentBox
            Sent box object
        """
        return PrivateMessageSentBox.acquire(self.client)

    def get_messages(self, message_ids: list[int]) -> PrivateMessageCollection:
        """
        Get a collection of messages from multiple message IDs

        Parameters
        ----------
        message_ids : list[int]
            List of message IDs

        Returns
        -------
        PrivateMessageCollection
            Collection of messages
        """
        return PrivateMessageCollection.from_ids(self.client, message_ids)

    def get_message(self, message_id: int) -> PrivateMessage:
        """
        Get a message from a message ID

        Parameters
        ----------
        message_id : int
            Message ID

        Returns
        -------
        PrivateMessage
            Message object
        """
        return PrivateMessage.from_id(self.client, message_id)

    def mark_as_read(self, message_ids: list[int]) -> None:
        """
        Mark messages as read

        Parameters
        ----------
        message_ids : list[int]
            IDs of the messages to mark as read
        """
        PrivateMessageCollection.mark_as_read(self.client, message_ids)

    def mark_as_unread(self, message_ids: list[int]) -> None:
        """
        Mark messages as unread

        Parameters
        ----------
        message_ids : list[int]
            IDs of the messages to mark as unread
        """
        PrivateMessageCollection.mark_as_unread(self.client, message_ids)

    def remove(self, message_ids: list[int]) -> None:
        """
        Delete messages

        Parameters
        ----------
        message_ids : list[int]
            IDs of the messages to delete
        """
        PrivateMessageCollection.remove_messages(self.client, message_ids)

    def save_draft(self, subject: str, body: str, recipient: Optional["User"] = None) -> None:
        """
        Save a private message draft

        Parameters
        ----------
        subject : str
            Draft subject
        body : str
            Draft body
        recipient : User | None, default None
            Intended recipient
        """
        PrivateMessage.save_draft(self.client, subject, body, recipient)

    def check_can_send(self, user: AbstractUser) -> None:
        """
        Check whether the account is allowed to message a user

        Parameters
        ----------
        user : AbstractUser
            Prospective recipient

        Raises
        ------
        ForbiddenException
            If sending is not allowed
        """
        PrivateMessage.check_can_send(self.client, user)

    def preview(self, subject: str, body: str, recipient: Optional["User"] = None) -> str:
        """
        Render a preview of a private message without sending it

        Parameters
        ----------
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
        """
        return PrivateMessage.preview(self.client, subject, body, recipient)

    def fetch_reply_form_html(self, reply_message_id: int) -> str:
        """
        Fetch the pre-filled "new message" form HTML for replying to a message

        Parameters
        ----------
        reply_message_id : int
            ID of the message being replied to

        Returns
        -------
        str
            Raw rendered HTML body
        """
        return PrivateMessage.fetch_reply_form_html(self.client, reply_message_id)

    def get_invitations_html(self, page: int = 1) -> str:
        """
        Fetch a page of the account's pending site invitations (raw HTML)

        Parameters
        ----------
        page : int, default 1
            Page number

        Returns
        -------
        str
            Raw rendered HTML body
        """
        return pm.get_invitations_html(self.client, page)

    def get_invitation_detail_html(self, item: int) -> str:
        """
        Fetch the detail HTML of a single site invitation

        Parameters
        ----------
        item : int
            Invitation ID

        Returns
        -------
        str
            Raw rendered HTML body
        """
        return pm.get_invitation_detail_html(self.client, item)

    def get_applications(self) -> list["pm.SiteJoinApplication"]:
        """
        Get all of the account's pending outgoing site join applications

        Returns
        -------
        list[SiteJoinApplication]
            All pending applications
        """
        return pm.get_applications(self.client)

    def get_application_detail_html(self, item: int) -> str:
        """
        Fetch the detail HTML of a single site join application

        Parameters
        ----------
        item : int
            Application ID

        Returns
        -------
        str
            Raw rendered HTML body
        """
        return pm.get_application_detail_html(self.client, item)

    def get_contacts(self) -> list["pm.Contact"]:
        """
        Get the account's contact list

        Returns
        -------
        list[Contact]
            All contacts
        """
        return pm.get_contacts(self.client)

    def get_contacts_list_html(self) -> str:
        """
        Fetch the contact picker used when composing a new message (raw HTML)

        Returns
        -------
        str
            Raw rendered HTML body
        """
        return pm.get_contacts_list_html(self.client)

    def add_contact(self, user: AbstractUser) -> None:
        """
        Add a user to the account's contact list

        Parameters
        ----------
        user : AbstractUser
            User to add
        """
        pm.add_contact(self.client, user)

    def remove_contact(self, user: AbstractUser) -> None:
        """
        Remove a user from the account's contact list

        Parameters
        ----------
        user : AbstractUser
            User to remove
        """
        pm.remove_contact(self.client, user)

    def add_contact_via_profile(self, user: AbstractUser) -> str:
        """
        Add a user to the account's contact list from their profile page

        Parameters
        ----------
        user : AbstractUser
            User to add

        Returns
        -------
        str
            Raw rendered HTML body
        """
        return pm.add_contact_via_profile(self.client, user)


class ClientSiteAccessor:
    """
    A class that provides site-related operations

    Associated with a client instance, provides methods for retrieving and manipulating Wikidot sites.
    Access through the Client.site property.
    """

    def __init__(self, client: "Client"):
        """
        Initialize method

        Parameters
        ----------
        client : Client
            Parent client instance
        """
        self.client = client

    def get(self, unix_name: str) -> "Site":
        """
        Get a site object from a UNIX name

        Parameters
        ----------
        unix_name : str
            UNIX name of the site (e.g., 'fondation')

        Returns
        -------
        Site
            Site object
        """
        return Site.from_unix_name(self.client, unix_name)

    def create(
        self,
        name: str,
        unixname: str,
        subtitle: str = "",
        language: str = "en",
        template: NewSiteTemplate = "standard-template",
        privacy: NewSitePrivacy = "open",
        tos: bool = True,
    ) -> str:
        """
        Create a new site

        Parameters
        ----------
        name : str
            Site title
        unixname : str
            Site UNIX name (e.g. "foo" -> foo.wikidot.com)
        subtitle : str, default ""
            Site subtitle
        language : str, default "en"
            Site language code
        template : NewSiteTemplate, default "standard-template"
            Starting content template
        privacy : NewSitePrivacy, default "open"
            Site visibility
        tos : bool, default True
            Whether to accept the Terms of Service

        Returns
        -------
        str
            UNIX name of the created site

        Raises
        ------
        FormErrorsException
            If validation fails (e.g. unixname already taken)
        """
        return DashboardSites.create(
            self.client,
            name=name,
            unixname=unixname,
            subtitle=subtitle,
            language=language,
            template=template,
            privacy=privacy,
            tos=tos,
        )

    @property
    def my_sites(self) -> list[DashboardSite]:
        """
        Get every site the account belongs to (all roles) plus deleted sites

        Returns
        -------
        list[DashboardSite]
            All rows of the account's site dashboard
        """
        return DashboardSites.list_sites(self.client)

    def accept_invitation(self, invitation_id: int) -> None:
        """
        Accept a pending site invitation

        Parameters
        ----------
        invitation_id : int
            Invitation ID
        """
        DashboardSites.accept_invitation(self.client, invitation_id)

    def throw_away_invitation(self, invitation_id: int) -> None:
        """
        Discard a pending site invitation without accepting it

        Parameters
        ----------
        invitation_id : int
            Invitation ID
        """
        DashboardSites.throw_away_invitation(self.client, invitation_id)

    def remove_application(self, site_id: int) -> None:
        """
        Withdraw a pending membership application the account submitted to a site

        Parameters
        ----------
        site_id : int
            ID of the site the application was submitted to
        """
        DashboardSites.remove_application(self.client, site_id)

    def restore_site(self, site_id: int, confirm_site_name: str) -> None:
        """
        Restore a deleted site the account administers

        Parameters
        ----------
        site_id : int
            ID of the deleted site
        confirm_site_name : str
            Site name, required as a typed confirmation
        """
        DashboardSites.restore_site(self.client, site_id, confirm_site_name)

    def resign_as_admin(self, site_id: int) -> None:
        """
        Resign the account's admin role on a site

        Parameters
        ----------
        site_id : int
            Site ID
        """
        DashboardSites.resign_as_admin(self.client, site_id)

    def resign_as_moderator(self, site_id: int) -> None:
        """
        Resign the account's moderator role on a site

        Parameters
        ----------
        site_id : int
            Site ID
        """
        DashboardSites.resign_as_moderator(self.client, site_id)

    def sign_off_as_member(self, site_id: int) -> None:
        """
        Leave a site the account is a plain member of

        Parameters
        ----------
        site_id : int
            Site ID
        """
        DashboardSites.sign_off_as_member(self.client, site_id)

    def set_site_storage_limit(self, site_id: int, raw_fields: dict[str, Any]) -> None:
        """
        Set a site's file storage limit

        Unmeasured: the form fields of limit-site-<siteId> could not be
        captured during the investigation (no Pro site available). Pass the
        exact field names/values as sent by the real form.

        Parameters
        ----------
        site_id : int
            Site ID
        raw_fields : dict[str, Any]
            Raw form fields to send as-is
        """
        DashboardSites.set_storage_limit(self.client, site_id, raw_fields)


class Client:
    """
    Core client for managing connections and interactions with the Wikidot API

    This class serves as the foundation for all interactions with the Wikidot API.
    All functionality such as user authentication, site operations, and page management is provided through this client.
    """

    # Accessor属性
    user: "ClientUserAccessor"
    private_message: "ClientPrivateMessageAccessor"
    site: "ClientSiteAccessor"
    account: "ClientAccountAccessor"

    # セッション関連属性
    amc_client: AjaxModuleConnectorClient
    is_logged_in: bool
    username: str | None
    me: Optional["AbstractUser"]

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        amc_config: AjaxModuleConnectorConfig | None = None,
        logging_level: str = "WARNING",
    ):
        """
        Initialize the client and optionally perform authentication

        Parameters
        ----------
        username : str | None, default None
            Username. If provided, authentication will be attempted
        password : str | None, default None
            Password. If provided, authentication will be attempted
        amc_config : AjaxModuleConnectorConfig | None, default None
            AjaxModuleConnector configuration
        logging_level : str, default "WARNING"
            Logging level
        """
        # ロギング設定を行う
        from wikidot.common.logger import setup_console_handler

        setup_console_handler(wd_logger, logging_level)

        # AMCClientを初期化
        self.amc_client = AjaxModuleConnectorClient(site_name=None, config=amc_config)

        # セッション関連変数の初期化
        self.is_logged_in = False
        self.username = None
        self.me = None

        # usernameとpasswordが指定されていればログインする
        if username is not None and password is not None:
            HTTPAuthentication.login(self, username, password)
            self.is_logged_in = True
            self.username = username
            self.me = User.from_name(self, username)

        # ----------
        # 以下メソッド
        # ----------

        self.user = ClientUserAccessor(self)
        self.private_message = ClientPrivateMessageAccessor(self)
        self.site = ClientSiteAccessor(self)
        self.account = ClientAccountAccessor(self)

        # ------------
        # メソッド終わり
        # ------------

    def __enter__(self) -> "Client":
        """
        Context manager protocol entry point

        Called when using the client with a with statement.

        Returns
        -------
        Client
            Self instance
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """
        Context manager protocol exit processing

        Called at the end of a with statement and automatically performs logout processing.

        Parameters
        ----------
        exc_type : type
            Type of exception that occurred
        exc_value : Exception
            Exception that occurred
        traceback : traceback
            Exception traceback
        """
        if self.is_logged_in:
            try:
                HTTPAuthentication.logout(self)
            except Exception as e:
                # ログアウトエラーは記録するが、再度raiseはしない
                wd_logger.warning(f"Error during logout: {e}", exc_info=True)
            finally:
                self.is_logged_in = False
                self.username = None

    def __str__(self) -> str:
        """
        String representation of the object

        Returns
        -------
        str
            String representation of the client
        """
        return f"Client(username={self.username}, is_logged_in={self.is_logged_in})"

    def login_check(self) -> None:
        """
        Check login status

        Called before executing operations that require login.
        Raises an exception if not logged in.

        Raises
        ------
        LoginRequiredException
            When not logged in
        """
        if not self.is_logged_in:
            raise LoginRequiredException("Login is required to execute this function")
        return

    def close(self) -> None:
        """
        Explicitly release client resources

        Performs logout processing if logged in and cleans up associated resources.
        If not using a with statement, explicitly call this method to release resources.

        Examples
        --------
        >>> client = Client(username="user", password="pass")
        >>> try:
        ...     # Some processing
        ...     pass
        ... finally:
        ...     client.close()
        """
        if self.is_logged_in:
            try:
                HTTPAuthentication.logout(self)
            except Exception as e:
                # ログアウトエラーは記録するが、再度raiseはしない
                wd_logger.warning(f"Error during logout: {e}", exc_info=True)
            finally:
                self.is_logged_in = False
                self.username = None
