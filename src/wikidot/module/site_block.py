"""
Module for parsing Wikidot site user/IP block listings

`managesite/blocks/{ManageSiteUserBlocksModule,ManageSiteIpBlocksModule}`
render these lists; there is no pagination parameter for either (unlike the
member lists in site_member_admin.py) per this project's JS research
(`managesite_blocks_ManageSiteUserBlocksModule.js` /
`managesite_blocks_ManageSiteIpBlocksModule.js` take no `page` argument).

Access these through `Site.member.get_blocked_users()` /
`Site.member.get_blocked_ips()`, not directly.
"""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

from ..util.parser import user as user_parser

if TYPE_CHECKING:
    from .site import Site
    from .user import AbstractUser

#: Matches the `deleteBlock(event, <id>, ...)` onclick handlers Wikidot's
#: client embeds per row (see forum_post_revision.py's showRevision(event, id)
#: for the same onclick-parsing pattern used elsewhere in this codebase).
_DELETE_BLOCK_ID_RE = re.compile(r"deleteBlock\s*\(\s*event\s*,\s*(\d+)")


@dataclass
class UserBlock:
    """
    A single blocked-user entry

    **Row markup is not directly measured** (no admin-panel HTML sample was
    captured for this module; only the client-side JS handlers were). Row
    parsing reuses the `span.printuser` convention validated elsewhere in
    this codebase (e.g. `SiteMember._parse`, `ForumPostRevision`), since
    `managesite_blocks_ManageSiteUserBlocksModule.js` confirms each row's
    "unblock" control passes the user ID via `deleteBlock(event, userId, ...)`
    -- the same onclick-argument shape as other admin listings in this
    project. Verify against a live site before relying on `reason` parsing.

    Attributes
    ----------
    site : Site
        The site the block applies to
    user : AbstractUser
        The blocked user
    reason : str
        Block reason, as rendered (best-effort; row markup unverified)
    """

    site: "Site"
    user: "AbstractUser"
    reason: str

    @staticmethod
    def _parse_all(site: "Site", html: BeautifulSoup) -> list["UserBlock"]:
        """Internal method to extract blocked-user entries from list HTML"""
        blocks: list[UserBlock] = []

        for row in html.select("table tr"):
            user_elem = row.select_one("span.printuser")
            if user_elem is None:
                continue

            user = user_parser(site.client, user_elem)

            cells = row.select("td")
            reason = cells[-1].get_text(strip=True) if cells else ""

            blocks.append(UserBlock(site, user, reason))

        return blocks


@dataclass
class IpBlock:
    """
    A single blocked-IP entry

    **Row markup is not directly measured** (same caveat as `UserBlock`).
    `block_id` is extracted from the `deleteBlock(event, blockId, ...)`
    onclick handler (`managesite_blocks_ManageSiteIpBlocksModule.js`
    confirms this argument is a block ID, not the IP itself -- asymmetric
    with `UserBlock`, whose equivalent argument is a user ID; see
    site_member_admin.py's `unblock_user`/`unblock_ip` docstrings).

    Attributes
    ----------
    site : Site
        The site the block applies to
    block_id : int
        Block ID (required by `unblock_ip`)
    ip : str
        Blocked IP address/range, as rendered (best-effort; row markup
        unverified)
    reason : str
        Block reason, as rendered (best-effort; row markup unverified)
    """

    site: "Site"
    block_id: int
    ip: str
    reason: str

    @staticmethod
    def _parse_all(site: "Site", html: BeautifulSoup) -> list["IpBlock"]:
        """Internal method to extract blocked-IP entries from list HTML"""
        blocks: list[IpBlock] = []

        for row in html.select("table tr"):
            link = row.select_one("a[onclick*='deleteBlock']")
            if link is None:
                continue

            match = _DELETE_BLOCK_ID_RE.search(str(link.get("onclick", "")))
            if match is None:
                continue
            block_id = int(match.group(1))

            cells = row.select("td")
            if not cells:
                continue
            ip = cells[0].get_text(strip=True)
            reason = cells[-1].get_text(strip=True) if len(cells) > 1 else ""

            blocks.append(IpBlock(site, block_id, ip, reason))

        return blocks
