"""
Module for Wikidot's site-wide settings (Manage Site's `_admin` panel)

Access through `Site.settings`. Methods are grouped following
31_tasks.md's P1 breakdown:

- `update_categories`: the read-modify-write primitive for the seven
  `categories`-backed areas (Task 1-1)
- Permissions / License / Navigation / Templates / PageRate /
  PerPageDiscussion / Appearance: thin wrappers over `update_categories`
  (Task 1-4)
- General / Domain / Access policy: standalone form saves (Task 1-3)
- Everything else (CustomFooter / Toolbars / GoogleAnalytics /
  Autonumerate / Pingbacks / API / OpenID / Backup / Icons / Newsletter):
  single-shot settings (Task 1-5)

Only the *save* side is implemented for General/Domain/Access policy.
Reading the current values back would require scraping the rendered
`sm-general-form` / `sm-private-form` / `sm-domain` HTML, and the survey
this plan is based on did not capture a real HTML sample for those forms
(only the field name/type list in 35_form-fields.md) — see the P1
completion report for this as a flagged, deliberate scope decision rather
than a silent omission.
"""

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Literal

from ..util.amc_body import checkbox, flag, json_param, omit_falsy
from .site_category import SiteCategoryCollection, SiteLicense
from .site_permissions import PagePermissions, RatingSettings

if TYPE_CHECKING:
    from .site import Site
    from .user import AbstractUser


#: Module names that render each categories-backed settings area. Each of
#: these embeds the site's full `categories` array (same 24-field schema;
#: see 40_admin-managesite.md), so update_categories fetches from the
#: module matching the area being changed rather than a single fixed one
#: — a module that only echoes back a subset of fields would otherwise
#: cause the categories round trip (SiteCategory._raw, see D3) to lose
#: the fields it didn't include on the next save of a *different* area.
_MODULE_PERMISSIONS = "managesite/ManageSitePermissionsModule"
_MODULE_LICENSE = "managesite/ManageSiteLicenseModule"
_MODULE_NAVIGATION = "managesite/ManageSiteNavigationModule"
_MODULE_TEMPLATES = "managesite/ManageSiteTemplatesModule"
_MODULE_PAGE_RATE = "managesite/pagerate/ManageSitePageRateSettingsModule"
_MODULE_PER_PAGE_DISCUSSION = "managesite/ManageSitePerPageDiscussionModule"
_MODULE_APPEARANCE = "managesite/themes/ManageSiteAppearanceModule"


