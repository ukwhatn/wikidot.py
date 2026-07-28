"""
Module for handling the logged-in user's Wikidot account (`www.wikidot.com/account/settings`)

This module provides classes for account-level settings and profile operations
that are distinct from any single site: password/email/language, private message
receive preferences, forum signature, avatar, and API key management.

All requests in this module are sent to `www.wikidot.com` (Client.amc_client's
default host), never to a site's own host.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

from bs4 import BeautifulSoup

from ..common import exceptions
from ..common.decorators import login_required
from ..connector.ajax import require_body
from ..util.amc_body import checkbox, flag, json_param, omit_falsy
from ..util.parser import odate as odate_parser

if TYPE_CHECKING:
    from .client import Client
    from .user import AbstractUser

#: `from` values accepted by DashboardSettingsAction/saveReceiveMessages
PrivateMessageReceiveFrom = Literal["a", "mf", "f", "n"]

#: option keys accepted by userinfo/UserChangesListModule's `options` JSON.
#: Unlike the page-history version (history/PageHistoryModule), there is no
#: "tags" key here.
RECENT_CHANGES_OPTION_KEYS = frozenset({"all", "source", "title", "move", "files", "new", "meta"})


class AccountSettings:
    """
    A class that provides operations on `DashboardSettingsAction` and `dashboard/settings/*`

    Covers account-wide settings: password, email, language, private message
    receive preferences and block list, toolbars, digest/newsletter/invitation
    subscriptions, API key, and Facebook link. Access through Client.account.settings.

    Note that `saveReceiveMessages` / `blockUser` / `deleteBlock` live under this
    action namespace even though they are about private messages: Wikidot groups
    all of DashboardSettingsAction here regardless of topic, so this class owns them
    instead of ClientPrivateMessageAccessor.
    """

    def __init__(self, client: "Client"):
        """
        Initialize method

        Parameters
        ----------
        client : Client
            Parent client instance
        """
        self.client = client

    def _request(self, event: str, **params: Any) -> Any:
        """
        Internal helper to send a DashboardSettingsAction request

        Parameters
        ----------
        event : str
            Event name
        **params : Any
            Additional request parameters

        Returns
        -------
        Any
            Parsed JSON response
        """
        response = self.client.amc_client.request(
            [
                {
                    "action": "DashboardSettingsAction",
                    "event": event,
                    "moduleName": "Empty",
                    **params,
                }
            ]
        )[0]
        return response.json()

    @login_required
    def set_receive_messages(self, from_: PrivateMessageReceiveFrom) -> None:
        """
        Set who is allowed to send you private messages

        Parameters
        ----------
        from_ : Literal["a", "mf", "f", "n"]
            "a" = all registered users, "mf" = co-members + contacts,
            "f" = contacts only, "n" = nobody

        Raises
        ------
        LoginRequiredException
            If not logged in
        FormErrorsException
            If validation fails
        """
        self._request("saveReceiveMessages", **{"from": from_})

    @login_required
    def block_user(self, user: "AbstractUser") -> None:
        """
        Add a user to the private message block list

        Parameters
        ----------
        user : AbstractUser
            User to block

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        self._request("blockUser", userId=user.id)

    @login_required
    def unblock_user(self, user: "AbstractUser") -> None:
        """
        Remove a user from the private message block list

        Parameters
        ----------
        user : AbstractUser
            User to unblock

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        self._request("deleteBlock", userId=user.id)

    @login_required
    def start_email_change(self, email: str) -> None:
        """
        Start the two-step email change flow (step 1)

        Wikidot sends a confirmation code to the new address; complete the
        change with confirm_email_change(evercode).

        Parameters
        ----------
        email : str
            New email address

        Raises
        ------
        LoginRequiredException
            If not logged in
        FormErrorsException
            status "form_error" with a message (single string, not per-field)
        """
        self._request("changeEmail1", email=email)

    @login_required
    def confirm_email_change(self, evercode: str) -> None:
        """
        Complete the two-step email change flow (step 2)

        Parameters
        ----------
        evercode : str
            Confirmation code received by email

        Raises
        ------
        LoginRequiredException
            If not logged in
        FormErrorsException
            status "form_error" with a message (single string, not per-field)
        """
        self._request("changeEmail2", evercode=evercode)

    @login_required
    def change_password(self, old_password: str, new_password: str) -> None:
        """
        Change the account password

        Parameters
        ----------
        old_password : str
            Current password
        new_password : str
            New password (sent twice as new_password1/new_password2, matching
            form(change-password-form))

        Raises
        ------
        LoginRequiredException
            If not logged in
        FormErrorsException
            status "form_error" with a message
        """
        self._request(
            "changePassword",
            old_password=old_password,
            new_password1=new_password,
            new_password2=new_password,
        )

    @login_required
    def set_language(self, language: str) -> None:
        """
        Set the account UI language

        Parameters
        ----------
        language : str
            Language code (e.g. "en", "ja")

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        self._request("saveLanguage", language=language)

    @login_required
    def set_receive_digest(self, receive: bool) -> None:
        """
        Set whether to receive the site activity digest email

        Parameters
        ----------
        receive : bool
            True to subscribe, False to unsubscribe

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        self._request("saveReceiveDigest", **omit_falsy(receive="yes" if receive else False))

    @login_required
    def set_receive_newsletter(self, receive: bool) -> None:
        """
        Set whether to receive the Wikidot newsletter

        Parameters
        ----------
        receive : bool
            True to subscribe, False to unsubscribe

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        self._request("saveReceiveNewsletter", **omit_falsy(receive="yes" if receive else False))

    @login_required
    def set_receive_invitations(self, receive: bool) -> None:
        """
        Set whether to receive site invitations

        Parameters
        ----------
        receive : bool
            True to allow invitations, False to block them

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        self._request("saveReceiveInvitations", **omit_falsy(receive=flag(receive)))

    @login_required
    def set_toolbars(self, top: bool = False, bottom: bool = False) -> None:
        """
        Set which editor toolbars are shown

        Parameters
        ----------
        top : bool, default False
            Show the top toolbar
        bottom : bool, default False
            Show the bottom toolbar

        Raises
        ------
        LoginRequiredException
            If not logged in

        Notes
        -----
        This is `DashboardSettingsAction/saveToolbarsPref` (account-wide editor
        preference). Do not confuse it with `ManageSiteAction/saveToolbarsPref`,
        a same-named event on a per-site settings action.
        """
        self._request(
            "saveToolbarsPref",
            **omit_falsy(toolbarTop=checkbox(top), toolbarBottom=checkbox(bottom)),
        )

    @login_required
    def generate_api_key(self, read_only: bool = False) -> str:
        """
        Regenerate the account's API key

        Parameters
        ----------
        read_only : bool, default False
            True to generate a read-only key. Any other value (including
            omission) generates a read-write key; only the literal "r" means
            read-only on the wire

        Returns
        -------
        str
            The newly generated API key

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        data = self._request("generateApiKey", type="r" if read_only else "w")
        return str(data["newKey"])

    @login_required
    def connect_facebook(self, fb_user: dict[str, Any]) -> dict[str, Any]:
        """
        Link the account with a Facebook account

        Parameters
        ----------
        fb_user : dict[str, Any]
            Facebook user object, sent using bracket notation
            (e.g. fbUser[id]=..., fbUser[name]=...)

        Returns
        -------
        dict[str, Any]
            The "fbaccount" field of the response

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        data = self._request("connectWithFacebook", fbUser=fb_user)
        return dict(data["fbaccount"])

    @login_required
    def disconnect_facebook(self) -> None:
        """
        Unlink the account from Facebook

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        self._request("disconnectWithFacebook")

    # ------------------------------------------------------------------
    # Raw module fetches (dashboard/settings/*)
    #
    # These mirror the tabs of the /account/settings dashboard and exist for
    # completeness with the module catalog; most of their state is more
    # conveniently read/written through the action methods above. They
    # return the raw rendered HTML body rather than a parsed structure,
    # since only the request/response envelope (not per-tab markup) was
    # measured during the investigation.
    # ------------------------------------------------------------------

    def _fetch(self, module_name: str) -> str:
        """
        Internal helper to fetch a dashboard/settings/* module's rendered HTML

        Parameters
        ----------
        module_name : str
            Module name to fetch

        Returns
        -------
        str
            Raw rendered HTML body
        """
        response = self.client.amc_client.request([{"moduleName": module_name}])[0]
        return require_body(response, module_name)

    @login_required
    def get_account_html(self) -> str:
        """Fetch the raw HTML of dashboard/settings/DSAccountModule (`#/account`)."""
        return self._fetch("dashboard/settings/DSAccountModule")

    @login_required
    def get_about_html(self) -> str:
        """Fetch the raw HTML of dashboard/settings/DSAboutModule (`#/about`)."""
        return self._fetch("dashboard/settings/DSAboutModule")

    @login_required
    def get_forum_signature_html(self) -> str:
        """Fetch the raw HTML of dashboard/settings/DSForumSignatureModule (`#/forumsignature`)."""
        return self._fetch("dashboard/settings/DSForumSignatureModule")

    @login_required
    def get_toolbars_html(self) -> str:
        """Fetch the raw HTML of dashboard/settings/DSToolbarsModule (`#/toolbars`)."""
        return self._fetch("dashboard/settings/DSToolbarsModule")

    @login_required
    def get_newsletter_html(self) -> str:
        """Fetch the raw HTML of dashboard/settings/DSNewsletterModule (`#/newsletter`)."""
        return self._fetch("dashboard/settings/DSNewsletterModule")

    @login_required
    def get_messages_html(self) -> str:
        """
        Fetch the raw HTML of dashboard/settings/DSMessagesModule (`#/messages`)

        This is also the module used to re-render the PM settings tab after
        set_receive_messages()/block_user()/unblock_user(). Do not confuse
        with dashboard/messages/DMSettingsModule (the `/account/messages#/settings`
        tab), which is a different module that renders the same UI from the
        messages hub and returned an empty body when measured.
        """
        return self._fetch("dashboard/settings/DSMessagesModule")

    @login_required
    def get_invitations_html(self) -> str:
        """Fetch the raw HTML of dashboard/settings/DSInvitationsModule (`#/invitations`)."""
        return self._fetch("dashboard/settings/DSInvitationsModule")

    @login_required
    def get_facebook_html(self) -> str:
        """Fetch the raw HTML of dashboard/settings/DSFacebookModule (`#/facebook`)."""
        return self._fetch("dashboard/settings/DSFacebookModule")

    @login_required
    def get_visibility_html(self) -> str:
        """
        Fetch the raw HTML of dashboard/settings/DSVisibilityModule (`#/visibility`)

        Unmeasured: in the investigation this module returned status
        "no_permission" for a non-Pro account, so its availability on
        free accounts is unconfirmed.
        """
        return self._fetch("dashboard/settings/DSVisibilityModule")

    @login_required
    def get_api_html(self) -> str:
        """Fetch the raw HTML of dashboard/settings/DSApiModule (`#/api`)."""
        return self._fetch("dashboard/settings/DSApiModule")


