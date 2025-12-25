from types import TracebackType
from typing import Optional

from ..common import wd_logger
from ..common.exceptions import LoginRequiredException
from ..connector.ajax import AjaxModuleConnectorClient, AjaxModuleConnectorConfig
from .auth import HTTPAuthentication
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
