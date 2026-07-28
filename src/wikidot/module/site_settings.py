"""
Module for Wikidot's site-wide settings (Manage Site's `_admin` panel)

Access through `Site.settings`. Methods are grouped following
31_tasks.md's P1 breakdown:

- `update_categories`: the read-modify-write primitive for the seven
  `categories`-backed areas (Task 1-1)
- Permissions / License / Navigation / Templates / PageRate /
  PerPageDiscussion / Appearance: thin wrappers over `update_categories`
  (Task 1-4)
- General / Domain / Access policy: read-modify-write form saves
  (Task 1-3)
- Everything else (CustomFooter / Toolbars / GoogleAnalytics /
  Autonumerate / Pingbacks / API / OpenID / Backup / Icons / Newsletter):
  single-shot settings (Task 1-5)

General/Domain/Access policy have both a `get_*` and a `save_*` method.
`save_*`'s parameters all default to None, meaning "keep the current
value" (fetched via `get_*` first); pass "" explicitly to clear a text
field. This matters because Wikidot's save events resubmit the whole
form, not a diff — omitting a field silently blanks it (`saveGeneral`
called with only `name` would otherwise wipe subtitle/description/
default_page/welcome_page and reset language to "en").
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from bs4 import BeautifulSoup
from bs4.element import Tag

from ..connector.ajax import require_body
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


def _form_field(soup: Tag, name: str) -> str | None:
    """
    Read a form field's current value by its `name` attribute

    Handles the three form control shapes formToArray understands
    (text-like input, textarea, select); returns None if the element is
    missing or (for select) nothing is marked selected, rather than
    guessing a value.
    """
    el = soup.select_one(f'[name="{name}"]')
    if el is None:
        return None
    if el.name == "textarea":
        return el.get_text()
    if el.name == "select":
        selected = el.select_one("option[selected]")
        if selected is None:
            return None
        value = selected.get("value")
        return str(value) if value is not None else selected.get_text()
    value = el.get("value")
    return str(value) if value is not None else None


def _form_checkbox(soup: Tag, name: str) -> bool | None:
    """Read a checkbox's current checked state by its `name` attribute"""
    el = soup.select_one(f'input[name="{name}"]')
    if el is None:
        return None
    return el.has_attr("checked")


def _form_radio(soup: Tag, name: str) -> str | None:
    """Read the checked option's value from a radio button group"""
    el = soup.select_one(f'input[name="{name}"][checked]')
    if el is None:
        return None
    value = el.get("value")
    return str(value) if value is not None else None


def _element_value(soup: Tag, element_id: str) -> str | None:
    """
    Read an element's current value by its `id`

    For the handful of fields Wikidot's own JS reads by id instead of via
    formToArray (see 35_form-fields.md "JS が id で直接読む項目"), such as
    Domain's fields.
    """
    el = soup.select_one(f"#{element_id}")
    if el is None:
        return None
    value = el.get("value")
    return str(value) if value is not None else None


def _element_checkbox(soup: Tag, element_id: str) -> bool | None:
    """Read a checkbox's current checked state by its `id`"""
    el = soup.select_one(f"#{element_id}")
    if el is None:
        return None
    return el.has_attr("checked")


@dataclass
class GeneralSettings:
    """
    Current values of the site's General settings form (`sm-general-form`)

    Any field is None when the corresponding form element could not be
    found in the rendered HTML; this library does not guess a value in
    that case.
    """

    name: str | None
    subtitle: str | None
    language: str | None
    description: str | None
    default_page: str | None
    welcome_page: str | None


@dataclass
class DomainSettings:
    """Current values of the site's Domain settings"""

    domain: str | None
    domain_default: bool | None
    redirects: list[str] | None


