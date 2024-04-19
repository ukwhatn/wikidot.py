from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

from wikidot.common.exceptions import NotFoundException
from wikidot.util.requestutil import RequestUtil
from wikidot.util.stringutil import StringUtil

if TYPE_CHECKING:
    from wikidot.module.client import Client


class UserCollection(list["AbstractUser"]):
    """ユーザーオブジェクトのリスト"""

    def __iter__(self) -> Iterator["AbstractUser"]:
        return super().__iter__()

    @staticmethod
    def from_names(
        client: "Client", names: list[str], raise_when_not_found: bool = False
    ) -> "UserCollection":
        """ユーザー名のリストからユーザーオブジェクトのリストを取得する

        Parameters
        ----------
        client: Client
            クライアント
        names: list[str]
            ユーザー名のリスト
        raise_when_not_found: bool
            ユーザーが見つからない場合に例外を送出するかどうか (True: 送出する, False: 送出しない)
            デフォルトでは送出しない

        Returns
        -------
        UserCollection
            ユーザーオブジェクトのリスト
        """
        responses = RequestUtil.request(
            client,
            "GET",
            [
                f"https://www.wikidot.com/user:info/{StringUtil.to_unix(name)}"
                for name in names
            ],
        )

        users: list[AbstractUser] = []

        for response in responses:
            if isinstance(response, Exception):
                raise response

            html = BeautifulSoup(response.text, "lxml")

            # 存在チェック
            if html.select_one("div.error-block"):
                if raise_when_not_found:
                    raise NotFoundException(f"User not found: {response.url}")
                else:
                    continue

            # id取得
            user_id = int(
                html.select_one("a.btn.btn-default.btn-xs")["href"].split("/")[-1]
            )

            # name取得
            name = html.select_one("h1.profile-title").get_text(strip=True)

            # avatar_url取得
            avatar_url = f"https://www.wikidot.com/avatar.php?userid={user_id}"

            users.append(
                User(
                    client=client,
                    id=user_id,
                    name=name,
                    unix_name=StringUtil.to_unix(name),
                    avatar_url=avatar_url,
                )
            )

        return UserCollection(users)


@dataclass
class AbstractUser:
    """ユーザーオブジェクトの抽象クラス

    Attributes
    ----------
    client: Client
        クライアントクラスのインスタンス
    id: int | None
        ユーザーID
    name: str | None
        ユーザー名
    unix_name: str | None
        ユーザーのUNIX名
    avatar_url: str | None
        ユーザーアバターのURL
    ip: str | None
        ユーザーのIPアドレス
    """

    client: "Client"
    id: int | None = None
    name: str | None = None
    unix_name: str | None = None
    avatar_url: str | None = None
    ip: str | None = None

    def __str__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name}, unix_name={self.unix_name})"


@dataclass
class User(AbstractUser):
    """一般のユーザーオブジェクト

    Attributes
    ----------
    client: Client
        クライアントクラスのインスタンス
    id: int | None
        ユーザーID
    name: str | None
        ユーザー名
    unix_name: str | None
        ユーザーのUNIX名
    avatar_url: str | None
        ユーザーアバターのURL
    ip: None
        ユーザーのIPアドレス（取得できないためNone）
    """

    # client: 'Client'
    # id: int | None
    # name: str | None
    # unix_name: str | None
    # avatar_url: str | None
    ip: None = None

    @staticmethod
    def from_name(
        client: "Client", name: str, raise_when_not_found: bool = False
    ) -> "User":
        """ユーザー名からユーザーオブジェクトを取得する

        Parameters
        ----------
        client: Client
            クライアント
        name: str
            ユーザー名
        raise_when_not_found: bool
            ユーザーが見つからない場合に例外を送出するかどうか (True: 送出する, False: 送出しない)
            デフォルトでは送出しない

        Returns
        -------
        User
            ユーザーオブジェクト
        """
        return UserCollection.from_names(client, [name], raise_when_not_found)[0]


@dataclass
class DeletedUser(AbstractUser):
    """削除されたユーザーオブジェクト

    Attributes
    ----------
    client: Client
        クライアントクラスのインスタンス
    id: int | None
        ユーザーID
    name: str
        ユーザー名（削除されたため"account deleted"）
    unix_name: str
        ユーザーのUNIX名（削除されたため"account_deleted"）
    avatar_url: None
        ユーザーアバターのURL（削除されたためNone）
    ip: None
        ユーザーのIPアドレス（取得できないためNone）
    """

    # client: 'Client'
    # id: int | None
    name: str = "account deleted"
    unix_name: str = "account_deleted"
    avatar_url: None = None
    ip: None = None


@dataclass
class AnonymousUser(AbstractUser):
    """匿名ユーザーオブジェクト

    Attributes
    ----------
    client: Client
        クライアントクラスのインスタンス
    id: None
        ユーザーID（匿名ユーザーのためNone）
    name: str
        ユーザー名（匿名ユーザーのため"Anonymous"）
    unix_name: str
        ユーザーのUNIX名（匿名ユーザーのため"anonymous"）
    avatar_url: None
        ユーザーアバターのURL（匿名ユーザーのためNone）
    ip: str
        ユーザーのIPアドレス
    """

    # client: 'Client'
    id: None = None
    name: str = "Anonymous"
    unix_name: str = "anonymous"
    avatar_url: None = None
    # ip: None = None


@dataclass
class GuestUser(AbstractUser):
    """ゲストユーザーオブジェクト

    Attributes
    ----------
    client: Client
        クライアントクラスのインスタンス
    id: None
        ユーザーID（ゲストユーザーのためNone）
    name: str
        ユーザー名
    unix_name: None
        ユーザーのUNIX名（ゲストユーザーのためNone）
    avatar_url: None
        ユーザーアバターのURL（ゲストユーザーのためNone）
    ip: None
        ユーザーのIPアドレス（取得できないためNone）
    """

    # client: 'Client'
    id: None = None
    # name: str | None
    unix_name: None = None
    avatar_url: None = None
    ip: None = None


@dataclass
class WikidotUser(AbstractUser):
    """Wikidotシステムユーザーオブジェクト

    Attributes
    ----------
    client: Client
        クライアントクラスのインスタンス
    id: None
        ユーザーID（WikidotシステムユーザーのためNone）
    name: str
        ユーザー名（Wikidotシステムユーザーのため"Wikidot"）
    unix_name: str
        ユーザーのUNIX名（Wikidotシステムユーザーのため"wikidot"）
    avatar_url: None
        ユーザーアバターのURL（WikidotシステムユーザーのためNone）
    ip: None
        ユーザーのIPアドレス（取得できないためNone）
    """

    # client: 'Client'
    id: None = None
    name: str = "Wikidot"
    unix_name: str = "wikidot"
    avatar_url: None = None
    ip: None = None
