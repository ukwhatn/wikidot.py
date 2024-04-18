from wikidot.common import wd_logger
from wikidot.common.exceptions import LoginRequiredException
from wikidot.connector.ajax import AjaxModuleConnectorClient, AjaxModuleConnectorConfig
from wikidot.module.auth import HTTPAuthentication
from wikidot.module.private_message import (
    PrivateMessage,
    PrivateMessageCollection,
    PrivateMessageInbox,
    PrivateMessageSentBox,
)
from wikidot.module.site import Site
from wikidot.module.user import User, UserCollection


class ClientUserMethods:
    def __init__(self, client: "Client"):
        self.client = client

    def get(self, name: str, raise_when_not_found: bool = False) -> User:
        """ユーザー名からユーザーオブジェクトを取得する

        Parameters
        ----------
        name: str
            ユーザー名

        raise_when_not_found: bool
            ユーザーが見つからない場合に例外を送出するかどうか (True: 送出する, False: 送出しない)
            デフォルトでは送出せずにNoneを返す

        Returns
        -------
        User
            ユーザーオブジェクト
        """
        return User.from_name(self.client, name, raise_when_not_found)

    def get_bulk(
        self, names: list[str], raise_when_not_found: bool = False
    ) -> list[User]:
        """ユーザー名からユーザーオブジェクトを取得する

        Parameters
        ----------
        names: list[str]
            ユーザー名のリスト
        raise_when_not_found: bool
            ユーザーが見つからない場合に例外を送出するかどうか (True: 送出する, False: 送出しない)
            デフォルトでは送出せずにNoneを返す

        Returns
        -------
        list[User]
            ユーザーオブジェクトのリスト
        """
        return UserCollection.from_names(self.client, names, raise_when_not_found)


class ClientPrivateMessageMethods:
    def __init__(self, client: "Client"):
        self.client = client

    def send(self, recipient: User, subject: str, body: str) -> None:
        """メッセージを送信する

        Parameters
        ----------
        recipient: User
            受信者
        subject: str
            件名
        body: str
            本文
        """
        PrivateMessage.send(self.client, recipient, subject, body)

    def get_inbox(self) -> PrivateMessageInbox:
        """受信箱を取得する

        Returns
        -------
        PrivateMessageInbox
            受信箱
        """
        return PrivateMessageInbox.acquire(self.client)

    def get_sentbox(self) -> PrivateMessageSentBox:
        """送信箱を取得する

        Returns
        -------
        PrivateMessageSentBox
            送信箱
        """
        return PrivateMessageSentBox.acquire(self.client)

    def get_messages(self, message_ids: list[int]) -> PrivateMessageCollection:
        """メッセージを取得する

        Parameters
        ----------
        message_ids: list[int]
            メッセージIDのリスト

        Returns
        -------
        list[PrivateMessage]
            メッセージのリスト
        """
        return PrivateMessageCollection.from_ids(self.client, message_ids)

    def get_message(self, message_id: int) -> PrivateMessage:
        """メッセージを取得する

        Parameters
        ----------
        message_id: int
            メッセージID

        Returns
        -------
        PrivateMessage
            メッセージ
        """
        return PrivateMessage.from_id(self.client, message_id)


class ClientSiteMethods:
    def __init__(self, client: "Client"):
        self.client = client

    def get(self, unix_name: str) -> "Site":
        """UNIX名からサイトオブジェクトを取得する

        Parameters
        ----------
        unix_name: str
            サイトのUNIX名

        Returns
        -------
        Site
            サイトオブジェクト
        """
        return Site.from_unix_name(self.client, unix_name)


class Client:
    """基幹クライアント"""

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        amc_config: AjaxModuleConnectorConfig | None = None,
        logging_level: str = "WARNING",
    ):
        """Wikidot Client

        Parameters
        ----------
        username: str | None
            ユーザー名
        password: str | None
            パスワード
        amc_config: dict | None
            AMCの設定
        logging_level: str
            ロギングレベル
        """
        # 最初にロギングレベルを決定する
        wd_logger.setLevel(logging_level)

        # AMCClientを初期化
        self.amc_client = AjaxModuleConnectorClient(site_name=None, config=amc_config)

        # セッション関連変数の初期化
        self.is_logged_in = False
        self.username = None

        # usernameとpasswordが指定されていればログインする
        if username is not None and password is not None:
            HTTPAuthentication.login(self, username, password)
            self.is_logged_in = True
            self.username = username

        # ----------
        # 以下メソッド
        # ----------

        self.user = ClientUserMethods(self)
        self.private_message = ClientPrivateMessageMethods(self)
        self.site = ClientSiteMethods(self)

        # ------------
        # メソッド終わり
        # ------------

    def __del__(self):
        """デストラクタ"""
        if self.is_logged_in:
            HTTPAuthentication.logout(self)
            self.is_logged_in = False
            self.username = None
        del self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.__del__()
        return

    def __str__(self):
        return f"Client(username={self.username}, is_logged_in={self.is_logged_in})"

    def login_check(self) -> None:
        if not self.is_logged_in:
            raise LoginRequiredException("Login is required to execute this function")
        return
