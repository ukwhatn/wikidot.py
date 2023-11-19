from dataclasses import dataclass


@dataclass
class AbstractUser:
    id: int | None = None
    name: str | None = None
    unix_name: str | None = None
    avatar_url: str | None = None
    ip: str | None = None


@dataclass
class User(AbstractUser):
    # id: int | None
    # name: str | None
    # unix_name: str | None
    # avatar_url: str | None
    ip: None = None


@dataclass
class DeletedUser(AbstractUser):
    # id: int | None
    name: str = "account deleted"
    unix_name: str = "account_deleted"
    avatar_url: None = None
    ip: None = None


@dataclass
class AnonymousUser(AbstractUser):
    id: None = None
    name: str = "Anonymous"
    unix_name: str = "anonymous"
    avatar_url: None = None
    # ip: None = None


@dataclass
class GuestUser(AbstractUser):
    id: None = None
    # name: str | None
    unix_name: None = None
    avatar_url: None = None
    ip: None = None


@dataclass
class WikidotUser(AbstractUser):
    id: None = None
    name: str = "Wikidot"
    unix_name: str = "wikidot"
    avatar_url: None = None
    ip: None = None