@dataclass
class AccessPolicySettings:
    """
    Current values of the site's Access policy settings (`sm-private-form`)

    `viewers` (extra allowed users for a private site) is intentionally
    absent: it is not part of this form, see `save_access_policy`'s
    docstring for why it cannot be read back.
    """

    privacy: Literal["open", "closed", "private"] | None
    by_apply: bool | None
    by_domain: str | None
    by_password: bool | None
    password: str | None
    allow_hotlink: bool | None
    landing_page: str | None
    hide_nav: bool | None


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

    def get_general(self) -> GeneralSettings:
        """
        Fetch the site's current General settings

        Renders `managesite/ManageSiteGeneralModule` and reads the current
        values out of `sm-general-form` by its documented field names
        (35_form-fields.md).

        Returns
        -------
        GeneralSettings
        """
        module_name = "managesite/ManageSiteGeneralModule"
        response = self.site.amc_request([{"moduleName": module_name}])[0]
        soup = BeautifulSoup(require_body(response, module_name), "lxml")
        return GeneralSettings(
            name=_form_field(soup, "name"),
            subtitle=_form_field(soup, "subtitle"),
            language=_form_field(soup, "language"),
            description=_form_field(soup, "description"),
            default_page=_form_field(soup, "default_page"),
            welcome_page=_form_field(soup, "welcome_page"),
        )

    def save_general(
        self,
        name: str | None = None,
        subtitle: str | None = None,
        language: str | None = None,
        description: str | None = None,
        default_page: str | None = None,
        welcome_page: str | None = None,
    ) -> str | None:
        """
        Save the site's title/subtitle/language/description/entry pages

        `saveGeneral` resubmits the whole form rather than a diff, so this
        fetches the current settings (`get_general`) first and only
        overrides the fields the caller passed explicitly. None keeps the
        current value; pass "" to clear a field.

        Parameters
        ----------
        name : str | None, default None
            Site title. None keeps the current title. An empty string (or
            a current title this library could not read) raises
            FormErrorsException, since the title is required
        subtitle : str | None, default None
        language : str | None, default None
            Site language code (e.g. "en", "ja")
        description : str | None, default None
            Up to 300 characters
        default_page : str | None, default None
            Fullname of the page to use as the site's start page
        welcome_page : str | None, default None
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
        current = self.get_general()
        response = self.site.amc_request(
            [
                {
                    "action": "ManageSiteAction",
                    "event": "saveGeneral",
                    "name": name if name is not None else (current.name or ""),
                    "subtitle": subtitle if subtitle is not None else (current.subtitle or ""),
                    "language": language if language is not None else (current.language or "en"),
                    "description": description if description is not None else (current.description or ""),
                    "default_page": default_page if default_page is not None else (current.default_page or ""),
                    "welcome_page": welcome_page if welcome_page is not None else (current.welcome_page or ""),
                    "moduleName": "Empty",
                }
            ]
        )[0]
        result = response.json().get("unixName")
        return result if isinstance(result, str) else None

    def get_domain(self) -> DomainSettings:
        """
        Fetch the site's current Domain settings

        Renders `managesite/ManageSiteDomainModule`. Unlike General/Access
        policy these fields are read by element id, not `name` (Wikidot's
        own JS reads them the same way; see 35_form-fields.md "JS が id で
        直接読む項目").

        Returns
        -------
        DomainSettings
        """
        module_name = "managesite/ManageSiteDomainModule"
        response = self.site.amc_request([{"moduleName": module_name}])[0]
        soup = BeautifulSoup(require_body(response, module_name), "lxml")
        redirects_box = soup.select_one("#sm-redirects-box")
        redirects: list[str] | None = None
        if redirects_box is not None:
            redirects = [str(value) for el in redirects_box.select("input") if (value := el.get("value")) is not None]
        return DomainSettings(
            domain=_element_value(soup, "sm-domain-field"),
            domain_default=_element_checkbox(soup, "sm-domain-default"),
            redirects=redirects,
        )

    def save_domain(
        self,
        domain: str | None = None,
        redirects: list[str] | None = None,
        domain_default: bool | None = None,
    ) -> str | None:
        """
        Save the site's custom domain and redirect domains

        Fetches the current settings (`get_domain`) first; None keeps the
        current value for each parameter.

        Parameters
        ----------
        domain : str | None, default None
            Custom domain (fully qualified, e.g. "example.com"). None
            keeps the current domain
        redirects : list[str] | None, default None
            Additional domains that redirect to this site. None keeps the
            current redirect list; pass [] to clear it. At most 10
            (Wikidot's own client also allows empty entries through, which
            show up as consecutive ";" in the joined string; this method
            does not filter them out to match observed behavior)
        domain_default : bool | None, default None
            Whether to reset to the default wikidot.com subdomain. None
            keeps the current state

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
        current = self.get_domain()
        resolved_domain = domain if domain is not None else (current.domain or "")
        resolved_redirects = redirects if redirects is not None else (current.redirects or [])
        resolved_domain_default = domain_default if domain_default is not None else bool(current.domain_default)
        body = omit_falsy(domainDefault=flag(resolved_domain_default))
        response = self.site.amc_request(
            [
                {
                    "action": "ManageSiteAction",
                    "event": "saveDomain",
                    "domain": resolved_domain,
                    "redirects": ";".join(resolved_redirects),
                    "moduleName": "Empty",
                    **body,
                }
            ]
        )[0]
        result = response.json().get("newDomain")
        return result if isinstance(result, str) else None

    def get_access_policy(self) -> AccessPolicySettings:
        """
        Fetch the site's current Access policy settings

        Renders `managesite/ManageSiteAccessPolicyModule` and reads
        `sm-private-form`. Does not include `viewers` — see
        `save_access_policy` for why that field cannot be read back.

        Returns
        -------
        AccessPolicySettings
        """
        module_name = "managesite/ManageSiteAccessPolicyModule"
        response = self.site.amc_request([{"moduleName": module_name}])[0]
        soup = BeautifulSoup(require_body(response, module_name), "lxml")
        privacy_raw = _form_radio(soup, "privacy")
        privacy: Literal["open", "closed", "private"] | None = (
            privacy_raw if privacy_raw in ("open", "closed", "private") else None  # type: ignore[assignment]
        )
        return AccessPolicySettings(
            privacy=privacy,
            by_apply=_form_checkbox(soup, "by_apply"),
            by_domain=_form_field(soup, "by_domain"),
            by_password=_form_checkbox(soup, "by_password"),
            password=_form_field(soup, "password"),
            allow_hotlink=_form_checkbox(soup, "allowHotlink"),
            landing_page=_form_field(soup, "landingPage"),
            hide_nav=_form_checkbox(soup, "hideNav"),
        )

    def save_access_policy(
        self,
        privacy: Literal["open", "closed", "private"] | None = None,
        by_apply: bool | None = None,
        by_domain: str | None = None,
        by_password: bool | None = None,
        password: str | None = None,
        allow_hotlink: bool | None = None,
        landing_page: str | None = None,
        hide_nav: bool | None = None,
        viewers: "Iterable[AbstractUser] | Iterable[int] | None" = None,
    ) -> None:
        """
        Save the site's access policy (privacy level, apply/password/domain
        gating, extra viewers, hotlinking, landing page, nav visibility)

        Fetches the current settings (`get_access_policy`) first; None
        keeps the current value for each parameter (except `viewers`, see
        below).

        Parameters
        ----------
        privacy : Literal["open", "closed", "private"] | None, default None
            None keeps the current value. Raises ValueError if it cannot
            be determined (this library will not guess between open /
            closed / private, since a wrong guess could expose a private
            site)
        by_apply : bool | None, default None
            Allow joining by application. None keeps the current value
        by_domain : str | None, default None
            Email domain that may join without application. None keeps
            the current value
        by_password : bool | None, default None
            Allow joining with a password. None keeps the current value
        password : str | None, default None
            Join password (used when by_password is True). None keeps the
            current value. **Note**: it is unconfirmed whether Wikidot
            actually echoes the real current password back in this form
            (services commonly blank password fields for security) — if
            you are changing another field on a password-gated site,
            pass the password explicitly rather than relying on this
        allow_hotlink : bool | None, default None
        landing_page : str | None, default None
            Fullname of the page shown to non-members when privacy is
            "private". None keeps the current value
        hide_nav : bool | None, default None
        viewers : Iterable[AbstractUser | int] | None, default None
            Extra users allowed to view a private site. **Not** part of
            `sm-private-form` — Wikidot assembles it client-side via an
            autocomplete widget with no static representation of the
            current selection, so it cannot be read back the way the
            other fields can. None omits the `viewers` parameter from the
            request entirely (rather than sending an empty string, which
            would actively clear it), but this is *not* the same
            guarantee as the other fields' "keeps the current value": if
            the site has extra viewers configured, pass them explicitly
            to preserve them

        Raises
        ------
        ValueError
            If `privacy` is None and the current value could not be
            determined
        """
        current = self.get_access_policy()
        resolved_privacy = privacy if privacy is not None else current.privacy
        if resolved_privacy is None:
            raise ValueError("privacy could not be determined from the site's current settings; pass it explicitly")
        resolved_by_domain = by_domain if by_domain is not None else (current.by_domain or "")
        resolved_password = password if password is not None else (current.password or "")
        resolved_landing_page = landing_page if landing_page is not None else (current.landing_page or "")
        resolved_by_apply = by_apply if by_apply is not None else bool(current.by_apply)
        resolved_by_password = by_password if by_password is not None else bool(current.by_password)
        resolved_allow_hotlink = allow_hotlink if allow_hotlink is not None else bool(current.allow_hotlink)
        resolved_hide_nav = hide_nav if hide_nav is not None else bool(current.hide_nav)

        body = omit_falsy(
            by_apply=checkbox(resolved_by_apply),
            by_password=checkbox(resolved_by_password),
            allowHotlink=checkbox(resolved_allow_hotlink),
            hideNav=checkbox(resolved_hide_nav),
        )
        if viewers is not None:
            ids = [v if isinstance(v, int) else v.id for v in viewers]
            body["viewers"] = ",".join(str(i) for i in ids)

        self.site.amc_request(
            [
                {
                    "action": "ManageSiteAction",
                    "event": "savePrivateSettings",
                    "privacy": resolved_privacy,
                    "by_domain": resolved_by_domain,
                    "password": resolved_password,
                    "landingPage": resolved_landing_page,
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
