import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal, Optional, overload

import httpx
from bs4 import BeautifulSoup

if sys.version_info >= (3, 12):
    from typing import Unpack
else:
    from typing_extensions import Unpack

from ..common import exceptions
from ..common.decorators import login_required
from ..util.http import sync_get_with_retry
from ..util.parser import odate as odate_parser
from ..util.parser import user as user_parser
from ..util.quick_module import QMCUser, QuickModule
from .forum_category import ForumCategoryCollection
from .forum_thread import ForumThread, ForumThreadCollection
from .page import Page, PageCollection, SearchPagesQuery, SearchPagesQueryParams
from .site_application import SiteApplication
from .site_member import SiteMember

if TYPE_CHECKING:
    from .client import Client
    from .user import AbstractUser, User


class SitePagesAccessor:
    """
    A class that provides operations on page collections within a site

    Provides operations on multiple pages such as page search functionality.
    Access through the Site.pages property.
    """

    def __init__(self, site: "Site"):
        """
        Initialize method

        Parameters
        ----------
        site : Site
            Parent site instance
        """
        self.site = site

    def search(self, **kwargs: Unpack[SearchPagesQueryParams]) -> "PageCollection":
        """
        Search for pages within a site

        Receives keyword arguments, converts them to a SearchPagesQuery object, and executes the search.

        Parameters
        ----------
        **kwargs : Unpack[SearchPagesQueryParams]
            Search condition keyword arguments. See SearchPagesQueryParams for details.

        Returns
        -------
        PageCollection
            Page collection of search results
        """
        query = SearchPagesQuery(**kwargs)
        return PageCollection.search_pages(self.site, query)


class SitePageAccessor:
    """
    A class that provides operations on individual pages within a site

    Provides individual page operations such as retrieving and creating pages.
    Access through the Site.page property.
    """

    def __init__(self, site: "Site"):
        """
        Initialize method

        Parameters
        ----------
        site : Site
            Parent site instance
        """
        self.site = site

    def get(self, fullname: str, raise_when_not_found: bool = True) -> Optional["Page"]:
        """
        Get a page from its fullname

        Parameters
        ----------
        fullname : str
            Fullname of the page (e.g., "component:scp-173")
        raise_when_not_found : bool, default True
            Whether to raise an exception if the page is not found
            If False, returns None when the page is not found

        Returns
        -------
        Page | None
            Page object, or None if not found

        Raises
        ------
        NotFoundException
            When raise_when_not_found is True and the page is not found
        """
        res = PageCollection.search_pages(self.site, SearchPagesQuery(fullname=fullname))
        if len(res) == 0:
            if raise_when_not_found:
                raise exceptions.NotFoundException(f"Page is not found: {fullname}")
            return None
        return res[0]

    def create(
        self,
        fullname: str,
        title: str = "",
        source: str = "",
        comment: str = "",
        force_edit: bool = False,
    ) -> "Page":
        """
        Create a new page

        Parameters
        ----------
        fullname : str
            Fullname of the page (e.g., "scp-173")
        title : str, default ""
            Title of the page
        source : str, default ""
            Source code of the page (Wikidot markup)
        comment : str, default ""
            Edit comment
        force_edit : bool, default False
            Whether to overwrite if the page already exists

        Returns
        -------
        Page
            Created page object

        Raises
        ------
        TargetErrorException
            When the page already exists and force_edit is False
        """
        return Page.create_or_edit(
            site=self.site,
            fullname=fullname,
            title=title,
            source=source,
            comment=comment,
            force_edit=force_edit,
            raise_on_exists=True,
        )


class SiteForumAccessor:
    """
    A class that provides operations on forum functionality within a site

    Provides forum-related functionality such as retrieving forum categories.
    Access through the Site.forum property.
    """

    def __init__(self, site: "Site"):
        """
        Initialize method

        Parameters
        ----------
        site : Site
            Parent site instance
        """
        self.site = site

    @property
    def categories(self) -> "ForumCategoryCollection":
        """
        Get a list of forum categories within the site

        Returns
        -------
        ForumCategoryCollection
            Collection of forum categories
        """
        return ForumCategoryCollection.acquire_all(self.site)


