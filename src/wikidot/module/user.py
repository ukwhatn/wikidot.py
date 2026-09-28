from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from bs4 import BeautifulSoup

from ..common.exceptions import NoElementException, NotFoundException
from ..util.requestutil import RequestUtil
from ..util.stringutil import StringUtil
from .user_info import (
    RecentPost,
    UserChange,
    UserProfile,
    UserSiteEntry,
    fetch_user_changes,
    fetch_user_posts,
    fetch_user_profile,
    fetch_user_site_entries,
)

if TYPE_CHECKING:
    from .client import Client


class UserCollection(list["AbstractUser"]):
    """
    A class representing a collection of user objects

    A list extension class for storing and manipulating multiple user objects.
    Provides functionality for iteration operations and bulk retrieval from usernames.
    """

    def __iter__(self) -> Iterator["AbstractUser"]:
        """
        An iterator that returns user objects in the collection sequentially

        Returns
        -------
        Iterator[AbstractUser]
            Iterator of user objects
        """
        return super().__iter__()

    @staticmethod
    def from_names(client: "Client", names: list[str], raise_when_not_found: bool = False) -> "UserCollection":
        """
        Get a collection of user objects from a list of usernames

        Parameters
        ----------
        client : Client
            Client instance
        names : list[str]
            List of usernames to search for
        raise_when_not_found : bool, default False
            Whether to raise an exception when a user is not found (True: raise, False: do not raise)
            By default, does not raise and excludes the user from results

        Returns
        -------
        UserCollection
            Collection of user objects

        Raises
        ------
        NotFoundException
            When raise_when_not_found is True and a user is not found
        NoElementException
            When required elements are not found during user page parsing
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
    Abstract base class for user objects

    Defines common attributes and functionality for all user types.
    Do not instantiate this class directly; use derived classes instead.

    Attributes
    ----------
    client : Client
        Client instance
    id : int | None
        User ID
    name : str | None
        Username
    unix_name : str | None
        UNIX-formatted name used in user URLs
    avatar_url : str | None
        URL of the user's avatar image
    ip : str | None
        User's IP address (only set for anonymous users)
    """

    client: "Client"
    id: int | None = None
    name: str | None = None
    unix_name: str | None = None
    avatar_url: str | None = None
    ip: str | None = None

    def __str__(self) -> str:
        """
        String representation of the object

        Returns
        -------
        str
            String representation of the user object
        """
        return f"{self.__class__.__name__}(id={self.id}, name={self.name}, unix_name={self.unix_name})"


@dataclass
class User(AbstractUser):
    """
    A class representing a regular Wikidot user

    Represents a registered normal Wikidot user. Holds basic information such as user ID and username.

    Attributes
    ----------
    client : Client
        Client instance
    id : int | None
        User ID
    name : str | None
        Username
    unix_name : str | None
        UNIX-formatted name used in user URLs
    avatar_url : str | None
        URL of the user's avatar image
    ip : None
        User's IP address (None for regular users as it cannot be obtained)
    """

    # client: 'Client'
    # id: int | None
    # name: str | None
    # unix_name: str | None
    # avatar_url: str | None
    ip: str | None = None

    @staticmethod
    def from_name(client: "Client", name: str, raise_when_not_found: bool = False) -> Optional["AbstractUser"]:
        """
        Get a user object from a username

        Parameters
        ----------
        client : Client
            Client instance
        name : str
            Username to search for
        raise_when_not_found : bool, default False
            Whether to raise an exception when a user is not found (True: raise, False: do not raise)
            By default, returns None without raising

        Returns
        -------
        AbstractUser
            User object

        Raises
        ------
        NotFoundException
            When raise_when_not_found is True and the user is not found
        NoElementException
            When required elements are not found during user page parsing
        IndexError
            When the user is not found (when raise_when_not_found is False)
        """
        result = UserCollection.from_names(client, [name], raise_when_not_found)
        if len(result) == 0:
            if raise_when_not_found:
                raise NotFoundException(f"User not found: {name}")
            else:
                return None

        return result[0]

    def _require_id(self) -> int:
        if self.id is None:
            raise ValueError(f"User ID is not set: {self}")
        return self.id

    def get_changes(
        self,
        options: dict[str, bool] | None = None,
        limit: int | None = None,
    ) -> list[UserChange]:
        """
        Get the user's recent page edits, across all sites (user:info "Recent contributions" tab)

        Login is not required.

        Parameters
        ----------
        options : dict[str, bool] | None, default None
            Filter flags. Keys must be a subset of RECENT_CHANGES_OPTION_KEYS
            ("all", "source", "title", "move", "files", "new", "meta")
        limit : int | None, default None
            Maximum number of entries to retrieve. If None, retrieves all

        Returns
        -------
        list[UserChange]
            List of change history (in descending order by date)

        Raises
        ------
        ValueError
            If options contains an unknown key, or the user ID is not set
        NoElementException
            If HTML element parsing fails
        """
        return fetch_user_changes(self.client, self._require_id(), options=options, limit=limit)

    def get_posts(self, limit: int | None = None) -> list[RecentPost]:
        """
        Get the user's recent forum posts, across all sites (user:info "Recent posts and comments" tab)

        Login is not required.

        Parameters
        ----------
        limit : int | None, default None
            Maximum number of entries to retrieve. If None, retrieves all

        Returns
        -------
        list[RecentPost]
            List of recent posts (in descending order by date)

        Raises
        ------
        ValueError
            If the user ID is not set
        NoElementException
            If HTML element parsing fails
        """
        return fetch_user_posts(self.client, self._require_id(), limit=limit)

    def get_profile(self) -> UserProfile:
        """
        Get the user's profile (user:info "Profile" tab)

        Login is not required.

        Returns
        -------
        UserProfile
            Parsed profile

        Raises
        ------
        ValueError
            If the user ID is not set
        NoElementException
            If the profile box is not found
        AMCHttpStatusCodeException
            If the user does not exist (Wikidot responds with HTTP 500)
        """
        return fetch_user_profile(self.client, self._require_id())

    def get_member_of(self) -> list[UserSiteEntry]:
        """
        Get the sites the user is a member of (user:info "Member of" tab)

        Login is not required.

        Returns
        -------
        list[UserSiteEntry]
            Sites the user is a member of (empty if none)

        Raises
        ------
        ValueError
            If the user ID is not set
        """
        return fetch_user_site_entries(self.client, self._require_id(), "userinfo/UserInfoMemberOfModule")

    def get_admin_of(self) -> list[UserSiteEntry]:
        """
        Get the sites the user is an administrator of (user:info "Admin of" tab)

        Login is not required.

        Returns
        -------
        list[UserSiteEntry]
            Sites the user administers (empty if none)

        Raises
        ------
        ValueError
            If the user ID is not set
        """
        return fetch_user_site_entries(self.client, self._require_id(), "userinfo/UserInfoAdminOfModule")

    def get_moderator_of(self) -> list[UserSiteEntry]:
        """
        Get the sites the user is a moderator of (user:info "Moderator of" tab)

        Login is not required.

        Returns
        -------
        list[UserSiteEntry]
            Sites the user moderates (empty if none)

        Raises
        ------
        ValueError
            If the user ID is not set
        """
        return fetch_user_site_entries(self.client, self._require_id(), "userinfo/UserInfoModeratorOfModule")


