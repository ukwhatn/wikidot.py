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


class ClientUserMethods:
    """
    ユーザー関連の操作を提供するクラス

    クライアントインスタンスに関連付けられ、Wikidotユーザーの取得や操作を行うメソッドを提供する。
    Client.userプロパティを通じてアクセスする。
    """

    def __init__(self, client: "Client"):
        """
        初期化メソッド

        Parameters
        ----------
        client : Client
            親クライアントインスタンス
        """
        self.client = client

    def get(self, name: str, raise_when_not_found: bool = False) -> "AbstractUser":
        """
        ユーザー名からユーザーオブジェクトを取得する

        Parameters
        ----------
        name : str
            ユーザー名
        raise_when_not_found : bool, default False
            ユーザーが見つからない場合に例外を送出するかどうか (True: 送出する, False: 送出しない)
            デフォルトでは送出せずにNoneを返す

        Returns
        -------
        AbstractUser
            ユーザーオブジェクト
        """
        return User.from_name(self.client, name, raise_when_not_found)

    def get_bulk(self, names: list[str], raise_when_not_found: bool = False) -> UserCollection:
        """
        複数のユーザー名からユーザーオブジェクトのコレクションを取得する

        Parameters
        ----------
        names : list[str]
            ユーザー名のリスト
        raise_when_not_found : bool, default False
            ユーザーが見つからない場合に例外を送出するかどうか (True: 送出する, False: 送出しない)
            デフォルトでは送出せずにNoneを返す

        Returns
        -------
        UserCollection
            ユーザーオブジェクトのコレクション
        """
        return UserCollection.from_names(self.client, names, raise_when_not_found)


class ClientPrivateMessageMethods:
    """
    プライベートメッセージ関連の操作を提供するクラス

    クライアントインスタンスに関連付けられ、Wikidotプライベートメッセージの送信や取得を行うメソッドを提供する。
    Client.private_messageプロパティを通じてアクセスする。
    """

    def __init__(self, client: "Client"):
        """
        初期化メソッド

        Parameters
        ----------
        client : Client
            親クライアントインスタンス
        """
        self.client = client

    def send(self, recipient: User, subject: str, body: str) -> None:
        """
        プライベートメッセージを送信する

        Parameters
        ----------
        recipient : User
            受信者
        subject : str
            件名
        body : str
            本文
        """
        PrivateMessage.send(self.client, recipient, subject, body)

    @property
    def inbox(self) -> PrivateMessageInbox:
        """
        受信箱を取得する

        Returns
        -------
        PrivateMessageInbox
            受信箱オブジェクト
        """
        return PrivateMessageInbox.acquire(self.client)

    @property
    def sentbox(self) -> PrivateMessageSentBox:
        """
        送信箱を取得する

        Returns
        -------
        PrivateMessageSentBox
            送信箱オブジェクト
        """
        return PrivateMessageSentBox.acquire(self.client)

    def get_messages(self, message_ids: list[int]) -> PrivateMessageCollection:
        """
        複数のメッセージIDからメッセージのコレクションを取得する

        Parameters
        ----------
        message_ids : list[int]
            メッセージIDのリスト

        Returns
        -------
        PrivateMessageCollection
            メッセージのコレクション
        """
        return PrivateMessageCollection.from_ids(self.client, message_ids)

    def get_message(self, message_id: int) -> PrivateMessage:
        """
        メッセージIDからメッセージを取得する

        Parameters
        ----------
        message_id : int
            メッセージID

        Returns
        -------
        PrivateMessage
            メッセージオブジェクト
        """
        return PrivateMessage.from_id(self.client, message_id)


class ClientSiteMethods:
    """
    サイト関連の操作を提供するクラス

    クライアントインスタンスに関連付けられ、Wikidotサイトの取得や操作を行うメソッドを提供する。
    Client.siteプロパティを通じてアクセスする。
    """

    def __init__(self, client: "Client"):
        """
        初期化メソッド

        Parameters
        ----------
        client : Client
            親クライアントインスタンス
        """
        self.client = client

    def get(self, unix_name: str) -> "Site":
        """
        UNIX名からサイトオブジェクトを取得する

        Parameters
        ----------
        unix_name : str
            サイトのUNIX名（例: 'fondation'）

        Returns
        -------
        Site
            サイトオブジェクト
        """
        return Site.from_unix_name(self.client, unix_name)


class Client:
    """
    Wikidot APIへの接続とインタラクションを管理する基幹クライアント

    このクラスは、Wikidot APIとの全てのインタラクションの基盤となる。
    ユーザー認証、サイト操作、ページ管理などすべての機能はこのクライアントを通じて提供される。
    """

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        amc_config: AjaxModuleConnectorConfig | None = None,
        logging_level: str = "WARNING",
    ):
        """
        クライアントの初期化とオプションでの認証を行う

        Parameters
        ----------
        username : str | None, default None
            ユーザー名。設定すると認証試行を行う
        password : str | None, default None
            パスワード。設定すると認証試行を行う
        amc_config : AjaxModuleConnectorConfig | None, default None
            AjaxModuleConnectorの設定
        logging_level : str, default "WARNING"
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
            self.me = User.from_name(self, username)

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
        """
        デストラクタ - クライアントの使用終了時の後処理

        ログイン中であればログアウト処理を行い、リソースを解放する。
        """
        if self.is_logged_in:
            HTTPAuthentication.logout(self)
            self.is_logged_in = False
            self.username = None
        del self

    def __enter__(self):
        """
        コンテキストマネージャプロトコルのエントリーポイント

        with文でクライアントを使用する際に呼び出される。

        Returns
        -------
        Client
            自身のインスタンス
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        コンテキストマネージャプロトコルの終了処理

        with文の終了時に呼び出され、自動的にログアウト処理を行う。

        Parameters
        ----------
        exc_type : type
            発生した例外の型
        exc_value : Exception
            発生した例外
        traceback : traceback
            例外のトレースバック
        """
        self.__del__()
        return

    def __str__(self):
        """
        オブジェクトの文字列表現

        Returns
        -------
        str
            クライアントの文字列表現
        """
        return f"Client(username={self.username}, is_logged_in={self.is_logged_in})"

    def login_check(self) -> None:
        """
        ログイン状態の確認

        ログインが必要な操作を実行する前に呼び出される。
        ログインしていない場合は例外を送出する。

        Raises
        ------
        LoginRequiredException
            ログインしていない場合
        """
        if not self.is_logged_in:
            raise LoginRequiredException("Login is required to execute this function")
        return
