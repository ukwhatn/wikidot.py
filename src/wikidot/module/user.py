from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

from ..common.exceptions import NoElementException, NotFoundException
from ..util.requestutil import RequestUtil
from ..util.stringutil import StringUtil

if TYPE_CHECKING:
    from .client import Client


class UserCollection(list["AbstractUser"]):
    """
    ユーザーオブジェクトのコレクションを表すクラス

    複数のユーザーオブジェクトを格納・操作するためのリスト拡張クラス。
    イテレーション操作やユーザー名からの一括取得などの機能を提供する。
    """

    def __iter__(self) -> Iterator["AbstractUser"]:
        """
        コレクション内のユーザーオブジェクトを順に返すイテレータ

        Returns
        -------
        Iterator[AbstractUser]
            ユーザーオブジェクトのイテレータ
        """
        return super().__iter__()

    @staticmethod
    def from_names(client: "Client", names: list[str], raise_when_not_found: bool = False) -> "UserCollection":
        """
        ユーザー名のリストからユーザーオブジェクトのコレクションを取得する

        Parameters
        ----------
        client : Client
            クライアントインスタンス
        names : list[str]
            検索対象のユーザー名リスト
        raise_when_not_found : bool, default False
            ユーザーが見つからない場合に例外を送出するかどうか (True: 送出する, False: 送出しない)
            デフォルトでは送出せず、該当ユーザーは結果に含めない

        Returns
        -------
        UserCollection
            ユーザーオブジェクトのコレクション

        Raises
        ------
        NotFoundException
            raise_when_not_foundがTrueで、ユーザーが見つからない場合
        NoElementException
            ユーザーページの解析中に必要な要素が見つからない場合
        """
        responses = RequestUtil.request(
            client,
            "GET",
            [f"https://www.wikidot.com/user:info/{StringUtil.to_unix(name)}" for name in names],
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
            user_id_elem = html.select_one("a.btn.btn-default.btn-xs")
            if user_id_elem is None:
                raise NoElementException("User ID element not found")
            user_id = int(str(user_id_elem["href"]).split("/")[-1])

            # name取得
            name_elem = html.select_one("h1.profile-title")
            if name_elem is None:
                raise NoElementException("User name element not found")
            name = name_elem.get_text(strip=True)

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
    """
    ユーザーオブジェクトの抽象基底クラス

    すべてのユーザータイプの共通属性と機能を定義する。
    このクラスを直接インスタンス化せず、派生クラスを使用する。

    Attributes
    ----------
    client : Client
        クライアントインスタンス
    id : int | None
        ユーザーID
    name : str | None
        ユーザー名
    unix_name : str | None
        ユーザーのURLで使用されるUNIX形式の名前
    avatar_url : str | None
        ユーザーアバター画像のURL
    ip : str | None
        ユーザーのIPアドレス（匿名ユーザーの場合のみ設定される）
    """

    client: "Client"
    id: int | None = None
    name: str | None = None
    unix_name: str | None = None
    avatar_url: str | None = None
    ip: str | None = None

    def __str__(self):
        """
        オブジェクトの文字列表現

        Returns
        -------
        str
            ユーザーオブジェクトの文字列表現
        """
        return f"{self.__class__.__name__}(id={self.id}, name={self.name}, unix_name={self.unix_name})"


@dataclass
class User(AbstractUser):
    """
    一般のWikidotユーザーを表すクラス

    登録済みの通常Wikidotユーザーを表現する。ユーザーIDやユーザー名などの基本情報を保持する。

    Attributes
    ----------
    client : Client
        クライアントインスタンス
    id : int | None
        ユーザーID
    name : str | None
        ユーザー名
    unix_name : str | None
        ユーザーのURLで使用されるUNIX形式の名前
    avatar_url : str | None
        ユーザーアバター画像のURL
    ip : None
        ユーザーのIPアドレス（通常ユーザーでは取得できないためNone）
    """

    # client: 'Client'
    # id: int | None
    # name: str | None
    # unix_name: str | None
    # avatar_url: str | None
    ip: str | None = None

    @staticmethod
    def from_name(client: "Client", name: str, raise_when_not_found: bool = False) -> "AbstractUser":
        """
        ユーザー名からユーザーオブジェクトを取得する

        Parameters
        ----------
        client : Client
            クライアントインスタンス
        name : str
            検索対象のユーザー名
        raise_when_not_found : bool, default False
            ユーザーが見つからない場合に例外を送出するかどうか (True: 送出する, False: 送出しない)
            デフォルトでは送出せずにNoneを返す

        Returns
        -------
        AbstractUser
            ユーザーオブジェクト

        Raises
        ------
        NotFoundException
            raise_when_not_foundがTrueで、ユーザーが見つからない場合
        NoElementException
            ユーザーページの解析中に必要な要素が見つからない場合
        IndexError
            ユーザーが見つからない場合（raise_when_not_foundがFalseの場合）
        """
        return UserCollection.from_names(client, [name], raise_when_not_found)[0]


@dataclass
class DeletedUser(AbstractUser):
    """
    削除されたWikidotユーザーを表すクラス

    すでに削除されたユーザーアカウントを表現する。
    削除されたユーザーには固定の「account deleted」という名前が割り当てられる。

    Attributes
    ----------
    client : Client
        クライアントインスタンス
    id : int | None
        ユーザーID
    name : str
        ユーザー名（削除されたため"account deleted"固定）
    unix_name : str
        ユーザーのUNIX名（削除されたため"account_deleted"固定）
    avatar_url : None
        ユーザーアバターのURL（削除されたユーザーのためNone）
    ip : None
        ユーザーのIPアドレス（取得できないためNone）
    """

    id: int | None = None
    name: str | None = "account deleted"
    unix_name: str | None = "account_deleted"
    avatar_url: str | None = None
    ip: str | None = None


@dataclass
class AnonymousUser(AbstractUser):
    """
    匿名（非登録）のWikidotユーザーを表すクラス

    登録せずに投稿した匿名ユーザーを表現する。
    IPアドレスのみを識別情報として持つ。

    Attributes
    ----------
    client : Client
        クライアントインスタンス
    id : None
        ユーザーID（匿名ユーザーのためNone）
    name : str
        ユーザー名（匿名ユーザーのため"Anonymous"固定）
    unix_name : str
        ユーザーのUNIX名（匿名ユーザーのため"anonymous"固定）
    avatar_url : None
        ユーザーアバターのURL（匿名ユーザーのためNone）
    ip : str
        ユーザーのIPアドレス
    """

    id: int | None = None
    name: str | None = "Anonymous"
    unix_name: str | None = "anonymous"
    avatar_url: str | None = None
    ip: str | None = None


@dataclass
class GuestUser(AbstractUser):
    """
    ゲスト投稿したWikidotユーザーを表すクラス

    名前とメールアドレスのみを入力して投稿したゲストユーザーを表現する。
    ユーザー名は任意だが、IDやUNIX名は持たない。

    Attributes
    ----------
    client : Client
        クライアントインスタンス
    id : None
        ユーザーID（ゲストユーザーのためNone）
    name : str | None
        ユーザー名（ゲスト投稿時に指定した名前）
    unix_name : None
        ユーザーのUNIX名（ゲストユーザーのためNone）
    avatar_url : str | None
        ユーザーアバターのURL（Gravatarの場合あり）
    ip : None
        ユーザーのIPアドレス（取得できないためNone）
    """

    id: int | None = None
    name: str | None = None
    unix_name: str | None = None
    avatar_url: str | None = None
    ip: str | None = None


@dataclass
class WikidotUser(AbstractUser):
    """
    Wikidotシステムユーザーを表すクラス

    Wikidotシステムによる自動投稿や通知を表現するための特殊ユーザー。
    "Wikidot"という固定の名前を持つ。

    Attributes
    ----------
    client : Client
        クライアントインスタンス
    id : None
        ユーザーID（システムユーザーのためNone）
    name : str
        ユーザー名（システムユーザーのため"Wikidot"固定）
    unix_name : str
        ユーザーのUNIX名（システムユーザーのため"wikidot"固定）
    avatar_url : None
        ユーザーアバターのURL（システムユーザーのためNone）
    ip : None
        ユーザーのIPアドレス（取得できないためNone）
    """

    id: int | None = None
    name: str | None = "Wikidot"
    unix_name: str | None = "wikidot"
    avatar_url: str | None = None
    ip: str | None = None