@dataclass
class DeletedUser(AbstractUser):
    """
    A class representing a deleted Wikidot user

    Represents a user account that has been deleted.
    Deleted users are assigned a fixed name of "account deleted".

    Attributes
    ----------
    client : Client
        Client instance
    id : int | None
        User ID
    name : str
        Username (fixed as "account deleted" because the account is deleted)
    unix_name : str
        UNIX name of the user (fixed as "account_deleted" because the account is deleted)
    avatar_url : None
        URL of the user's avatar (None for deleted users)
    ip : None
        User's IP address (None as it cannot be obtained)
    """

    id: int | None = None
    name: str | None = "account deleted"
    unix_name: str | None = "account_deleted"
    avatar_url: str | None = None
    ip: str | None = None


@dataclass
class AnonymousUser(AbstractUser):
    """
    A class representing an anonymous (unregistered) Wikidot user

    Represents an anonymous user who posted without registering.
    Has only an IP address as identification information.

    Attributes
    ----------
    client : Client
        Client instance
    id : None
        User ID (None for anonymous users)
    name : str
        Username (fixed as "Anonymous" for anonymous users)
    unix_name : str
        UNIX name of the user (fixed as "anonymous" for anonymous users)
    avatar_url : None
        URL of the user's avatar (None for anonymous users)
    ip : str
        User's IP address
    """

    id: int | None = None
    name: str | None = "Anonymous"
    unix_name: str | None = "anonymous"
    avatar_url: str | None = None
    ip: str | None = None


@dataclass
class GuestUser(AbstractUser):
    """
    A class representing a guest Wikidot user who posted as a guest

    Represents a guest user who posted by entering only a name and email address.
    The username is optional but does not have an ID or UNIX name.

    Attributes
    ----------
    client : Client
        Client instance
    id : None
        User ID (None for guest users)
    name : str | None
        Username (name specified when posting as a guest)
    unix_name : None
        UNIX name of the user (None for guest users)
    avatar_url : str | None
        URL of the user's avatar (may be from Gravatar)
    ip : None
        User's IP address (None as it cannot be obtained)
    """

    id: int | None = None
    name: str | None = None
    unix_name: str | None = None
    avatar_url: str | None = None
    ip: str | None = None


@dataclass
class WikidotUser(AbstractUser):
    """
    A class representing the Wikidot system user

    A special user for representing automatic posts and notifications by the Wikidot system.
    Has a fixed name of "Wikidot".

    Attributes
    ----------
    client : Client
        Client instance
    id : None
        User ID (None for system users)
    name : str
        Username (fixed as "Wikidot" for system users)
    unix_name : str
        UNIX name of the user (fixed as "wikidot" for system users)
    avatar_url : None
        URL of the user's avatar (None for system users)
    ip : None
        User's IP address (None as it cannot be obtained)
    """

    id: int | None = None
    name: str | None = "Wikidot"
    unix_name: str | None = "wikidot"
    avatar_url: str | None = None
    ip: str | None = None
