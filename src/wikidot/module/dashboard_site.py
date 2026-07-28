"""
Module for handling the logged-in user's own sites and site invitations
(`www.wikidot.com/account/sites`)

These operations act on the current account's relationship to sites --
creating a new site, listing sites the account belongs to, accepting or
discarding invitations, and resigning from a role -- as distinct from
`Site`, which represents operations performed *within* a single already-
identified site. Some targets here (a pending invitation, a deleted site)
have no accessible `Site` object yet, so these are modeled as standalone
functions taking raw IDs rather than methods on a resource dataclass.

All requests are sent to `www.wikidot.com` (Client.amc_client's default
host), never to a site's own host.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from bs4 import BeautifulSoup

from ..common.decorators import login_required
from ..connector.ajax import require_body
from ..util.amc_body import checkbox, omit_falsy

if TYPE_CHECKING:
    from .client import Client

#: `template` values accepted by NewSiteAction/createSite (form(new-site-form))
NewSiteTemplate = Literal[
    "standard-template",
    "blog-template",
    "blank-template",
    "default-template",
    "notebooks",
]

#: `privacy` values accepted by NewSiteAction/createSite (form(new-site-form))
NewSitePrivacy = Literal["open", "closed", "private"]


@dataclass
class DashboardSite:
    """
    A row of the account's site dashboard listing (dashboard/sites/DSListModule)

    Represents the current account's relationship to one site (any role, or a
    site it once belonged to but is now deleted). Distinct from `Site`, which
    represents a site's own state independent of any particular account.

    Row markup was measured 2026-07-29 (see `70_account.md` "一覧モジュールの
    行マークアップ"): each row is `div.site`, with `div.name > a` (title),
    `div.url` (site URL), and a `div.data` block holding `span.activity`,
    `span.site-id`, `span.unix-name`, `span.tagline`, `span.deleted`,
    `span.occupation`. The measurement captured the DOM skeleton but not the
    exact value encoding of every field, so `activity` and `role` are kept as
    the raw observed text rather than a guessed enum/unit.

    Attributes
    ----------
    client : Client
        Client instance
    site_id : int
        Site ID (span.site-id)
    title : str
        Site title (text of div.name > a)
    url : str
        Site URL (text of div.url)
    unix_name : str
        Site UNIX name (span.unix-name)
    tagline : str
        Site tagline/subtitle (span.tagline)
    activity : str
        Raw text of span.activity. Exact meaning/unit was not confirmed during
        the investigation
    role : str
        Raw text of span.occupation. Observed values are expected to align
        with the hash-tab identifiers used elsewhere on this page
        ("master_admin" / "admin" / "moderator" / "member"), but this
        correspondence was not independently confirmed
    deleted : bool
        Whether span.deleted is present in this row's div.data block
    """

    client: "Client"
    site_id: int
    title: str
    url: str
    unix_name: str
    tagline: str
    activity: str
    role: str
    deleted: bool

    def __str__(self) -> str:
        """
        String representation of the object

        Returns
        -------
        str
            String representation of the dashboard site row
        """
        return f"DashboardSite(site_id={self.site_id}, title={self.title}, role={self.role}, deleted={self.deleted})"

    def restore(self, confirm_site_name: str) -> None:
        """
        Restore this site (must currently be deleted)

        Parameters
        ----------
        confirm_site_name : str
            Site name, required as a typed confirmation

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        DashboardSites.restore_site(self.client, self.site_id, confirm_site_name)

    def resign_as_admin(self) -> None:
        """
        Resign the account's admin role on this site

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        DashboardSites.resign_as_admin(self.client, self.site_id)

    def resign_as_moderator(self) -> None:
        """
        Resign the account's moderator role on this site

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        DashboardSites.resign_as_moderator(self.client, self.site_id)

    def sign_off_as_member(self) -> None:
        """
        Leave this site (account must be a plain member)

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        DashboardSites.sign_off_as_member(self.client, self.site_id)

    def set_storage_limit(self, raw_fields: dict[str, Any]) -> None:
        """
        Set this site's file storage limit

        Unmeasured: see DashboardSites.set_storage_limit for details.

        Parameters
        ----------
        raw_fields : dict[str, Any]
            Raw form fields to send as-is

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        DashboardSites.set_storage_limit(self.client, self.site_id, raw_fields)

    @staticmethod
    def _parse_row(client: "Client", row: Any) -> "DashboardSite | None":
        """
        Internal method to parse a single dashboard/sites/DSListModule row

        Parameters
        ----------
        client : Client
            Client instance
        row : bs4.Tag
            `div.site` element to parse

        Returns
        -------
        DashboardSite | None
            Parsed row, or None if a required element is missing
        """
        name_link = row.select_one("div.name > a")
        url_elem = row.select_one("div.url")
        site_id_elem = row.select_one("span.site-id")
        unix_name_elem = row.select_one("span.unix-name")
        tagline_elem = row.select_one("span.tagline")
        activity_elem = row.select_one("span.activity")
        role_elem = row.select_one("span.occupation")
        deleted_elem = row.select_one("span.deleted")

        if name_link is None or site_id_elem is None or unix_name_elem is None:
            return None

        site_id_text = site_id_elem.get_text().strip()
        if not site_id_text.isdigit():
            return None

        return DashboardSite(
            client=client,
            site_id=int(site_id_text),
            title=name_link.get_text().strip(),
            url=url_elem.get_text().strip() if url_elem else "",
            unix_name=unix_name_elem.get_text().strip(),
            tagline=tagline_elem.get_text().strip() if tagline_elem else "",
            activity=activity_elem.get_text().strip() if activity_elem else "",
            role=role_elem.get_text().strip() if role_elem else "",
            deleted=deleted_elem is not None,
        )

    @staticmethod
    @login_required
    def acquire_all(client: "Client") -> list["DashboardSite"]:
        """
        Retrieve every site the account belongs to (all roles) plus deleted sites

        Wraps dashboard/sites/DSListModule, which renders the full list in one
        response (the real UI filters by role/deleted client-side via DOM
        attributes rather than separate requests).

        Parameters
        ----------
        client : Client
            Client instance

        Returns
        -------
        list[DashboardSite]
            All rows of the account's site dashboard

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        response = client.amc_client.request([{"moduleName": "dashboard/sites/DSListModule"}])[0]
        html = BeautifulSoup(require_body(response, "dashboard/sites/DSListModule"), "lxml")

        sites = []
        for row in html.select("div.site"):
            site = DashboardSite._parse_row(client, row)
            if site is not None:
                sites.append(site)
        return sites


class DashboardSites:
    """
    A class that provides operations on `DashboardSitesAction` / `NewSiteAction` /
    `dashboard/sites/*`

    Static namespace grouping the account's site-dashboard operations. Access
    through Client.site (create/list/accept_invitation/...) rather than
    instantiating this class directly.
    """

    @staticmethod
    @login_required
    def create(
        client: "Client",
        name: str,
        unixname: str,
        subtitle: str = "",
        language: str = "en",
        template: NewSiteTemplate = "standard-template",
        privacy: NewSitePrivacy = "open",
        tos: bool = True,
    ) -> str:
        """
        Create a new site (form(new-site-form) -> NewSiteAction/createSite)

        Parameters
        ----------
        client : Client
            Client instance
        name : str
            Site title
        unixname : str
            Site UNIX name (used in the domain, e.g. "foo" -> foo.wikidot.com)
        subtitle : str, default ""
            Site subtitle
        language : str, default "en"
            Site language code
        template : NewSiteTemplate, default "standard-template"
            Starting content template
        privacy : NewSitePrivacy, default "open"
            Site visibility ("open", "closed", or "private")
        tos : bool, default True
            Whether to accept the Terms of Service. The real form requires
            this checked to submit; sending False reproduces the unchecked
            (omitted) wire state

        Returns
        -------
        str
            UNIX name of the created site (the "siteUnixName" response field)

        Raises
        ------
        LoginRequiredException
            If not logged in
        FormErrorsException
            If validation fails (e.g. unixname already taken)
        """
        response = client.amc_client.request(
            [
                {
                    "action": "NewSiteAction",
                    "event": "createSite",
                    "moduleName": "Empty",
                    "name": name,
                    "subtitle": subtitle,
                    "unixname": unixname,
                    "language": language,
                    "template": template,
                    "privacy": privacy,
                    **omit_falsy(tos=checkbox(tos)),
                }
            ]
        )[0]
        return str(response.json()["siteUnixName"])

    @staticmethod
    def list_sites(client: "Client") -> list[DashboardSite]:
        """
        Retrieve every site the account belongs to (all roles) plus deleted sites

        Parameters
        ----------
        client : Client
            Client instance

        Returns
        -------
        list[DashboardSite]
            All rows of the account's site dashboard

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        return DashboardSite.acquire_all(client)

    @staticmethod
    @login_required
    def accept_invitation(client: "Client", invitation_id: int) -> None:
        """
        Accept a pending site invitation

        Parameters
        ----------
        client : Client
            Client instance
        invitation_id : int
            Invitation ID (as listed by dashboard/messages/DMInvitationsModule)

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        client.amc_client.request(
            [
                {
                    "action": "DashboardSitesAction",
                    "event": "acceptInvitation",
                    "invitation_id": invitation_id,
                    "moduleName": "Empty",
                }
            ]
        )

    @staticmethod
    @login_required
    def throw_away_invitation(client: "Client", invitation_id: int) -> None:
        """
        Discard a pending site invitation without accepting it

        Parameters
        ----------
        client : Client
            Client instance
        invitation_id : int
            Invitation ID

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        client.amc_client.request(
            [
                {
                    "action": "DashboardSitesAction",
                    "event": "throwAwayInvitation",
                    "invitation_id": invitation_id,
                    "moduleName": "Empty",
                }
            ]
        )

    @staticmethod
    @login_required
    def remove_application(client: "Client", site_id: int) -> None:
        """
        Withdraw a pending membership application the account submitted to a site

        Parameters
        ----------
        client : Client
            Client instance
        site_id : int
            ID of the site the application was submitted to

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        client.amc_client.request(
            [
                {
                    "action": "DashboardSitesAction",
                    "event": "removeApplication",
                    "site_id": site_id,
                    "moduleName": "Empty",
                }
            ]
        )

    @staticmethod
    @login_required
    def restore_site(client: "Client", site_id: int, confirm_site_name: str) -> None:
        """
        Restore a deleted site the account administers

        Parameters
        ----------
        client : Client
            Client instance
        site_id : int
            ID of the deleted site
        confirm_site_name : str
            Site name, required by form(ds-restore-site-form) as a typed
            confirmation (mirrors the real UI's "type the site name" guard)

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        client.amc_client.request(
            [
                {
                    "action": "DashboardSitesAction",
                    "event": "restoreSite",
                    "site_id": site_id,
                    "site_name": confirm_site_name,
                    "moduleName": "Empty",
                }
            ]
        )

    @staticmethod
    @login_required
    def resign_as_admin(client: "Client", site_id: int) -> None:
        """
        Resign the account's admin role on a site (form(ds-admin-resign-form))

        Parameters
        ----------
        client : Client
            Client instance
        site_id : int
            Site ID

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        client.amc_client.request(
            [
                {
                    "action": "DashboardSitesAction",
                    "event": "adminResign",
                    "site_id": site_id,
                    "moduleName": "Empty",
                }
            ]
        )

    @staticmethod
    @login_required
    def resign_as_moderator(client: "Client", site_id: int) -> None:
        """
        Resign the account's moderator role on a site (form(ds-moderator-resign-form))

        Parameters
        ----------
        client : Client
            Client instance
        site_id : int
            Site ID

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        client.amc_client.request(
            [
                {
                    "action": "DashboardSitesAction",
                    "event": "moderatorResign",
                    "site_id": site_id,
                    "moduleName": "Empty",
                }
            ]
        )

    @staticmethod
    @login_required
    def sign_off_as_member(client: "Client", site_id: int) -> None:
        """
        Leave a site the account is a plain member of (form(ds-member-signoff-form))

        Parameters
        ----------
        client : Client
            Client instance
        site_id : int
            Site ID

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        client.amc_client.request(
            [
                {
                    "action": "DashboardSitesAction",
                    "event": "memberSignOff",
                    "site_id": site_id,
                    "moduleName": "Empty",
                }
            ]
        )

    @staticmethod
    @login_required
    def set_storage_limit(client: "Client", site_id: int, raw_fields: dict[str, Any]) -> None:
        """
        Set a site's file storage limit (form(limit-site-<siteId>))

        Unmeasured: dashboard/sites/DSListModule did not render this form
        for the investigation account (no Pro site available), so the field
        names of limit-site-<siteId> could not be captured. Pass the exact
        field names/values as sent by the real form.

        Parameters
        ----------
        client : Client
            Client instance
        site_id : int
            Site ID
        raw_fields : dict[str, Any]
            Raw form fields to send as-is

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        client.amc_client.request(
            [
                {
                    "action": "DashboardSitesAction",
                    "event": "setStorageLimit",
                    "site_id": site_id,
                    "moduleName": "Empty",
                    **raw_fields,
                }
            ]
        )
