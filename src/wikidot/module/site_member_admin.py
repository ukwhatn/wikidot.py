"""
Module for Wikidot site member administration (Manage Site's members/
invitations/abuse panels)

Access through `Site.member` (singular; complements the existing plural
`Site.members` / `Site.moderators` / `Site.admins` properties, which read
from the public-facing `membership/MembersListModule` and are unaffected by
this module). `Site.member` groups administrative operations that require
site-admin permissions: removing/promoting/demoting members, moderator
permissions, invitations, membership-application handling (delegated to
`SiteApplication`, unchanged), members auto-watching, and abuse-flag
clearing. Site user/IP blocks are a separate but related concern, exposed
here too (see `site_block.py` for the underlying parsing).

See plan/32_tasks.md Task 2-1..2-6 for the task breakdown this follows.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bs4 import BeautifulSoup

from ..connector.ajax import require_body
from ..util.amc_body import checkbox, flag, json_param, omit_falsy
from .site_block import IpBlock, UserBlock
from .site_member import SiteMember

if TYPE_CHECKING:
    from .site import Site
    from .user import AbstractUser


def _user_id(user: "AbstractUser | int") -> int:
    """Resolve a user-or-id argument to a plain int, matching the
    AbstractUser | int convenience pattern already used elsewhere
    (e.g. site_settings.py's `viewers` / `others` parameters)"""
    if isinstance(user, int):
        return user
    if user.id is None:
        raise ValueError(f"User has no id: {user}")
    return user.id


@dataclass
class UserSearchResult:
    """
    A single result row from `users/UserSearchModule`

    Attributes
    ----------
    id : int
        User ID
    name : str
        Username
    """

    id: int
    name: str


class MemberAccessor:
    """
    Accessor for site member administration (Manage Site panel)

    Access through `Site.member`.
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

    # ------------------------------------------------------------------
    # Task 2-1: admin-view member listing (paginated)
    # ------------------------------------------------------------------

    def _get_paginated(self, module_name: str) -> list[SiteMember]:
        """
        Internal helper: fetch a paginated `managesite/members/*` listing

        Parameters
        ----------
        module_name : str
            One of the three `managesite/members/*` modules

        Returns
        -------
        list[SiteMember]

        Notes
        -----
        Row markup for `ManageSiteMembersListModule` was confirmed live
        2026-07-29 (see 40_admin-managesite.md): 1st `td` is
        `span.printuser`, 2nd is `span.odate` (join date), 3rd is a
        Bootstrap options dropdown; a leading `th`-only header row is
        skipped by `SiteMember._parse`. `ManageSiteModeratorsModule` /
        `ManageSiteAdminsModule` were **not** confirmed (the test site had
        no moderators/admins to render), but are assumed to share this
        shape since Wikidot's server templates consistently render member
        rows through the shared `WIKIDOT.render.printuser` partial.

        **Pagination is unconfirmed.** The test site's 6 members did not
        render a `div.pager` at all, so whether the admin panel uses the
        same `div.pager` markup as the public `membership/MembersListModule`
        (vs. Bootstrap-style pagination) could not be verified -- Wikidot's
        own client (`loadMemberList`) just re-requests with `page` and does
        not itself track a total page count. The `page` parameter is
        confirmed correct either way; single-page results (the common case)
        are unaffected. Re-verify against a site with enough members to
        paginate before relying on multi-page results.
        """
        members: list[SiteMember] = []

        first_response = self.site.amc_request([{"moduleName": module_name, "page": 1}])[0]
        first_body = require_body(first_response, module_name)
        first_html = BeautifulSoup(first_body, "lxml")
        members.extend(SiteMember._parse(self.site, first_html))

        pager = first_html.select_one("div.pager")
        if pager is None:
            return members

        last_page = int(pager.select("a")[-2].text)
        if last_page == 1:
            return members

        responses = self.site.amc_request(
            [{"moduleName": module_name, "page": page} for page in range(2, last_page + 1)]
        )
        for response in responses:
            body = require_body(response, module_name)
            html = BeautifulSoup(body, "lxml")
            members.extend(SiteMember._parse(self.site, html))

        return members

    def get_members(self) -> list[SiteMember]:
        """
        Get the admin-panel view of all site members

        Uses `managesite/members/ManageSiteMembersListModule`, distinct from
        `Site.members` (public `membership/MembersListModule`): this is the
        view rendered inside `_admin`, requires site-admin permissions, and
        is what Wikidot's own client re-fetches after remove/promote/demote
        actions to refresh the panel.

        Returns
        -------
        list[SiteMember]
        """
        return self._get_paginated("managesite/members/ManageSiteMembersListModule")

    def get_moderators(self) -> list[SiteMember]:
        """
        Get the admin-panel view of site moderators

        Returns
        -------
        list[SiteMember]
        """
        return self._get_paginated("managesite/members/ManageSiteModeratorsModule")

    def get_admins(self) -> list[SiteMember]:
        """
        Get the admin-panel view of site administrators

        Returns
        -------
        list[SiteMember]
        """
        return self._get_paginated("managesite/members/ManageSiteAdminsModule")

    # ------------------------------------------------------------------
    # Task 2-2: member removal / ownership transfer / moderator perms
    # ------------------------------------------------------------------

    def remove(self, user: "AbstractUser | int", *, ban: bool = False) -> None:
        """
        Remove a member from the site. Destructive

        Parameters
        ----------
        user : AbstractUser | int
            Member to remove (or their user ID)
        ban : bool, default False
            **`ban=True` removes the member and blocks them in one call**
            (Wikidot's own client calls this combined flow "remove and
            ban" -- it is not merely a removal reason). Sent as `ban="yes"`
            when True; omitted entirely when False. If you only want to
            remove membership without blocking, leave this False
        """
        body = omit_falsy(ban="yes" if ban else False)
        self.site.amc_request(
            [
                {
                    "action": "ManageSiteMembershipAction",
                    "event": "removeMember",
                    "user_id": _user_id(user),
                    "moduleName": "Empty",
                    **body,
                }
            ]
        )

    def change_master(self, user: "AbstractUser | int") -> None:
        """
        Transfer site master-admin ownership to another admin

        Destructive from the caller's perspective: the caller loses master
        status. Uses `userId` (camelCase) -- unlike every other
        `ManageSiteMembershipAction` event in this module (which use
        `user_id`), Wikidot's own client sends this one parameter name in
        camelCase for `changeMaster` specifically (see 40_admin-managesite.md).

        Parameters
        ----------
        user : AbstractUser | int
            New master admin (must already be a site admin; or their user ID)
        """
        self.site.amc_request(
            [
                {
                    "action": "ManageSiteMembershipAction",
                    "event": "changeMaster",
                    "userId": _user_id(user),
                    "moduleName": "Empty",
                }
            ]
        )

    def get_moderator_permissions_form(self, moderator_id: int) -> dict[str, Any]:
        """
        Fetch the raw `sm-mod-perms-form` HTML for a moderator

        **未実測**: the test site used for this research had no moderators,
        so `sm-mod-perms-form`'s field names could not be captured (see
        35_form-fields.md). Returns the raw rendered HTML body instead of a
        typed structure -- inspect it yourself and pass the exact field
        names to `save_moderator_permissions`.

        Parameters
        ----------
        moderator_id : int
            Moderator's user ID (obtainable from `get_moderators()`)

        Returns
        -------
        dict[str, Any]
            `{"body": <raw HTML string>}`
        """
        module_name = "managesite/ManageSiteModeratorPermissionsModule"
        response = self.site.amc_request([{"moduleName": module_name, "moderatorId": moderator_id}])[0]
        return {"body": require_body(response, module_name)}

    def save_moderator_permissions(self, **fields: Any) -> None:
        """
        Save moderator permissions (`saveModeratorPermissions`)

        **未実測**: `sm-mod-perms-form`'s field names are unknown (see
        `get_moderator_permissions_form`). Pass the exact field names/values
        Wikidot's form uses as keyword arguments; this method does not
        validate, transform, or default them (unlike the typed
        `site.settings.*` methods).

        Parameters
        ----------
        **fields : Any
            Raw form fields to submit verbatim
        """
        self.site.amc_request(
            [
                {
                    "action": "ManageSiteMembershipAction",
                    "event": "saveModeratorPermissions",
                    "moduleName": "Empty",
                    **fields,
                }
            ]
        )

    # ------------------------------------------------------------------
    # Task 2-4: invitations
    # ------------------------------------------------------------------

    def search_users(self, query: str) -> list[UserSearchResult]:
        """
        Search for users to invite (`users/UserSearchModule`)

        Confirmed live 2026-07-29 (see 40_admin-managesite.md): `userIds`
        is a JSON array of IDs, but `userNames` is **not** a parallel
        array -- it's an object keyed by the user ID *as a string*
        (`{"3396310": "ukwhatn", ...}`). There is also no `count` key
        (the initial research's notes were wrong on both points); use
        `len(result)` if a count is needed.

        Parameters
        ----------
        query : str
            Search query (part of a username)

        Returns
        -------
        list[UserSearchResult]
        """
        module_name = "users/UserSearchModule"
        response = self.site.amc_request([{"moduleName": module_name, "query": query}])[0]
        data = response.json()
        ids = data.get("userIds") or []
        names_by_id = data.get("userNames") or {}
        return [UserSearchResult(id=i, name=names_by_id.get(str(i), "")) for i in ids]

    def send_email_invitations(self, addresses: list[tuple[str, str, bool]], message: str = "") -> None:
        """
        Send email invitations to join the site

        Parameters
        ----------
        addresses : list[tuple[str, str, bool]]
            `(email, name, is_contact)` tuples. Encoded as
            `addresses=[[email, name, isContact], ...]` (JSON), matching
            Wikidot's own client
        message : str, default ""
            Message included with the invitation
        """
        body = {
            "addresses": json_param([list(address) for address in addresses]),
            "message": message,
        }
        self.site.amc_request(
            [
                {
                    "action": "ManageSiteMembershipAction",
                    "event": "sendEmailInvitations",
                    "moduleName": "Empty",
                    **body,
                }
            ]
        )

    def delete_email_invitation(self, invitation_id: int) -> None:
        """
        Delete a pending email invitation

        Parameters
        ----------
        invitation_id : int
        """
        self.site.amc_request(
            [
                {
                    "action": "ManageSiteMembershipAction",
                    "event": "deleteEmailInvitation",
                    "invitationId": invitation_id,
                    "moduleName": "Empty",
                }
            ]
        )

    def resend_email_invitation(self, invitation_id: int, message: str = "") -> None:
        """
        Resend a pending email invitation

        Parameters
        ----------
        invitation_id : int
        message : str, default ""
        """
        self.site.amc_request(
            [
                {
                    "action": "ManageSiteMembershipAction",
                    "event": "resendEmailInvitation",
                    "invitationId": invitation_id,
                    "message": message,
                    "moduleName": "Empty",
                }
            ]
        )

    def set_let_users_invite(self, enabled: bool) -> None:
        """
        Allow/disallow regular members to invite others via email

        Parameters
        ----------
        enabled : bool
            Sent as the literal string "true"/"false" (always present, not
            omitted when False -- matches `enableLetUsersInvite(bool)`'s
            plain-boolean notation in 40_admin-managesite.md, the same
            always-sent convention as `site.settings.save_openid`'s
            `enableOpenID`)
        """
        self.site.amc_request(
            [
                {
                    "action": "ManageSiteMembershipAction",
                    "event": "letUsersInviteSave",
                    "enableLetUsersInvite": "true" if enabled else "false",
                    "moduleName": "Empty",
                }
            ]
        )

    def invite_admin(self, user: "AbstractUser | int") -> int | None:
        """
        Invite a user to become a site admin

        Parameters
        ----------
        user : AbstractUser | int
            User to invite (or their user ID)

        Returns
        -------
        int | None
            The invited user's ID, if returned by Wikidot
        """
        response = self.site.amc_request(
            [
                {
                    "action": "ManageSiteAction",
                    "event": "inviteAdmin",
                    "user_id": _user_id(user),
                    "moduleName": "Empty",
                }
            ]
        )[0]
        result = response.json().get("userId")
        return result if isinstance(result, int) else None

    # ------------------------------------------------------------------
    # Task 2-5: user / IP blocks
    # ------------------------------------------------------------------

    def get_blocked_users(self) -> list[UserBlock]:
        """
        Get the list of blocked users

        Returns
        -------
        list[UserBlock]
        """
        module_name = "managesite/blocks/ManageSiteUserBlocksModule"
        response = self.site.amc_request([{"moduleName": module_name}])[0]
        html = BeautifulSoup(require_body(response, module_name), "lxml")
        return UserBlock._parse_all(self.site, html)

    def get_blocked_ips(self) -> list[IpBlock]:
        """
        Get the list of blocked IP addresses/ranges

        Returns
        -------
        list[IpBlock]
        """
        module_name = "managesite/blocks/ManageSiteIpBlocksModule"
        response = self.site.amc_request([{"moduleName": module_name}])[0]
        html = BeautifulSoup(require_body(response, module_name), "lxml")
        return IpBlock._parse_all(self.site, html)

    def block_user(self, user: "AbstractUser | int", reason: str = "") -> None:
        """
        Block a user from the site

        Parameters
        ----------
        user : AbstractUser | int
            User to block (or their user ID)
        reason : str, default ""
            Block reason (200 characters max per Wikidot's form)
        """
        self.site.amc_request(
            [
                {
                    "action": "ManageSiteBlockAction",
                    "event": "blockUser",
                    "userId": _user_id(user),
                    "reason": reason,
                    "moduleName": "Empty",
                }
            ]
        )

    def unblock_user(self, user: "AbstractUser | int") -> None:
        """
        Remove a user block

        Parameters
        ----------
        user : AbstractUser | int
            Blocked user (or their user ID). `deleteBlock`'s `userId` really
            is a user ID (confirmed 2026-07-29 from
            `managesite_blocks_ManageSiteUserBlocksModule.js`) -- do not
            confuse with `unblock_ip`'s `blockId`, which is a block ID
        """
        self.site.amc_request(
            [
                {
                    "action": "ManageSiteBlockAction",
                    "event": "deleteBlock",
                    "userId": _user_id(user),
                    "moduleName": "Empty",
                }
            ]
        )

    def block_ip(self, ips: str, reason: str = "") -> None:
        """
        Block one or more IP addresses/ranges

        Parameters
        ----------
        ips : str
            IP addresses/ranges, one per line (matches the `ips` textarea)
        reason : str, default ""
            Block reason (200 characters max per Wikidot's form)
        """
        self.site.amc_request(
            [
                {
                    "action": "ManageSiteBlockAction",
                    "event": "blockIp",
                    "ips": ips,
                    "reason": reason,
                    "moduleName": "Empty",
                }
            ]
        )

    def unblock_ip(self, block_id: int) -> None:
        """
        Remove an IP block

        Parameters
        ----------
        block_id : int
            Block ID (from `get_blocked_ips()`). `deleteIpBlock`'s `blockId`
            is a block ID, not an IP or user ID -- asymmetric with
            `unblock_user`'s `userId`, do not confuse the two
        """
        self.site.amc_request(
            [
                {
                    "action": "ManageSiteBlockAction",
                    "event": "deleteIpBlock",
                    "blockId": block_id,
                    "moduleName": "Empty",
                }
            ]
        )

    # ------------------------------------------------------------------
    # Task 2-6: abuse-flag clearing / members auto-watching / block-link
    # ------------------------------------------------------------------

    def clear_user_flags(self, user: "AbstractUser | int") -> None:
        """
        Clear abuse flags reported against a user

        Parameters
        ----------
        user : AbstractUser | int
            User to clear (or their user ID)
        """
        self.site.amc_request(
            [
                {
                    "action": "ManageSiteAbuseAction",
                    "event": "clearUserFlags",
                    "userId": _user_id(user),
                    "moduleName": "Empty",
                }
            ]
        )

    def clear_page_flags(self, path: str) -> None:
        """
        Clear abuse flags reported against a page

        Parameters
        ----------
        path : str
            Page path
        """
        self.site.amc_request(
            [{"action": "ManageSiteAbuseAction", "event": "clearPageFlags", "path": path, "moduleName": "Empty"}]
        )

    def clear_anonymous_flags(self, address: str, proxy: bool = False) -> None:
        """
        Clear abuse flags reported against an anonymous (IP) address

        Parameters
        ----------
        address : str
            IP address
        proxy : bool, default False
            Sent as `proxy="yes"` when True (matching the `?("yes")`
            notation in 40_admin-managesite.md, the same value Wikidot uses
            for `removeMember`'s `ban`); omitted when False
        """
        body = omit_falsy(proxy="yes" if proxy else False)
        self.site.amc_request(
            [
                {
                    "action": "ManageSiteAbuseAction",
                    "event": "clearAnonymousFlags",
                    "address": address,
                    "moduleName": "Empty",
                    **body,
                }
            ]
        )

    def set_members_watching(self, watch_all: bool = False, selected_categories: list[int] | None = None) -> None:
        """
        Configure members' automatic watching of new pages

        Parameters
        ----------
        watch_all : bool, default False
            Watch all categories automatically
        selected_categories : list[int] | None, default None
            Category IDs to watch when `watch_all` is False. Sent as
            `selected_categories[]=<id>&...` (the AMC client auto-expands
            list values into bracket notation; see 30_plan.md D2)
        """
        body = omit_falsy(watch_all=checkbox(watch_all))
        if selected_categories is not None:
            body["selected_categories"] = selected_categories
        self.site.amc_request(
            [
                {
                    "action": "ManageSiteMembershipAction",
                    "event": "saveMembersWatching",
                    "moduleName": "Empty",
                    **body,
                }
            ]
        )

    def set_block_link(self, karma_level: int, block_link: bool = False) -> None:
        """
        Configure automatic link-blocking by karma level

        Parameters
        ----------
        karma_level : int
            Karma threshold (0-5)
        block_link : bool, default False
            Whether to actually block links below the threshold
        """
        body = omit_falsy(blockLink=flag(block_link))
        self.site.amc_request(
            [
                {
                    "action": "ManageSiteAction",
                    "event": "saveBlockLink",
                    "karmaLevel": karma_level,
                    "moduleName": "Empty",
                    **body,
                }
            ]
        )
