"""
Module for handling Wikidot's per-site "category" objects

`categories` is the shared read-modify-write data structure behind seven
Manage Site areas (Permissions / License / Navigation / Templates / PageRate
/ PerPageDiscussion / Appearance): each renders the *entire* category array
alongside its HTML body, and each save sends the *entire* array back as a
single JSON string — there is no partial-update endpoint. See 30_plan.md D3
and 40_admin-managesite.md for the schema and wire format this is built
from.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from ..common import exceptions
from ..util.amc_body import json_param
from .site_permissions import Actor, PagePermissions, RatingSettings, replace_actors

if TYPE_CHECKING:
    from .site import Site


class SiteLicense(Enum):
    """
    Known `license_id` values for a category

    Values and the exact option text come from a live read-only fetch of
    `managesite/ManageSiteLicenseModule` (`select#sm-license-lic`), recorded
    in 35_form-fields.md's "license_id の値（実測）" table. All 15 values are
    confirmed, including the previously-grouped NonCommercial variants
    (5/6/7 and 15/16/17).
    """

    OTHER = 1
    """"Other" (custom license). Requires `license_other` to be set."""
    CC_ATTRIBUTION_SHAREALIKE_2_5 = 2
    """"Creative Commons Attribution Share Alike 2.5" """
    CC_ATTRIBUTION_2_5 = 3
    """"Creative Commons Attribution 2.5" """
    CC_ATTRIBUTION_NO_DERIVATIVES_2_5 = 4
    """"Creative Commons Attribution No Derivatives 2.5" """
    CC_ATTRIBUTION_NONCOMMERCIAL_2_5 = 5
    """"Creative Commons Attribution Non-commercial 2.5" """
    CC_ATTRIBUTION_NONCOMMERCIAL_SHAREALIKE_2_5 = 6
    """"Creative Commons Attribution Non-commercial Share Alike 2.5" """
    CC_ATTRIBUTION_NONCOMMERCIAL_NO_DERIVATIVES_2_5 = 7
    """"Creative Commons Attribution Non-commercial No Derivatives 2.5" """
    GFDL_1_2 = 8
    """"GNU Free Documentation License 1.2" """
    STANDARD_COPYRIGHT = 11
    """"Standard copyright (not recommended)" """
    CC_ATTRIBUTION_SHAREALIKE_3_0 = 12
    """"Creative Commons Attribution-ShareAlike 3.0 License (recommended)" """
    CC_ATTRIBUTION_3_0 = 13
    """"Creative Commons Attribution 3.0 License" """
    CC_ATTRIBUTION_NO_DERIVATIVES_3_0 = 14
    """"Creative Commons Attribution-NoDerivs 3.0 License" """
    CC_ATTRIBUTION_NONCOMMERCIAL_3_0 = 15
    """"Creative Commons Attribution-NonCommercial 3.0 License" """
    CC_ATTRIBUTION_NONCOMMERCIAL_SHAREALIKE_3_0 = 16
    """"Creative Commons Attribution-NonCommercial-ShareAlike 3.0 License" """
    CC_ATTRIBUTION_NONCOMMERCIAL_NO_DERIVATIVES_3_0 = 17
    """"Creative Commons Attribution-NonCommercial-NoDerivs 3.0 License" """


@dataclass
class SiteCategory:
    """
    A single category object from a site's Manage Site `categories` array

    Attributes mirror the JSON schema documented in 40_admin-managesite.md
    (24 fields, `_default` category holds the site-wide defaults that other
    categories inherit when their own `*_default` flag is set).

    Attributes
    ----------
    category_id : int
    site_id : int
    name : str
    theme_default : bool
    theme_id : int | str
        Normally an int theme id. Wikidot's own client sends the empty
        string here (not 0) when `theme_external_url` is used instead
        (see 40_admin-managesite.md「Appearance」)
    layout_default : bool
    layout_id : int
    theme_external_url : str
    permissions_default : bool
    permissions : PagePermissions | None
        None when permissions_default is True (inherits site default)
    license_default : bool
    license_id : int | None
    license_other : str
    nav_default : bool
    top_bar_page_name : str | None
    side_bar_page_name : str | None
    template_id : int | None
    per_page_discussion : bool | None
        None means "use site default"
    per_page_discussion_default : bool
    rating : RatingSettings | None
    autonumerate : bool
    page_title_template : str | None
    enable_pingback_out : bool
    enable_pingback_in : bool
    """

    category_id: int
    site_id: int
    name: str
    theme_default: bool
    theme_id: int | str
    layout_default: bool
    layout_id: int
    theme_external_url: str
    permissions_default: bool
    permissions: PagePermissions | None
    license_default: bool
    license_id: int | None
    license_other: str
    nav_default: bool
    top_bar_page_name: str | None
    side_bar_page_name: str | None
    template_id: int | None
    per_page_discussion: bool | None
    per_page_discussion_default: bool
    rating: RatingSettings | None
    autonumerate: bool
    page_title_template: str | None
    enable_pingback_out: bool
    enable_pingback_in: bool
    #: Original response dict, kept so to_dict() can round-trip fields this
    #: library does not (yet) know about instead of dropping them
    _raw: dict[str, Any] = field(repr=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SiteCategory":
        """
        Parse a single category object from a `categories` array element

        Parameters
        ----------
        data : dict[str, Any]
            Raw category object as returned by Wikidot

        Returns
        -------
        SiteCategory
        """
        permissions_str = data.get("permissions")
        rating_str = data.get("rating")
        return cls(
            category_id=data["category_id"],
            site_id=data["site_id"],
            name=data["name"],
            theme_default=bool(data.get("theme_default", False)),
            theme_id=data.get("theme_id", 0),
            layout_default=bool(data.get("layout_default", True)),
            layout_id=data.get("layout_id", 0),
            theme_external_url=data.get("theme_external_url") or "",
            permissions_default=bool(data.get("permissions_default", False)),
            permissions=PagePermissions.decode(permissions_str) if permissions_str else None,
            license_default=bool(data.get("license_default", True)),
            license_id=data.get("license_id"),
            license_other=data.get("license_other") or "",
            nav_default=bool(data.get("nav_default", True)),
            top_bar_page_name=data.get("top_bar_page_name"),
            side_bar_page_name=data.get("side_bar_page_name"),
            template_id=data.get("template_id"),
            per_page_discussion=data.get("per_page_discussion"),
            per_page_discussion_default=bool(data.get("per_page_discussion_default", True)),
            rating=RatingSettings.decode(rating_str) if rating_str else None,
            autonumerate=bool(data.get("autonumerate", False)),
            page_title_template=data.get("page_title_template"),
            enable_pingback_out=bool(data.get("enable_pingback_out", False)),
            enable_pingback_in=bool(data.get("enable_pingback_in", False)),
            _raw=data,
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Rebuild a category object for sending back to Wikidot

        Starts from `_raw` (so unknown fields survive the round trip) and
        overwrites only the fields this class models.

        Returns
        -------
        dict[str, Any]
        """
        result = dict(self._raw)
        result.update(
            category_id=self.category_id,
            site_id=self.site_id,
            name=self.name,
            theme_default=self.theme_default,
            theme_id=self.theme_id,
            layout_default=self.layout_default,
            layout_id=self.layout_id,
            theme_external_url=self.theme_external_url,
            permissions_default=self.permissions_default,
            permissions=self.permissions.encode() if self.permissions is not None else None,
            license_default=self.license_default,
            license_id=self.license_id,
            license_other=self.license_other,
            nav_default=self.nav_default,
            top_bar_page_name=self.top_bar_page_name,
            side_bar_page_name=self.side_bar_page_name,
            template_id=self.template_id,
            per_page_discussion=self.per_page_discussion,
            per_page_discussion_default=self.per_page_discussion_default,
            rating=self.rating.encode() if self.rating is not None else None,
            autonumerate=self.autonumerate,
            page_title_template=self.page_title_template,
            enable_pingback_out=self.enable_pingback_out,
            enable_pingback_in=self.enable_pingback_in,
        )
        return result

    def set_permissions(
        self,
        *,
        view: Iterable[Actor] | None = None,
        create: Iterable[Actor] | None = None,
        edit: Iterable[Actor] | None = None,
        move: Iterable[Actor] | None = None,
        delete: Iterable[Actor] | None = None,
        upload_files: Iterable[Actor] | None = None,
        rename_files: Iterable[Actor] | None = None,
        replace_files: Iterable[Actor] | None = None,
        show_options: Iterable[Actor] | None = None,
    ) -> None:
        """
        Update the specified page-permission fields, leaving the rest unchanged

        Also clears `permissions_default` (this category now has its own
        explicit permissions instead of inheriting the site default).

        Parameters
        ----------
        view, create, edit, move, delete, upload_files, rename_files,
        replace_files, show_options : Iterable[Actor] | None
            New actor set for that permission. Fields left as None are
            unchanged
        """
        current = self.permissions or PagePermissions()
        updates = {
            name: value
            for name, value in (
                ("view", view),
                ("create", create),
                ("edit", edit),
                ("move", move),
                ("delete", delete),
                ("upload_files", upload_files),
                ("rename_files", rename_files),
                ("replace_files", replace_files),
                ("show_options", show_options),
            )
            if value is not None
        }
        self.permissions = replace_actors(current, **updates)
        self.permissions_default = False


