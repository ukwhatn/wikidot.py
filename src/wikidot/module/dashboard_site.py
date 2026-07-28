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

from typing import TYPE_CHECKING, Any, Literal

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
    @login_required
    def list_html(client: "Client") -> str:
        """
        Fetch the raw HTML of dashboard/sites/DSListModule

        Renders every site the account belongs to (all roles) plus deleted
        sites in one response; the real UI filters by role/deleted client-side
        via DOM attributes rather than separate requests. Row markup detail
        (site id/unix name/role attributes) was not captured during the
        investigation, so this returns the raw body rather than a parsed list.

        Parameters
        ----------
        client : Client
            Client instance

        Returns
        -------
        str
            Raw rendered HTML body

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        response = client.amc_client.request([{"moduleName": "dashboard/sites/DSListModule"}])[0]
        return require_body(response, "dashboard/sites/DSListModule")

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