@dataclass
class SiteChange:
    """
    A class representing a single change history entry for a site

    Holds information about changes to pages within a site (creation, editing, deletion, etc.).

    Attributes
    ----------
    site : Site
        Site where the change occurred
    page_fullname : str
        Fullname of the changed page
    page_title : str
        Title of the changed page
    revision_no : int
        Revision number
    changed_by : AbstractUser
        User who made the change
    changed_at : datetime
        Date and time of change
    flags : list[str]
        Change flags ("N"=new, "S"=source change, "T"=title change, "R"=rename, "M"=move, "F"=file, "A"=delete)
    comment : str | None
        Change comment
    """

    site: "Site"
    page_fullname: str
    page_title: str
    revision_no: int
    changed_by: "AbstractUser"
    changed_at: datetime
    flags: list[str]
    comment: str | None

    def __str__(self) -> str:
        """
        String representation of the object

        Returns
        -------
        str
            String representation of the change history
        """
        return (
            f"SiteChange(page_fullname={self.page_fullname}, "
            f"revision_no={self.revision_no}, changed_by={self.changed_by}, "
            f"changed_at={self.changed_at}, flags={self.flags})"
        )


@dataclass
class Site:
    """
    A class representing a Wikidot site

    Provides basic site information and various operational functions for the site.
    Serves as the entry point for accessing features such as pages, forums, and member management.

    Attributes
    ----------
    client : Client
        Client instance
    id : int
        Site ID
    title : str
        Title of the site
    unix_name : str
        UNIX name of the site (used as part of the URL)
    domain : str
        Domain of the site (fully qualified domain name)
    ssl_supported : bool
        Whether the site supports SSL/HTTPS
    """

    client: "Client"

    id: int
    title: str
    unix_name: str
    domain: str
    ssl_supported: bool

    # Accessor属性
    pages: "SitePagesAccessor" = field(init=False, repr=False)
    page: "SitePageAccessor" = field(init=False, repr=False)
    forum: "SiteForumAccessor" = field(init=False, repr=False)

    # キャッシュ属性
    _members: list["SiteMember"] | None = field(init=False, default=None, repr=False)
    _moderators: list["SiteMember"] | None = field(init=False, default=None, repr=False)
    _admins: list["SiteMember"] | None = field(init=False, default=None, repr=False)

    def __post_init__(self) -> None:
        """
        Post-initialization processing

        Initializes instances of each subclass that provides site-related functionality.
        """
        self.pages = SitePagesAccessor(self)
        self.page = SitePageAccessor(self)
        self.forum = SiteForumAccessor(self)

    def __str__(self) -> str:
        """
        String representation of the object

        Returns
        -------
        str
            String representation of the site object
        """
        return f"Site(id={self.id}, title={self.title}, unix_name={self.unix_name})"

    @staticmethod
    def from_unix_name(client: "Client", unix_name: str) -> "Site":
        """
        Get a site object from a UNIX name

        Accesses the site with the specified UNIX name, parses site information, and generates a Site object.

        Parameters
        ----------
        client : Client
            Client instance
        unix_name : str
            UNIX name of the site (e.g., "fondation")

        Returns
        -------
        Site
            Site object

        Raises
        ------
        NotFoundException
            When a site with the specified UNIX name does not exist
        UnexpectedException
            When an error occurs during site information parsing
        """
        # サイト情報を取得
        # リダイレクトには従う、リトライ付き
        config = client.amc_client.config
        response = sync_get_with_retry(
            f"http://{unix_name}.wikidot.com",
            timeout=config.request_timeout,
            attempt_limit=config.attempt_limit,
            retry_interval=config.retry_interval,
            max_backoff=config.max_backoff,
            backoff_factor=config.backoff_factor,
            follow_redirects=True,
            raise_for_status=False,
        )

        # サイトが存在しない場合
        if response.status_code == httpx.codes.NOT_FOUND:
            raise exceptions.NotFoundException(f"Site is not found: {unix_name}.wikidot.com")

        # サイトが存在する場合
        source = response.text

        # id : WIKIREQUEST.info.siteId = xxxx;
        id_match = re.search(r"WIKIREQUEST\.info\.siteId = (\d+);", source)
        if id_match is None:
            raise exceptions.UnexpectedException(f"Cannot find site id: {unix_name}.wikidot.com")
        site_id = int(id_match.group(1))

        # title : titleタグ
        title_match = re.search(r"<title>(.*?)</title>", source)
        if title_match is None:
            raise exceptions.UnexpectedException(f"Cannot find site title: {unix_name}.wikidot.com")
        title = title_match.group(1)

        # unix_name : WIKIREQUEST.info.siteUnixName = "xxxx";
        unix_name_match = re.search(r'WIKIREQUEST\.info\.siteUnixName = "(.*?)";', source)
        if unix_name_match is None:
            raise exceptions.UnexpectedException(f"Cannot find site unix_name: {unix_name}.wikidot.com")
        unix_name = unix_name_match.group(1)

        # domain :WIKIREQUEST.info.domain = "xxxx";
        domain_match = re.search(r'WIKIREQUEST\.info\.domain = "(.*?)";', source)
        if domain_match is None:
            raise exceptions.UnexpectedException(f"Cannot find site domain: {unix_name}.wikidot.com")
        domain = domain_match.group(1)

        # SSL対応チェック
        ssl_supported = str(response.url).startswith("https")

        return Site(
            client=client,
            id=site_id,
            title=title,
            unix_name=unix_name,
            domain=domain,
            ssl_supported=ssl_supported,
        )

    @overload
    def amc_request(
        self, bodies: list[dict[str, Any]], return_exceptions: Literal[False] = False
    ) -> tuple[httpx.Response, ...]: ...

    @overload
    def amc_request(
        self, bodies: list[dict[str, Any]], return_exceptions: Literal[True] = ...
    ) -> tuple[httpx.Response | Exception, ...]: ...

    def amc_request(
        self, bodies: list[dict[str, Any]], return_exceptions: bool = False
    ) -> tuple[httpx.Response, ...] | tuple[httpx.Response | Exception, ...]:
        """
        Execute an Ajax Module Connector request for this site

        Parameters
        ----------
        bodies : list[dict]
            List of request bodies
        return_exceptions : bool, default False
            Whether to return or raise exceptions (True: return, False: raise)

        Returns
        -------
        list | Exception
            List of responses, or exceptions if return_exceptions is True
        """
        if return_exceptions:
            return self.client.amc_client.request(bodies, True, self.unix_name, self.ssl_supported)
        else:
            return self.client.amc_client.request(bodies, False, self.unix_name, self.ssl_supported)

    @property
    def applications(self) -> list[SiteApplication]:
        """
        Get pending membership applications to the site

        Returns
        -------
        list[SiteApplication]
            List of membership applications
        """
        return SiteApplication.acquire_all(self)

    @login_required
    def invite_user(self, user: "User", text: str) -> None:
        """
        Invite a user to the site

        Parameters
        ----------
        user : User
            User to invite
        text : str
            Invitation message

        Raises
        ------
        TargetErrorException
            When the user is already invited or already a member
        WikidotStatusCodeException
            When other Wikidot API errors occur
        LoginRequiredException
            When not logged in (by @login_required decorator)
        """
        try:
            self.amc_request(
                [
                    {
                        "action": "ManageSiteMembershipAction",
                        "event": "inviteMember",
                        "user_id": user.id,
                        "text": text,
                        "moduleName": "Empty",
                    }
                ]
            )
        except exceptions.WikidotStatusCodeException as e:
            if e.status_code == "already_invited":
                raise exceptions.TargetErrorException(
                    f"User is already invited to {self.unix_name}: {user.name}"
                ) from e
            elif e.status_code == "already_member":
                raise exceptions.TargetErrorException(
                    f"User is already a member of {self.unix_name}: {user.name}"
                ) from e
            else:
                raise e

    @property
    def url(self) -> str:
        """
        Get the URL of the site

        Returns
        -------
        str
            Full URL of the site
        """
        return f"http{'s' if self.ssl_supported else ''}://{self.domain}"

    @property
    def members(self) -> list[SiteMember]:
        """
        Get a list of site members

        Returns
        -------
        list[SiteMember]
            List of site members
        """
        if self._members is None:
            self._members = SiteMember.get(self)
        return self._members

    @property
    def moderators(self) -> list[SiteMember]:
        """
        Get a list of site moderators

        Returns
        -------
        list[SiteMember]
            List of site moderators
        """
        if self._moderators is None:
            self._moderators = SiteMember.get(self, "moderators")
        return self._moderators

    @property
    def admins(self) -> list[SiteMember]:
        """
        Get a list of site administrators

        Returns
        -------
        list[SiteMember]
            List of site administrators
        """
        if self._admins is None:
            self._admins = SiteMember.get(self, "admins")
        return self._admins

    def member_lookup(self, user_name: str, user_id: int | None = None) -> bool:
        """
        Check whether a specified user is a member of the site

        Parameters
        ----------
        user_name : str
            Username to check
        user_id : int | None, default None
            User ID to check (if specified, the ID must also match)

        Returns
        -------
        bool
            True if the user is a site member, False otherwise
        """
        users: list[QMCUser] = QuickModule.member_lookup(self.id, user_name)

        if len(users) == 0:
            return False

        for user in users:
            if user.name.strip() == user_name and (user_id is None or user.id == user_id):
                return True

        return False

    def get_thread(self, thread_id: int) -> ForumThread:
        """
        Get a thread

        Parameters
        ----------
        thread_id : int
            Thread ID

        Returns
        -------
        ForumThread
            Thread object
        """
        return ForumThread.get_from_id(self, thread_id)

    def get_threads(self, thread_ids: list[int]) -> ForumThreadCollection:
        """
        Get multiple threads

        Parameters
        ----------
        thread_ids : list[int]
            List of thread IDs

        Returns
        -------
        list[ForumThread]
            List of thread objects
        """
        return ForumThreadCollection.acquire_from_thread_ids(self, thread_ids)

    def get_recent_changes(self, limit: int | None = None) -> list["SiteChange"]:
        """
        Get recent change history of the site

        Retrieves recent changes to pages within the site (creation, editing, deletion, etc.).

        Parameters
        ----------
        limit : int | None, default None
            Maximum number of entries to retrieve. If None, retrieves only the first page (default count)

        Returns
        -------
        list[SiteChange]
            List of change history (in descending order by date)

        Raises
        ------
        NoElementException
            When HTML element parsing fails
        """
        from ..common.exceptions import NoElementException

        changes: list[SiteChange] = []
        per_page = min(limit, 1000) if limit is not None else 1000
        page_no = 1

        while True:
            response = self.amc_request(
                [
                    {
                        "moduleName": "changes/SiteChangesListModule",
                        "perpage": str(per_page),
                        "page": page_no,
                        "options": "{'all':true}",
                    }
                ]
            )[0]

            html = BeautifulSoup(response.json()["body"], "lxml")
            items = html.select("div.changes-list-item")

            if not items:
                break

            for item in items:
                comment_elem = item.select_one("td.comments")
                comment = comment_elem.get_text().strip() if comment_elem else None
                if comment == "":
                    comment = None

                title_elem = item.select_one("td.title a")
                if title_elem is None:
                    raise NoElementException("Title element is not found.")

                page_title = title_elem.get_text().strip()
                href = title_elem.get("href", "")
                page_fullname = str(href).strip("/")

                odate_elem = item.select_one("td.mod-date span.odate")
                if odate_elem is None:
                    raise NoElementException("Odate element is not found.")
                changed_at = odate_parser(odate_elem)

                rev_elem = item.select_one("td.revision-no")
                if rev_elem is None:
                    raise NoElementException("Revision number element is not found.")
                rev_text = rev_elem.get_text()
                rev_match = re.search(r"(\d+)", rev_text)
                if rev_match is None:
                    raise NoElementException("Revision number is not found.")
                revision_no = int(rev_match.group(1))

                user_elem = item.select_one("td.mod-by span.printuser")
                if user_elem is None:
                    raise NoElementException("User element is not found.")
                changed_by = user_parser(self.client, user_elem)

                flags_elem = item.select("td.flags span")
                flags = [span.get_text().strip() for span in flags_elem]

                changes.append(
                    SiteChange(
                        site=self,
                        page_fullname=page_fullname,
                        page_title=page_title,
                        revision_no=revision_no,
                        changed_by=changed_by,
                        changed_at=changed_at,
                        flags=flags,
                        comment=comment,
                    )
                )

                if limit is not None and len(changes) >= limit:
                    return changes

            pager = html.select_one("div.pager")
            if pager is None:
                break

            pager_links = pager.select("a")
            if len(pager_links) < 2:
                break

            last_page = int(pager_links[-2].get_text().strip())
            if page_no >= last_page:
                break

            page_no += 1

        return changes
