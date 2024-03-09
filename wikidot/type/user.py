from dataclasses import dataclass


@dataclass
class AbstractUser:
    """ユーザーオブジェクトの抽象クラス

    Attributes
    ----------
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
    id: int | None = None
    name: str | None = None
    unix_name: str | None = None
    avatar_url: str | None = None
    ip: str | None = None


@dataclass
class User(AbstractUser):
    """一般のユーザーオブジェクト

    Attributes
    ----------
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
    # id: int | None
    # name: str | None
    # unix_name: str | None
    # avatar_url: str | None
    ip: None = None


@dataclass
class DeletedUser(AbstractUser):
    """削除されたユーザーオブジェクト

    Attributes
    ----------
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
    id: None = None
    name: str = "Wikidot"
    unix_name: str = "wikidot"
    avatar_url: None = None
    ip: None = None