@dataclass
class SiteCategoryCollection:
    """
    The full `categories` array for a site, keyed by category name

    Never cached (see 30_plan.md D3): a new collection is fetched every
    time `SiteSettingsAccessor.update_categories` is called, so concurrent
    changes by other admins are not clobbered by a stale save.
    """

    site: "Site"
    categories: list[SiteCategory]

    def __getitem__(self, name: str) -> SiteCategory:
        """
        Look up a category by name

        Parameters
        ----------
        name : str
            Category name (e.g. "_default")

        Returns
        -------
        SiteCategory

        Raises
        ------
        KeyError
            If no category with that name exists
        """
        for category in self.categories:
            if category.name == name:
                return category
        raise KeyError(f"Category not found: {name}")

    def __iter__(self) -> Iterable[SiteCategory]:
        """Iterate over categories"""
        return iter(self.categories)

    def __len__(self) -> int:
        """Number of categories"""
        return len(self.categories)

    def names(self) -> list[str]:
        """
        Get all category names

        Returns
        -------
        list[str]
        """
        return [category.name for category in self.categories]

    @classmethod
    def fetch(cls, site: "Site", module_name: str) -> "SiteCategoryCollection":
        """
        Fetch the current `categories` array by rendering a Manage Site module

        Parameters
        ----------
        site : Site
            Site to fetch categories for
        module_name : str
            Any Manage Site module documented to embed the full `categories`
            array in its response (e.g. "managesite/ManageSitePermissionsModule")

        Returns
        -------
        SiteCategoryCollection

        Raises
        ------
        ResponseDataException
            If the response has no `categories` field
        """
        response = site.amc_request([{"moduleName": module_name}])[0]
        data = response.json()
        raw_categories = data.get("categories")
        if raw_categories is None:
            raise exceptions.ResponseDataException(f"Response has no 'categories' field: {module_name}")
        return cls(site=site, categories=[SiteCategory.from_dict(item) for item in raw_categories])

    def save(self, action: str, event: str) -> None:
        """
        Send the full `categories` array back to Wikidot

        Parameters
        ----------
        action : str
            AMC action (e.g. "ManageSiteAction")
        event : str
            AMC event (e.g. "savePermissions")
        """
        self.site.amc_request(
            [
                {
                    "action": action,
                    "event": event,
                    "categories": json_param([category.to_dict() for category in self.categories]),
                    "moduleName": "Empty",
                }
            ]
        )