class AccountProfile:
    """
    A class that provides operations on `DashboardProfileAction`

    Covers the public profile: display name, "about" bio, forum signature,
    profile visibility, and avatar. Access through Client.account.profile.
    """

    def __init__(self, client: "Client"):
        """
        Initialize method

        Parameters
        ----------
        client : Client
            Parent client instance
        """
        self.client = client

    def _request(self, event: str, **params: Any) -> Any:
        """
        Internal helper to send a DashboardProfileAction request

        Parameters
        ----------
        event : str
            Event name
        **params : Any
            Additional request parameters

        Returns
        -------
        Any
            Parsed JSON response
        """
        response = self.client.amc_client.request(
            [
                {
                    "action": "DashboardProfileAction",
                    "event": event,
                    "moduleName": "Empty",
                    **params,
                }
            ]
        )[0]
        return response.json()

    @login_required
    def change_screen_name(self, screen_name: str) -> None:
        """
        Change the account's display (screen) name

        Parameters
        ----------
        screen_name : str
            New display name

        Raises
        ------
        LoginRequiredException
            If not logged in
        FormErrorsException
            If validation fails
        """
        self._request("changeScreenName", screenName=screen_name)

    @login_required
    def save_about(
        self,
        real_name: str = "",
        gender: Literal["m", "f"] | None = None,
        birthday_day: str = "",
        birthday_month: str = "",
        birthday_year: str = "",
        about: str = "",
        website: str = "",
        im_aim: str = "",
        im_gadu_gadu: str = "",
        im_google_talk: str = "",
        im_icq: str = "",
        im_jabber: str = "",
        im_msn: str = "",
        im_yahoo: str = "",
        location: str = "",
    ) -> None:
        """
        Save the "about" section of the profile (form(dp-about-form))

        Parameters
        ----------
        real_name : str, default ""
            Real name
        gender : Literal["m", "f"] | None, default None
            Gender. None omits the field (matches the empty radio state)
        birthday_day, birthday_month, birthday_year : str, default ""
            Birthday, sent as separate select/text fields as on the form
        about : str, default ""
            Free-text bio. The web form caps this at 200 characters; this
            method does not enforce that client-side, so an over-length
            value surfaces as FormErrorsException from the server
        website : str, default ""
            Personal website URL
        im_aim, im_gadu_gadu, im_google_talk, im_icq, im_jabber, im_msn, im_yahoo : str, default ""
            Instant messenger handles
        location : str, default ""
            Location text

        Raises
        ------
        LoginRequiredException
            If not logged in
        FormErrorsException
            If validation fails (e.g. `about` over 200 characters)
        """
        self._request(
            "saveAbout",
            **omit_falsy(
                real_name=real_name,
                gender=gender,
                birthday_day=birthday_day,
                birthday_month=birthday_month,
                birthday_year=birthday_year,
                about=about,
                website=website,
                im_aim=im_aim,
                im_gadu_gadu=im_gadu_gadu,
                im_google_talk=im_google_talk,
                im_icq=im_icq,
                im_jabber=im_jabber,
                im_msn=im_msn,
                im_yahoo=im_yahoo,
                location=location,
            ),
        )

    @login_required
    def save_forum_signature(self, source: str) -> None:
        """
        Save the forum post signature

        Parameters
        ----------
        source : str
            Signature source (Wikidot markup). The web form caps this at 400
            characters; this method does not enforce that client-side, so an
            over-length value surfaces as FormErrorsException from the server

        Raises
        ------
        LoginRequiredException
            If not logged in
        FormErrorsException
            If validation fails (e.g. over 400 characters)
        """
        self._request("saveForumSignature", source=source)

    @login_required
    def preview_forum_signature(self, source: str) -> str:
        """
        Render a preview of a forum signature without saving it

        Parameters
        ----------
        source : str
            Signature source to preview

        Returns
        -------
        str
            Rendered HTML preview

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        response = self.client.amc_client.request(
            [{"moduleName": "dashboard/settings/DSForumSignaturePreviewModule", "source": source}]
        )[0]
        return require_body(response, "dashboard/settings/DSForumSignaturePreviewModule")

    @login_required
    def save_profile_visibility(self, raw_fields: dict[str, Any]) -> None:
        """
        Save profile visibility settings (form(ap-provilev-form))

        Unmeasured: `dashboard/settings/DSVisibilityModule` returned
        status "no_permission" for a non-Pro account during the
        investigation, so the field names of ap-provilev-form (note: "provilev"
        is the site's own typo, not corrected here) could not be captured.
        Pass the exact field names/values as sent by the real form.

        Parameters
        ----------
        raw_fields : dict[str, Any]
            Raw form fields to send as-is

        Raises
        ------
        LoginRequiredException
            If not logged in
        ForbiddenException
            If the account has no permission (observed on non-Pro accounts)
        """
        self._request("saveProfileVisibility", **raw_fields)

    @login_required
    def delete_avatar(self) -> None:
        """
        Delete the account's avatar image

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        self._request("deleteAvatar")

    @login_required
    def upload_avatar_from_uri(self, uri: str) -> dict[str, Any]:
        """
        Set the account's avatar from an image URL

        Parameters
        ----------
        uri : str
            URL of the image to use as the new avatar

        Returns
        -------
        dict[str, Any]
            Response containing "status", "im48", "im16" (avatar URLs at
            each size)

        Raises
        ------
        LoginRequiredException
            If not logged in
        """
        data = self._request("uploadAvatarUri", uri=uri)
        return dict(data)


@dataclass
class UserChange:
    """
    A row of the account's own recent page edits (userinfo/UserChangesListModule)

    Nearly identical in structure to SiteChange (site.py's
    changes/SiteChangesListModule row), with a site column added since this
    view spans every site the account belongs to (measured 2026-07-29, see
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
        Fullname of the changed page
    page_title : str
        Title of the changed page
    revision_no : int
        Revision number
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
    A row of the account's own recent forum posts (userinfo/UserRecentPostsListModule)

    Row markup was measured 2026-07-29 (see `70_account.md` "一覧モジュールの
    行マークアップ"): each row is `div.post`, with
    `div.long > div.head > div.title > a` (title/link), `div.info > span.odate`
    (date), and `div.content` (post text).

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
    """

    client: "Client"
    title: str
    url: str
    created_at: datetime
    content: str

    def __str__(self) -> str:
        """
        String representation of the object

        Returns
        -------
        str
            String representation of the post
        """
        return f"RecentPost(title={self.title}, created_at={self.created_at})"


class AccountRecentActivity:
    """
    A class that provides operations on the `/account/recent` dashboard tab

    Covers the logged-in account's own recent page edits and forum posts,
    across all sites it belongs to. Access through Client.account.recent.
    """

    def __init__(self, client: "Client"):
        """
        Initialize method

        Parameters
        ----------
        client : Client
            Parent client instance
        """
        self.client = client
        self._changes_user_id_cache: int | None = None
        self._posts_user_id_cache: int | None = None

    def _fetch_hidden_user_id(self, module_name: str, element_id: str) -> int:
        """
        Internal helper to fetch a hidden `userId` field from a shell module

        `www.wikidot.com` pages do not expose `WIKIREQUEST.info.userId`
        (unlike a site's own pages), and userinfo/UserChangesListModule /
        userinfo/UserRecentPostsListModule respond with status "not_ok" and
        an empty body if `userId` is omitted. The real UI reads it from a
        hidden input on the shell module that renders the tab
        (userinfo/UserChangesModule / userinfo/UserRecentPostsModule) before
        requesting the list module.

        Parameters
        ----------
        module_name : str
            Shell module to fetch ("userinfo/UserChangesModule" or
            "userinfo/UserRecentPostsModule")
        element_id : str
            id of the hidden input holding the user ID
            ("changes-user-id" or "recent-posts-user-id")

        Returns
        -------
        int
            The account's own user ID

        Raises
        ------
        UnexpectedException
            If the hidden field is missing or non-numeric
        """
        response = self.client.amc_client.request([{"moduleName": module_name}])[0]
        html = BeautifulSoup(require_body(response, module_name), "lxml")
        hidden = html.select_one(f"#{element_id}")
        if hidden is None:
            raise exceptions.UnexpectedException(f"Cannot find #{element_id} in {module_name}")
        value = hidden.get("value")
        if value is None or not str(value).isdigit():
            raise exceptions.UnexpectedException(f"#{element_id} in {module_name} is not numeric: {value!r}")
        return int(str(value))

    def _changes_user_id(self) -> int:
        """
        Internal helper to get (and cache) the userId for UserChangesListModule

        Returns
        -------
        int
            User ID, as read from userinfo/UserChangesModule's
            #changes-user-id hidden field
        """
        if self._changes_user_id_cache is None:
            self._changes_user_id_cache = self._fetch_hidden_user_id("userinfo/UserChangesModule", "changes-user-id")
        return self._changes_user_id_cache

    def _posts_user_id(self) -> int:
        """
        Internal helper to get (and cache) the userId for UserRecentPostsListModule

        Returns
        -------
        int
            User ID, as read from userinfo/UserRecentPostsModule's
            #recent-posts-user-id hidden field
        """
        if self._posts_user_id_cache is None:
            self._posts_user_id_cache = self._fetch_hidden_user_id(
                "userinfo/UserRecentPostsModule", "recent-posts-user-id"
            )
        return self._posts_user_id_cache

    @login_required
    def get_changes(
        self,
        options: dict[str, bool] | None = None,
        limit: int | None = None,
    ) -> list["UserChange"]:
        """
        Get the account's own recent page edits, across all sites

        Wraps `userinfo/UserChangesListModule`, fetching pages until
        exhausted or `limit` is reached.

        Parameters
        ----------
        options : dict[str, bool] | None, default None
            Filter flags. Keys must be a subset of RECENT_CHANGES_OPTION_KEYS
            ("all", "source", "title", "move", "files", "new", "meta"); unlike
            history/PageHistoryModule's options, there is no "tags" key here
        limit : int | None, default None
            Maximum number of entries to retrieve. If None, retrieves all

        Returns
        -------
        list[UserChange]
            List of change history (in descending order by date)

        Raises
        ------
        LoginRequiredException
            If not logged in
        ValueError
            If options contains a key outside RECENT_CHANGES_OPTION_KEYS
        NoElementException
            If HTML element parsing fails
        """
        if options is not None:
            unknown = set(options) - RECENT_CHANGES_OPTION_KEYS
            if unknown:
                raise ValueError(
                    f"Unknown options for userinfo/UserChangesListModule "
                    f"(no 'tags' key here, unlike page-history options): {sorted(unknown)}"
                )

        user_id = self._changes_user_id()

        changes: list[UserChange] = []
        per_page = min(limit, 1000) if limit is not None else 1000
        page_no = 1

        while True:
            response = self.client.amc_client.request(
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
                site_elem = item.select_one("td.site a")

                title_elem = item.select_one("td.title a")
                if title_elem is None:
                    raise exceptions.NoElementException("Title element is not found.")
                page_title = title_elem.get_text().strip()
                href = title_elem.get("href", "")
                page_fullname = str(href).strip("/")

                odate_elem = item.select_one("td.mod-date span.odate")
                if odate_elem is None:
                    raise exceptions.NoElementException("Odate element is not found.")
                changed_at = odate_parser(odate_elem)

                rev_elem = item.select_one("td.revision-no")
                if rev_elem is None:
                    raise exceptions.NoElementException("Revision number element is not found.")
                rev_match = re.search(r"(\d+)", rev_elem.get_text())
                if rev_match is None:
                    raise exceptions.NoElementException("Revision number is not found.")
                revision_no = int(rev_match.group(1))

                flags_elem = item.select("td.flags span.spantip")
                flags = [span.get_text().strip() for span in flags_elem]

                changes.append(
                    UserChange(
                        client=self.client,
                        site_title=site_elem.get_text().strip() if site_elem else "",
                        site_url=str(site_elem.get("href", "")) if site_elem else "",
                        page_fullname=page_fullname,
                        page_title=page_title,
                        revision_no=revision_no,
                        changed_at=changed_at,
                        flags=flags,
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

    @login_required
    def get_posts(self, limit: int | None = None) -> list["RecentPost"]:
        """
        Get the account's own recent forum posts, across all sites

        Wraps `userinfo/UserRecentPostsListModule`, fetching pages until
        exhausted or `limit` is reached.

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
        LoginRequiredException
            If not logged in
        NoElementException
            If HTML element parsing fails
        """
        user_id = self._posts_user_id()

        posts: list[RecentPost] = []
        page_no = 1

        while True:
            response = self.client.amc_client.request(
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
                title_elem = item.select_one("div.long div.head div.title a")
                if title_elem is None:
                    raise exceptions.NoElementException("Title element is not found.")

                odate_elem = item.select_one("div.info span.odate")
                content_elem = item.select_one("div.content")

                posts.append(
                    RecentPost(
                        client=self.client,
                        title=title_elem.get_text().strip(),
                        url=str(title_elem.get("href", "")),
                        created_at=(odate_parser(odate_elem) if odate_elem else datetime.fromtimestamp(0)),
                        content=content_elem.get_text().strip() if content_elem else "",
                    )
                )

                if limit is not None and len(posts) >= limit:
                    return posts

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

        return posts


class ClientAccountAccessor:
    """
    A class that provides account-level (Dashboard) settings/profile operations

    Associated with a client instance, provides access to the sub-accessors
    covering the /account/settings and /account/recent dashboards. Access
    through the Client.account property.
    """

    def __init__(self, client: "Client"):
        """
        Initialize method

        Parameters
        ----------
        client : Client
            Parent client instance
        """
        self.client = client
        self.settings = AccountSettings(client)
        self.profile = AccountProfile(client)
        self.recent = AccountRecentActivity(client)
