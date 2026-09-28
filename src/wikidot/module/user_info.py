"""
Module for fetching the tabs of a user's `www.wikidot.com/user:info/<unix>` page

Every tab is rendered by a `userinfo/*` module on `www.wikidot.com`, and all
of them respond without login (measured 2026-09-28). The list modules
(userinfo/UserChangesListModule / userinfo/UserRecentPostsListModule) accept
any user's `userId` directly, so the functions here take a user ID and are
shared by User (any user) and AccountRecentActivity (the logged-in account).

Note the parameter names differ by module, following what the real UI's JS
sends: the tab modules take `user_id`, the list modules take `userId`.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from bs4 import BeautifulSoup, NavigableString, Tag

from ..common import exceptions
from ..connector.ajax import require_body
from ..util.amc_body import json_param, omit_falsy
from ..util.parser.odate import odate_parse as odate_parser

if TYPE_CHECKING:
    from .client import Client

#: option keys accepted by userinfo/UserChangesListModule's `options` JSON.
#: Unlike the page-history version (history/PageHistoryModule), there is no
#: "tags" key here.
RECENT_CHANGES_OPTION_KEYS = frozenset({"all", "source", "title", "move", "files", "new", "meta"})

_PAGER_TARGET_PATTERN = re.compile(r"updateList\((\d+)\)")
_POST_ID_PATTERN = re.compile(r"post-(\d+)")


@dataclass
class UserChange:
    """
    A row of a user's recent page edits (userinfo/UserChangesListModule)

    Nearly identical in structure to SiteChange (site.py's
    changes/SiteChangesListModule row), with a site column added since this
    view spans every site the user belongs to (measured 2026-07-29, see
    `70_account.md` "一覧モジュールの行マークアップ").

    Attributes
    ----------
    client : Client
        Client instance
    site_title : str
        Title of the site the change occurred on (td.site > a)
    site_url : str
        URL of the site the change occurred on (td.site > a href)
    page_fullname : str
        Fullname of the changed page (path of td.title > a href)
    page_title : str
        Title of the changed page
    revision_no : int
        Revision number (0 for page creation, shown as "(new)")
    changed_at : datetime
        Date and time of change
    flags : list[str]
        Change flags ("N"=new, "S"=source change, "T"=title change,
        "R"=rename, "M"=move, "F"=file, "A"=delete)
    """

    client: "Client"
    site_title: str
    site_url: str
    page_fullname: str
    page_title: str
    revision_no: int
    changed_at: datetime
    flags: list[str]

    def __str__(self) -> str:
        """
        String representation of the object

        Returns
        -------
        str
            String representation of the change history entry
        """
        return (
            f"UserChange(site_title={self.site_title}, page_fullname={self.page_fullname}, "
            f"revision_no={self.revision_no}, changed_at={self.changed_at}, flags={self.flags})"
        )


@dataclass
class RecentPost:
    """
    A row of a user's recent forum posts (userinfo/UserRecentPostsListModule)

    Each row is `div.post#post-<id>`, with `div.long > div.head > div.title > a`
    (title/link), `div.info > span.odate` (date), `on site <a>` / `in
    discussion: <a>` text-anchored links inside `div.info`, and `div.content`
    (post text) (measured 2026-09-28).

    Attributes
    ----------
    client : Client
        Client instance
    title : str
        Post/thread title (div.title > a)
    url : str
        Link to the post (div.title > a href)
    created_at : datetime
        Date and time of the post
    content : str
        Post text (div.content)
    post_id : int | None
        Post ID (from div.post's `post-<id>` id attribute)
    site_title : str | None
        Title of the site the post belongs to (link after "on site")
    site_url : str | None
        URL of the site the post belongs to
    thread_title : str | None
        Title of the thread the post belongs to (link after "in discussion:")
    thread_url : str | None
        URL of the thread the post belongs to
    """

    client: "Client"
    title: str
    url: str
    created_at: datetime
    content: str
    post_id: int | None = None
    site_title: str | None = None
    site_url: str | None = None
    thread_title: str | None = None
    thread_url: str | None = None

    def __str__(self) -> str:
        """
        String representation of the object

        Returns
        -------
        str
            String representation of the post
        """
        return f"RecentPost(title={self.title}, created_at={self.created_at})"


@dataclass
class UserProfile:
    """
    A user's profile tab (userinfo/UserInfoProfileModule)

    Which rows appear depends on the user, so every named field may be None;
    `fields` holds every row as rendered.

    Attributes
    ----------
    client : Client
        Client instance
    fields : dict[str, str]
        Every `dt` -> `dd` row (label without the trailing ":", whitespace-normalized text)
    real_name : str | None
        "Real name" row
    website : str | None
        "Website" row (link href, or the text if it has no link)
    member_since : datetime | None
        "Wikidot user since" row
    account_type : str | None
        "Account type" row (e.g. "free")
    karma_level : str | None
        First word of the "Karma level" row (e.g. "high")
    """

    client: "Client"
    fields: dict[str, str] = field(default_factory=dict)
    real_name: str | None = None
    website: str | None = None
    member_since: datetime | None = None
    account_type: str | None = None
    karma_level: str | None = None


@dataclass
class UserSiteEntry:
    """
    A site listed in a user's Member of / Admin of / Moderator of tab

    Attributes
    ----------
    client : Client
        Client instance
    title : str
        Site title (dt > a)
    url : str
        Site URL (dt > a href)
    subtitle : str | None
        Site subtitle (dt > small > em)
    description : str | None
        Site description (small in the following dd)
    """

    client: "Client"
    title: str
    url: str
    subtitle: str | None = None
    description: str | None = None


def _has_next_page(html: BeautifulSoup, page_no: int) -> bool:
    """
    Whether the list module's pager links to a page after `page_no`

    The last page's pager holds only "« previous" and lower page numbers, so
    reading a fixed link position as the last page number does not work.
    """
    pager = html.select_one("div.pager")
    if pager is None:
        return False
    targets = [
        int(match.group(1))
        for link in pager.select("a")
        if (match := _PAGER_TARGET_PATTERN.search(str(link.get("onclick", "")))) is not None
    ]
    return bool(targets) and max(targets) > page_no


def _parse_revision_no(text: str) -> int:
    if "(new)" in text:
        return 0
    rev_match = re.search(r"(\d+)", text)
    if rev_match is None:
        raise exceptions.NoElementException("Revision number is not found.")
    return int(rev_match.group(1))


def _parse_change(client: "Client", item: Tag) -> UserChange:
    site_elem = item.select_one("td.site a")

    title_elem = item.select_one("td.title a")
    if title_elem is None:
        raise exceptions.NoElementException("Title element is not found.")

    odate_elem = item.select_one("td.mod-date span.odate")
    if odate_elem is None:
        raise exceptions.NoElementException("Odate element is not found.")

    rev_elem = item.select_one("td.revision-no")
    if rev_elem is None:
        raise exceptions.NoElementException("Revision number element is not found.")

    return UserChange(
        client=client,
        site_title=site_elem.get_text().strip() if site_elem else "",
        site_url=str(site_elem.get("href", "")) if site_elem else "",
        page_fullname=urlparse(str(title_elem.get("href", ""))).path.strip("/"),
        page_title=title_elem.get_text().strip(),
        revision_no=_parse_revision_no(rev_elem.get_text()),
        changed_at=odate_parser(odate_elem),
        flags=[span.get_text().strip() for span in item.select("td.flags span.spantip")],
    )


def _link_after_text(container: Tag, label: str) -> Tag | None:
    """
    Find the direct-child `a` right after a text node ending with `label`

    `div.info` also nests links inside span.printuser, so "the first a" would
    pick the author instead of the site/thread.
    """
    for link in container.find_all("a", recursive=False):
        previous = link.previous_sibling
        if isinstance(previous, NavigableString) and previous.strip().endswith(label):
            return link
    return None


def _parse_post(client: "Client", item: Tag) -> RecentPost:
    title_elem = item.select_one("div.long div.head div.title a")
    if title_elem is None:
        raise exceptions.NoElementException("Title element is not found.")

    info_elem = item.select_one("div.info")
    odate_elem = info_elem.select_one("span.odate") if info_elem else None
    content_elem = item.select_one("div.content")
    site_link = _link_after_text(info_elem, "on site") if info_elem else None
    thread_link = _link_after_text(info_elem, "in discussion:") if info_elem else None
    post_id_match = _POST_ID_PATTERN.fullmatch(str(item.get("id", "")))

    return RecentPost(
        client=client,
        title=title_elem.get_text().strip(),
        url=str(title_elem.get("href", "")),
        created_at=(odate_parser(odate_elem) if odate_elem else datetime.fromtimestamp(0)),
        content=content_elem.get_text().strip() if content_elem else "",
        post_id=int(post_id_match.group(1)) if post_id_match else None,
        site_title=site_link.get_text().strip() if site_link else None,
        site_url=str(site_link.get("href", "")) if site_link else None,
        thread_title=thread_link.get_text().strip() if thread_link else None,
        thread_url=str(thread_link.get("href", "")) if thread_link else None,
    )


def validate_recent_changes_options(options: dict[str, bool] | None) -> None:
    """
    Reject option keys that userinfo/UserChangesListModule does not accept

    Parameters
    ----------
    options : dict[str, bool] | None
        Filter flags passed to fetch_user_changes

    Raises
    ------
    ValueError
        If options contains a key outside RECENT_CHANGES_OPTION_KEYS
    """
    if options is None:
        return
    unknown = set(options) - RECENT_CHANGES_OPTION_KEYS
    if unknown:
        raise ValueError(
            f"Unknown options for userinfo/UserChangesListModule "
            f"(no 'tags' key here, unlike page-history options): {sorted(unknown)}"
        )


def fetch_user_changes(
    client: "Client",
    user_id: int,
    options: dict[str, bool] | None = None,
    limit: int | None = None,
) -> list[UserChange]:
    """
    Get a user's recent page edits, across all sites

    Wraps `userinfo/UserChangesListModule`, fetching pages until exhausted or
    `limit` is reached.

    Parameters
    ----------
    client : Client
        Client instance
    user_id : int
        ID of the user whose edits to fetch
    options : dict[str, bool] | None, default None
        Filter flags. Keys must be a subset of RECENT_CHANGES_OPTION_KEYS
    limit : int | None, default None
        Maximum number of entries to retrieve. If None, retrieves all

    Returns
    -------
    list[UserChange]
        List of change history (in descending order by date)

    Raises
    ------
    ValueError
        If options contains a key outside RECENT_CHANGES_OPTION_KEYS
    NoElementException
        If HTML element parsing fails
    """
    validate_recent_changes_options(options)

    changes: list[UserChange] = []
    per_page = min(limit, 1000) if limit is not None else 1000
    page_no = 1

    while True:
        response = client.amc_client.request(
            [
                {
                    "moduleName": "userinfo/UserChangesListModule",
                    "page": page_no,
                    "perpage": per_page,
                    "userId": user_id,
                    **omit_falsy(options=json_param(options) if options else False),
                }
            ]
        )[0]
        html = BeautifulSoup(require_body(response, "userinfo/UserChangesListModule"), "lxml")
        items = html.select("div.changes-list-item")

        if not items:
            break

        for item in items:
            changes.append(_parse_change(client, item))
            if limit is not None and len(changes) >= limit:
                return changes

        if not _has_next_page(html, page_no):
            break
        page_no += 1

    return changes


def fetch_user_posts(client: "Client", user_id: int, limit: int | None = None) -> list[RecentPost]:
    """
    Get a user's recent forum posts, across all sites

    Wraps `userinfo/UserRecentPostsListModule`, fetching pages until
    exhausted or `limit` is reached. The module ignores `perpage` and always
    returns 20 posts per page.

    Parameters
    ----------
    client : Client
        Client instance
    user_id : int
        ID of the user whose posts to fetch
    limit : int | None, default None
        Maximum number of entries to retrieve. If None, retrieves all

    Returns
    -------
    list[RecentPost]
        List of recent posts (in descending order by date)

    Raises
    ------
    NoElementException
        If HTML element parsing fails
    """
    posts: list[RecentPost] = []
    page_no = 1

    while True:
        response = client.amc_client.request(
            [
                {
                    "moduleName": "userinfo/UserRecentPostsListModule",
                    "page": page_no,
                    "userId": user_id,
                }
            ]
        )[0]
        html = BeautifulSoup(require_body(response, "userinfo/UserRecentPostsListModule"), "lxml")
        items = html.select("div.post")

        if not items:
            break

        for item in items:
            posts.append(_parse_post(client, item))
            if limit is not None and len(posts) >= limit:
                return posts

        if not _has_next_page(html, page_no):
            break
        page_no += 1

    return posts


def _fetch_tab(client: "Client", module_name: str, user_id: int) -> BeautifulSoup:
    response = client.amc_client.request([{"moduleName": module_name, "user_id": user_id}])[0]
    return BeautifulSoup(require_body(response, module_name), "lxml")


def fetch_user_profile(client: "Client", user_id: int) -> UserProfile:
    """
    Get a user's profile tab (userinfo/UserInfoProfileModule)

    Parameters
    ----------
    client : Client
        Client instance
    user_id : int
        ID of the user

    Returns
    -------
    UserProfile
        Parsed profile

    Raises
    ------
    NoElementException
        If the profile box is not found
    """
    html = _fetch_tab(client, "userinfo/UserInfoProfileModule", user_id)
    box = html.select_one("div.profile-box")
    if box is None:
        raise exceptions.NoElementException("Profile box is not found.")

    fields: dict[str, str] = {}
    dds: dict[str, Tag] = {}
    for dt in box.select("dl > dt"):
        dd = dt.find_next_sibling("dd")
        if not isinstance(dd, Tag):
            continue
        label = dt.get_text().strip().removesuffix(":").strip()
        fields[label] = " ".join(dd.get_text().split())
        dds[label] = dd

    website: str | None = None
    if "Website" in dds:
        website_link = dds["Website"].select_one("a")
        website = str(website_link.get("href", "")) if website_link else fields["Website"]

    member_since_elem = dds["Wikidot user since"].select_one("span.odate") if "Wikidot user since" in dds else None
    karma_words = fields.get("Karma level", "").split()

    return UserProfile(
        client=client,
        fields=fields,
        real_name=fields.get("Real name"),
        website=website,
        member_since=odate_parser(member_since_elem) if member_since_elem else None,
        account_type=fields.get("Account type"),
        karma_level=karma_words[0] if karma_words else None,
    )


def fetch_user_site_entries(client: "Client", user_id: int, module_name: str) -> list[UserSiteEntry]:
    """
    Get the sites listed in a user's Member of / Admin of / Moderator of tab

    Parameters
    ----------
    client : Client
        Client instance
    user_id : int
        ID of the user
    module_name : str
        "userinfo/UserInfoMemberOfModule", "userinfo/UserInfoAdminOfModule"
        or "userinfo/UserInfoModeratorOfModule"

    Returns
    -------
    list[UserSiteEntry]
        Listed sites (empty if the tab has no list)

    Raises
    ------
    NoElementException
        If a listed site has no link
    """
    html = _fetch_tab(client, module_name, user_id)
    site_list = html.select_one("dl")
    if site_list is None:
        return []

    entries: list[UserSiteEntry] = []
    for dt in site_list.find_all("dt", recursive=False):
        link = dt.find("a", recursive=False)
        if not isinstance(link, Tag):
            raise exceptions.NoElementException("Site link is not found.")
        subtitle_elem = dt.select_one(":scope > small > em")
        dd = dt.find_next_sibling()
        description_elem = dd.select_one("small") if isinstance(dd, Tag) and dd.name == "dd" else None
        description = description_elem.get_text().strip() if description_elem else ""

        entries.append(
            UserSiteEntry(
                client=client,
                title=link.get_text().strip(),
                url=str(link.get("href", "")),
                subtitle=subtitle_elem.get_text().strip() if subtitle_elem else None,
                description=description or None,
            )
        )
    return entries
