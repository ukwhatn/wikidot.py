from wikidot.common import wd_logger
from wikidot.connector.ajax import AjaxModuleConnectorClient, AjaxModuleConnectorConfig
from wikidot.module.auth import HTTPAuthentication


class Client:
    """基幹クライアント"""

    def __init__(
            self,
            username: str | None = None,
            password: str | None = None,
            amc_config: AjaxModuleConnectorConfig | None = None,
            logging_level: str = "INFO"
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