class SiteSettingsAccessor:
    """
    Accessor for Manage Site (`_admin`) settings

    Access through `Site.settings`.
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
    # Task 1-1: categories read-modify-write primitive
    # ------------------------------------------------------------------

    def update_categories(
        self,
        module_name: str,
        action: str,
        event: str,
        mutator: Callable[[SiteCategoryCollection], None],
    ) -> None:
        """
        Fetch the current `categories` array, mutate it, and save it back

        This is the single place that performs the categories
        read-modify-write cycle; every method below that touches
        `categories` (Permissions / License / Navigation / Templates /
        PageRate / PerPageDiscussion / Appearance) is a thin wrapper over
        this. The array is always re-fetched here (never cached), because
        a partial-update API does not exist and holding a stale snapshot
        risks reverting another admin's concurrent change.

        Parameters
        ----------
        module_name : str
            Manage Site module to fetch the `categories` array from before
            mutating (e.g. "managesite/ManageSitePermissionsModule").
            Matches the module that would render the area being changed —
            it is unconfirmed whether every categories-rendering module
            echoes back the same full 24-field schema, so this fetches
            from the module for the area actually being saved rather than
            a single fixed one
        action : str
            AMC action for the save request (e.g. "ManageSiteAction")
        event : str
            AMC event for the save request (e.g. "savePermissions")
        mutator : Callable[[SiteCategoryCollection], None]
            Called with the freshly fetched collection; mutate categories
            in place

        Examples
        --------
        >>> site.settings.update_categories(
        ...     "managesite/ManageSitePermissionsModule",
        ...     "ManageSiteAction", "savePermissions",
        ...     lambda cats: cats["_default"].set_permissions(
        ...         view={"anonymous", "registered", "member"}
        ...     ),
        ... )
        """
        collection = SiteCategoryCollection.fetch(self.site, module_name)
        mutator(collection)
        collection.save(action, event)

    # ------------------------------------------------------------------
    # Task 1-4: categories-backed settings
    # ------------------------------------------------------------------

    def set_page_permissions(self, category_name: str, permissions: PagePermissions) -> None:
        """
        Set explicit page permissions for a category

        Parameters
        ----------
        category_name : str
            Category name (e.g. "_default")
        permissions : PagePermissions
            New permissions. Clears the category's `permissions_default`
            flag (it stops inheriting the site default)
        """

        def mutator(cats: SiteCategoryCollection) -> None:
            category = cats[category_name]
            category.permissions = permissions
            category.permissions_default = False

        self.update_categories(_MODULE_PERMISSIONS, "ManageSiteAction", "savePermissions", mutator)

    def use_default_page_permissions(self, category_name: str) -> None:
        """
        Make a category inherit the site's default page permissions

        Parameters
        ----------
        category_name : str
            Category name
        """

        def mutator(cats: SiteCategoryCollection) -> None:
            category = cats[category_name]
            category.permissions = None
            category.permissions_default = True

        self.update_categories(_MODULE_PERMISSIONS, "ManageSiteAction", "savePermissions", mutator)

    def set_license(self, category_name: str, license: SiteLicense, other: str = "") -> None:
        """
        Set an explicit license for a category

        Parameters
        ----------
        category_name : str
            Category name
        license : SiteLicense
            License to apply
        other : str, default ""
            Free-text license description. Required when `license` is
            `SiteLicense.OTHER`

        Raises
        ------
        ValueError
            If `license` is `SiteLicense.OTHER` and `other` is empty
        """
        if license is SiteLicense.OTHER and not other:
            raise ValueError("license_other is required when license is SiteLicense.OTHER")

        def mutator(cats: SiteCategoryCollection) -> None:
            category = cats[category_name]
            category.license_id = license.value
            category.license_other = other
            category.license_default = False

        self.update_categories(_MODULE_LICENSE, "ManageSiteAction", "saveLicense", mutator)

    def use_default_license(self, category_name: str) -> None:
        """
        Make a category inherit the site's default license

        Parameters
        ----------
        category_name : str
            Category name
        """

        def mutator(cats: SiteCategoryCollection) -> None:
            cats[category_name].license_default = True

        self.update_categories(_MODULE_LICENSE, "ManageSiteAction", "saveLicense", mutator)

    def set_navigation(self, category_name: str, top_bar_page_name: str, side_bar_page_name: str) -> None:
        """
        Set explicit top/side navigation pages for a category

        Parameters
        ----------
        category_name : str
            Category name
        top_bar_page_name : str
            Fullname of the page used as the top bar
        side_bar_page_name : str
            Fullname of the page used as the side bar
        """

        def mutator(cats: SiteCategoryCollection) -> None:
            category = cats[category_name]
            category.top_bar_page_name = top_bar_page_name
            category.side_bar_page_name = side_bar_page_name
            category.nav_default = False

        self.update_categories(_MODULE_NAVIGATION, "ManageSiteAction", "saveNavigation", mutator)

    def use_default_navigation(self, category_name: str) -> None:
        """
        Make a category inherit the site's default navigation

        Parameters
        ----------
        category_name : str
            Category name
        """

        def mutator(cats: SiteCategoryCollection) -> None:
            cats[category_name].nav_default = True

        self.update_categories(_MODULE_NAVIGATION, "ManageSiteAction", "saveNavigation", mutator)

    def set_template(self, category_name: str, template_id: int | None) -> None:
        """
        Set (or clear, with None) the page template for a category

        Parameters
        ----------
        category_name : str
            Category name
        template_id : int | None
            Template ID, or None to unset
        """

        def mutator(cats: SiteCategoryCollection) -> None:
            cats[category_name].template_id = template_id

        self.update_categories(_MODULE_TEMPLATES, "ManageSiteAction", "saveTemplates", mutator)

    def set_page_rate_settings(self, category_name: str, rating: RatingSettings) -> None:
        """
        Set the rating (vote) configuration for a category

        Parameters
        ----------
        category_name : str
            Category name
        rating : RatingSettings
            New rating configuration
        """

        def mutator(cats: SiteCategoryCollection) -> None:
            cats[category_name].rating = rating

        self.update_categories(_MODULE_PAGE_RATE, "ManageSiteAction", "savePageRateSettings", mutator)

    def set_per_page_discussion(self, category_name: str, enabled: bool | None) -> None:
        """
        Enable/disable the per-page discussion thread for a category

        Parameters
        ----------
        category_name : str
            Category name
        enabled : bool | None
            True/False to force on/off, or None to use the site default
        """

        def mutator(cats: SiteCategoryCollection) -> None:
            category = cats[category_name]
            category.per_page_discussion = enabled
            category.per_page_discussion_default = enabled is None

        self.update_categories(_MODULE_PER_PAGE_DISCUSSION, "ManageSiteForumAction", "savePerPageDiscussion", mutator)

    def set_appearance_theme(self, category_name: str, theme_id: int) -> None:
        """
        Apply a built-in theme to a category

        Parameters
        ----------
        category_name : str
            Category name
        theme_id : int
            Theme ID
        """

        def mutator(cats: SiteCategoryCollection) -> None:
            category = cats[category_name]
            category.theme_id = theme_id
            category.theme_external_url = ""
            category.theme_default = False

        self.update_categories(_MODULE_APPEARANCE, "ManageSiteThemeAction", "saveAppearance", mutator)

    def set_appearance_external_theme(self, category_name: str, theme_external_url: str) -> None:
        """
        Apply an external theme URL to a category

        Wikidot represents "external theme" by sending `theme_id` as the
        empty string instead of an int (see SiteCategory.theme_id).

        Parameters
        ----------
        category_name : str
            Category name
        theme_external_url : str
            External theme stylesheet URL
        """

        def mutator(cats: SiteCategoryCollection) -> None:
            category = cats[category_name]
            category.theme_id = ""
            category.theme_external_url = theme_external_url
            category.theme_default = False

        self.update_categories(_MODULE_APPEARANCE, "ManageSiteThemeAction", "saveAppearance", mutator)

    def use_default_appearance(self, category_name: str) -> None:
        """
        Make a category inherit the site's default appearance

        Parameters
        ----------
        category_name : str
            Category name
        """

        def mutator(cats: SiteCategoryCollection) -> None:
            cats[category_name].theme_default = True

        self.update_categories(_MODULE_APPEARANCE, "ManageSiteThemeAction", "saveAppearance", mutator)

    # ------------------------------------------------------------------
    # Task 1-3: General / Domain / Access policy
    # ------------------------------------------------------------------

    def save_general(
        self,
        name: str,
        subtitle: str = "",
        language: str = "en",
        description: str = "",
        default_page: str = "",
        welcome_page: str = "",
    ) -> str | None:
        """
        Save the site's title/subtitle/language/description/entry pages

        Parameters
        ----------
        name : str
            Site title. Required (an empty value raises FormErrorsException)
        subtitle : str, default ""
        language : str, default "en"
            Site language code (e.g. "en", "ja")
        description : str, default ""
            Up to 300 characters
        default_page : str, default ""
            Fullname of the page to use as the site's start page
        welcome_page : str, default ""
            Fullname of the page shown to first-time visitors

        Returns
        -------
        str | None
            New unix name, only returned when the site's unix name changed
            as a result

        Raises
        ------
        FormErrorsException
            When validation fails (e.g. an empty title)
        """
        response = self.site.amc_request(
            [
                {
                    "action": "ManageSiteAction",
                    "event": "saveGeneral",
                    "name": name,
                    "subtitle": subtitle,
                    "language": language,
                    "description": description,
                    "default_page": default_page,
                    "welcome_page": welcome_page,
                    "moduleName": "Empty",
                }
            ]
        )[0]
        result = response.json().get("unixName")
        return result if isinstance(result, str) else None

    def save_domain(self, domain: str, redirects: list[str] | None = None, domain_default: bool = False) -> str | None:
        """
        Save the site's custom domain and redirect domains

        Parameters
        ----------
        domain : str
            Custom domain (fully qualified, e.g. "example.com")
        redirects : list[str] | None, default None
            Additional domains that redirect to this site. At most 10
            (Wikidot's own client also allows empty entries through, which
            show up as consecutive ";" in the joined string; this method
            does not filter them out to match observed behavior)
        domain_default : bool, default False
            Whether to reset to the default wikidot.com subdomain

        Returns
        -------
        str | None
            New domain, only returned when it changed

        Raises
        ------
        ValueError
            If more than 10 redirects are given
        """
        if redirects is not None and len(redirects) > 10:
            raise ValueError("redirects supports at most 10 entries")
        body = omit_falsy(domainDefault=flag(domain_default))
        response = self.site.amc_request(
            [
                {
                    "action": "ManageSiteAction",
                    "event": "saveDomain",
                    "domain": domain,
                    "redirects": ";".join(redirects) if redirects else "",
                    "moduleName": "Empty",
                    **body,
                }
            ]
        )[0]
        result = response.json().get("newDomain")
        return result if isinstance(result, str) else None

    def save_access_policy(
        self,
        privacy: Literal["open", "closed", "private"],
        by_apply: bool = False,
        by_domain: str = "",
        by_password: bool = False,
        password: str = "",
        allow_hotlink: bool = False,
        landing_page: str = "",
        hide_nav: bool = False,
        viewers: "Iterable[AbstractUser] | Iterable[int] | None" = None,
    ) -> None:
        """
        Save the site's access policy (privacy level, apply/password/domain
        gating, extra viewers, hotlinking, landing page, nav visibility)

        Parameters
        ----------
        privacy : Literal["open", "closed", "private"]
        by_apply : bool, default False
            Allow joining by application
        by_domain : str, default ""
            Email domain that may join without application
        by_password : bool, default False
            Allow joining with a password
        password : str, default ""
            Join password (used when by_password is True)
        allow_hotlink : bool, default False
        landing_page : str, default ""
            Fullname of the page shown to non-members when privacy is
            "private"
        hide_nav : bool, default False
        viewers : Iterable[AbstractUser | int] | None, default None
            Extra users allowed to view a private site
        """
        viewers_str = ""
        if viewers is not None:
            ids = [v if isinstance(v, int) else v.id for v in viewers]
            viewers_str = ",".join(str(i) for i in ids)
        body = omit_falsy(
            by_apply=checkbox(by_apply),
            by_password=checkbox(by_password),
            allowHotlink=checkbox(allow_hotlink),
            hideNav=checkbox(hide_nav),
        )
        self.site.amc_request(
            [
                {
                    "action": "ManageSiteAction",
                    "event": "savePrivateSettings",
                    "privacy": privacy,
                    "by_domain": by_domain,
                    "password": password,
                    "landingPage": landing_page,
                    "viewers": viewers_str,
                    "moduleName": "Empty",
                    **body,
                }
            ]
        )

    # ------------------------------------------------------------------
    # Task 1-5: single-shot settings
    # ------------------------------------------------------------------

    def save_custom_footer(self, source: str, use: bool = False) -> None:
        """
        Save the site's custom footer

        Parameters
        ----------
        source : str
            Footer Wikidot markup source
        use : bool, default False
            Whether to actually use the custom footer
        """
        body = omit_falsy(use=flag(use))
        self.site.amc_request(
            [
                {
                    "action": "ManageSiteAction",
                    "event": "saveCustomFooter",
                    "source": source,
                    "moduleName": "Empty",
                    **body,
                }
            ]
        )

    def save_toolbars_preference(
        self, toolbar_top: bool = False, toolbar_bottom: bool = False, promote: bool = False
    ) -> None:
        """
        Save the site's edit-toolbar visibility preference

        Parameters
        ----------
        toolbar_top : bool, default False
        toolbar_bottom : bool, default False
        promote : bool, default False
        """
        body = omit_falsy(
            toolbarTop=checkbox(toolbar_top),
            toolbarBottom=checkbox(toolbar_bottom),
            promote=checkbox(promote),
        )
        self.site.amc_request(
            [{"action": "ManageSiteAction", "event": "saveToolbarsPref", "moduleName": "Empty", **body}]
        )

    def save_google_analytics(self, key: str, use: bool = False) -> None:
        """
        Save the site's Google Analytics key

        Parameters
        ----------
        key : str
            Google Analytics tracking key
        use : bool, default False
            Whether to actually enable tracking
        """
        body = omit_falsy(use=checkbox(use))
        self.site.amc_request(
            [
                {
                    "action": "ManageSite3rdPartyAction",
                    "event": "saveGoogleAnalytics",
                    "key": key,
                    "moduleName": "Empty",
                    **body,
                }
            ]
        )

    def add_autonumeration(self, category_name: str, override: bool = False) -> None:
        """
        Enable page auto-numbering for a category

        Parameters
        ----------
        category_name : str
            Category name
        override : bool, default False
            Wikidot responds with status "non_numeric" and asks for
            confirmation when the category has pages with non-numeric
            names; pass override=True to confirm and proceed. This method
            does not auto-retry on "non_numeric" — catch
            WikidotStatusCodeException and re-call with override=True if
            needed

        Raises
        ------
        WikidotStatusCodeException
            status_code "non_numeric" if the category has non-numeric page
            names and override is False
        """
        body = omit_falsy(override=flag(override))
        self.site.amc_request(
            [
                {
                    "action": "ManageSiteAutonumerateAction",
                    "event": "addAutonumeration",
                    "categoryName": category_name,
                    "moduleName": "Empty",
                    **body,
                }
            ]
        )

    def remove_autonumeration(self, category_name: str) -> None:
        """
        Disable page auto-numbering for a category

        Parameters
        ----------
        category_name : str
            Category name
        """
        self.site.amc_request(
            [
                {
                    "action": "ManageSiteAutonumerateAction",
                    "event": "removeAutonumeration",
                    "categoryName": category_name,
                    "moduleName": "Empty",
                }
            ]
        )

    def set_autonumerate_title_format(self, category_name: str, title_format: str) -> None:
        """
        Set the auto-numbering title format for a category

        Parameters
        ----------
        category_name : str
            Category name
        title_format : str
            Title format string
        """
        self.site.amc_request(
            [
                {
                    "action": "ManageSiteAutonumerateAction",
                    "event": "setTitleFormat",
                    "categoryName": category_name,
                    "titleFormat": title_format,
                    "moduleName": "Empty",
                }
            ]
        )

    def add_pingbacks(self, category_name: str, override: bool = False) -> None:
        """
        Enable outgoing pingbacks for a category

        Parameters
        ----------
        category_name : str
            Category name
        override : bool, default False
            Confirmation flag mirroring add_autonumeration's override
        """
        body = omit_falsy(override=flag(override))
        self.site.amc_request(
            [
                {
                    "action": "ManageSitePingbacksAction",
                    "event": "addPingbacks",
                    "categoryName": category_name,
                    "moduleName": "Empty",
                    **body,
                }
            ]
        )

    def remove_pingbacks(self, category_name: str) -> None:
        """
        Disable outgoing pingbacks for a category

        Parameters
        ----------
        category_name : str
            Category name
        """
        self.site.amc_request(
            [
                {
                    "action": "ManageSitePingbacksAction",
                    "event": "removePingbacks",
                    "categoryName": category_name,
                    "moduleName": "Empty",
                }
            ]
        )

    def set_global_pingback(self, enabled: bool = False) -> None:
        """
        Enable/disable pingbacks site-wide

        Parameters
        ----------
        enabled : bool, default False
        """
        body = omit_falsy(enabled=flag(enabled))
        self.site.amc_request(
            [{"action": "ManageSitePingbacksAction", "event": "setGlobalPingback", "moduleName": "Empty", **body}]
        )

    def save_api_settings(
        self,
        enabled: bool = False,
        read_1: bool = False,
        read_2: bool = False,
        write_1: bool = False,
        write_2: bool = False,
    ) -> None:
        """
        Save the site's public API access settings

        Parameters
        ----------
        enabled : bool, default False
            Whether the API is enabled at all
        read_1, read_2 : bool, default False
            Read permission levels
        write_1, write_2 : bool, default False
            Write permission levels
        """
        body = omit_falsy(
            **{
                "sm-api-enable": checkbox(enabled),
                "read-1": checkbox(read_1),
                "read-2": checkbox(read_2),
                "write-1": checkbox(write_1),
                "write-2": checkbox(write_2),
            }
        )
        self.site.amc_request([{"action": "ManageSiteApiAction", "event": "save", "moduleName": "Empty", **body}])

    def save_openid(self, enabled: bool, identity_url: str = "", server_url: str = "") -> None:
        """
        Save the site-wide OpenID configuration

        Only the site-wide form (`sm-openid-form-0`) is modeled; the
        per-page OpenID forms are dynamically added/removed in the UI and
        out of scope for this method.

        Parameters
        ----------
        enabled : bool
            Whether OpenID login is enabled. Sent as the literal string
            "true"/"false" (unlike most other boolean settings here, this
            one is not omitted when False; see 40_admin-managesite.md)
        identity_url : str, default ""
        server_url : str, default ""
        """
        vals = [{"identityUrl": identity_url, "serverUrl": server_url}]
        self.site.amc_request(
            [
                {
                    "action": "ManageSiteOpenIDAction",
                    "event": "saveOpenID",
                    "enableOpenID": "true" if enabled else "false",
                    "vals": json_param(vals),
                    "moduleName": "Empty",
                }
            ]
        )

    def request_backup(
        self,
        backup_sources: bool = False,
        backup_files: bool = False,
        backup_type: Literal["tar", "zip"] = "zip",
    ) -> None:
        """
        Request a site backup

        Parameters
        ----------
        backup_sources : bool, default False
            Include page sources
        backup_files : bool, default False
            Include uploaded files
        backup_type : Literal["tar", "zip"], default "zip"
        """
        body = omit_falsy(backupSources=checkbox(backup_sources), backupFiles=checkbox(backup_files))
        self.site.amc_request(
            [
                {
                    "action": "ManageSiteBackupAction",
                    "event": "requestBackup",
                    "backupType": backup_type,
                    "moduleName": "Empty",
                    **body,
                }
            ]
        )

    def delete_backup(
        self,
        *,
        confirm: bool,
        backup_sources: bool = False,
        backup_files: bool = False,
        backup_type: Literal["tar", "zip"] = "zip",
    ) -> None:
        """
        Delete a site backup. Destructive and irreversible

        Parameters
        ----------
        confirm : bool
            Must be explicitly True to proceed (safety gate for a
            destructive operation)
        backup_sources : bool, default False
        backup_files : bool, default False
        backup_type : Literal["tar", "zip"], default "zip"

        Raises
        ------
        ValueError
            If confirm is not True
        """
        if not confirm:
            raise ValueError("delete_backup is destructive; pass confirm=True to proceed")
        body = omit_falsy(backupSources=checkbox(backup_sources), backupFiles=checkbox(backup_files))
        self.site.amc_request(
            [
                {
                    "action": "ManageSiteBackupAction",
                    "event": "deleteBackup",
                    "backupType": backup_type,
                    "moduleName": "Empty",
                    **body,
                }
            ]
        )

    def delete_favicon(self) -> None:
        """Delete the site's favicon"""
        self.site.amc_request([{"action": "ManageSiteIconsAction", "event": "deleteFavicon", "moduleName": "Empty"}])

    def set_favicon_from_uri(self, uri: str) -> None:
        """
        Set the site's favicon from a URL

        Parameters
        ----------
        uri : str
            Image URL
        """
        self.site.amc_request(
            [{"action": "ManageSiteIconsAction", "event": "uploadFaviconUri", "uri": uri, "moduleName": "Empty"}]
        )

    def delete_ios_icon(self) -> None:
        """Delete the site's iOS home screen icon"""
        self.site.amc_request([{"action": "ManageSiteIconsAction", "event": "deleteIosIcon", "moduleName": "Empty"}])

    def set_ios_icon_from_uri(self, uri: str) -> None:
        """
        Set the site's iOS home screen icon from a URL

        Parameters
        ----------
        uri : str
            Image URL
        """
        self.site.amc_request(
            [{"action": "ManageSiteIconsAction", "event": "uploadIosIconUri", "uri": uri, "moduleName": "Empty"}]
        )

    def delete_windows_icon(self) -> None:
        """Delete the site's Windows tile icon"""
        self.site.amc_request(
            [{"action": "ManageSiteIconsAction", "event": "deleteWindowsIcon", "moduleName": "Empty"}]
        )

    def set_windows_icon_from_uri(self, uri: str) -> None:
        """
        Set the site's Windows tile icon from a URL

        Parameters
        ----------
        uri : str
            Image URL
        """
        self.site.amc_request(
            [{"action": "ManageSiteIconsAction", "event": "uploadWindowsIconUri", "uri": uri, "moduleName": "Empty"}]
        )

    def set_windows_icon_background_color(self, color: str) -> None:
        """
        Set the site's Windows tile background color

        Parameters
        ----------
        color : str
            CSS color value

        Notes
        -----
        The AMC event name is `windowsIconBackroundColor` (missing the "g"
        in "Background") — this is a typo in Wikidot's own JS, kept
        verbatim here since the server only recognizes the exact name.
        """
        self.site.amc_request(
            [
                {
                    "action": "ManageSiteIconsAction",
                    "event": "windowsIconBackroundColor",
                    "color": color,
                    "moduleName": "Empty",
                }
            ]
        )

    def preview_newsletter(self, title: str, content: str) -> tuple[str, str]:
        """
        Render a newsletter preview

        Parameters
        ----------
        title : str
        content : str

        Returns
        -------
        tuple[str, str]
            Rendered (title, content)
        """
        response = self.site.amc_request(
            [
                {
                    "action": "ManageSiteNewsletterAction",
                    "event": "preview",
                    "title": title,
                    "content": content,
                    "moduleName": "Empty",
                }
            ]
        )[0]
        data = response.json()
        return data.get("title", ""), data.get("content", "")

    def send_newsletter(
        self,
        title: str,
        content: str,
        admins: bool = False,
        moderators: bool = False,
        members: bool = False,
        others: "list[AbstractUser] | list[int] | None" = None,
    ) -> None:
        """
        Send a newsletter to site members

        Parameters
        ----------
        title : str
        content : str
        admins : bool, default False
            Send to admins
        moderators : bool, default False
            Send to moderators
        members : bool, default False
            Send to all members
        others : list[AbstractUser | int] | None, default None
            Additional specific recipients
        """
        other_ids = [u if isinstance(u, int) else u.id for u in others] if others else []
        self.site.amc_request(
            [
                {
                    "action": "ManageSiteNewsletterAction",
                    "event": "send",
                    "title": title,
                    "content": content,
                    "admins": "true" if admins else "false",
                    "moderators": "true" if moderators else "false",
                    "members": "true" if members else "false",
                    "others": other_ids,
                    "moduleName": "Empty",
                }
            ]
        )
