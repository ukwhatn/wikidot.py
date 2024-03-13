from wikidot.common import wd_logger
from wikidot.connector.ajax import AjaxModuleConnectorClient, AjaxModuleConnectorConfig
from wikidot.module.auth import HTTPAuthentication
from wikidot.module.private_message import PrivateMessage, PrivateMessageInbox, \
    PrivateMessageSentBox, PrivateMessageCollection
from wikidot.module.user import User, UserCollection


class Client:
    """基幹クライアント"""

    def __init__(
            self,
            username: str | None = None,
            password: str | None = None,
            amc_config: AjaxModuleConnectorConfig | None = None,
            logging_level: str = "WARNING"
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
        self.amc_client = AjaxModuleConnectorClient(
            site_name=None,
            config=amc_config
        )

        # セッション関連変数の初期化
        self.is_logged_in = False
        self.username = None

        # usernameとpasswordが指定されていればログインする
        if username is not None and password is not None:
            HTTPAuthentication.login(self, username, password)
            self.is_logged_in = True
            self.username = username

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

    # ------------------------------
    # User
    # ------------------------------

    def find_user(
            self,
            name: str,
            raise_when_not_found: bool = False
    ) -> User:
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
        return User.from_name(self, name, raise_when_not_found)

    def find_users(
            self,
            names: list[str],
            raise_when_not_found: bool = False
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
        return UserCollection.from_names(self, names, raise_when_not_found)

    # ------------------------------
    # PrivateMessage
    # ------------------------------

    def send_private_message(
            self,
            recipient: User,
            subject: str,
            body: str
    ) -> None:
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
        PrivateMessage.send(self, recipient, subject, body)

    def get_private_message_inbox(self) -> PrivateMessageInbox:
        """受信箱を取得する

        Returns
        -------
        PrivateMessageInbox
            受信箱
        """
        return PrivateMessageInbox.acquire(self)

    def get_private_message_sentbox(self) -> PrivateMessageSentBox:
        """送信箱を取得する

        Returns
        -------
        PrivateMessageSentBox
            送信箱
        """
        return PrivateMessageSentBox.acquire(self)

    def get_private_messages(self, message_ids: list[int]) -> PrivateMessageCollection:
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
        return PrivateMessageCollection.from_ids(self, message_ids)

    def get_private_message(self, message_id: int) -> PrivateMessage:
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
        return PrivateMessage.from_id(self, message_id)
