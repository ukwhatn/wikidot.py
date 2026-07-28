"""
Module for Wikidot's forum-wide admin settings (Manage Site's Forum panel)

Access through `Site.forum` (`SiteForumAccessor` in site.py), which holds
thin delegating wrappers over the functions/classes defined here — see
30_plan.md D6 ("site.forum: 既存 + フォーラム管理") and 32_tasks.md Task 4-4.

`ManageSiteForumAction/savePerPageDiscussion` is intentionally NOT
reimplemented here: it is one of the seven `categories`-backed settings
areas (permissions_default group) and already lives at
`Site.settings.set_per_page_discussion` (Task 1-4, in site_settings.py).
Duplicating its read-modify-write cycle here would give two independent
implementations of the same operation.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..common.exceptions import ResponseDataException
from ..util.amc_body import json_param
from .site_permissions import ForumPermissions

if TYPE_CHECKING:
    from .site import Site

_MODULE_GET_FORUM_LAYOUT = "managesite/ManageSiteGetForumLayoutModule"


def activate_forum(site: "Site") -> None:
    """
    Enable the forum for a site that does not have one yet

    `ManageSiteForumAction/activateForum` takes no parameters
    (40_admin-managesite.md "Forum settings").

    Parameters
    ----------
    site : Site
    """
    site.amc_request([{"action": "ManageSiteForumAction", "event": "activateForum", "moduleName": "Empty"}])


def set_forum_default_nesting(site: "Site", max_nest_level: int) -> None:
    """
    Set the forum's site-wide default reply nesting depth

    Parameters
    ----------
    site : Site
    max_nest_level : int
        0-10 (0 = flat, no nested replies)

    Raises
    ------
    ValueError
        If max_nest_level is out of range
    """
    if not (0 <= max_nest_level <= 10):
        raise ValueError(f"max_nest_level must be between 0 and 10, got {max_nest_level}")
    site.amc_request(
        [
            {
                "action": "ManageSiteForumAction",
                "event": "saveForumDefaultNesting",
                "moduleName": "Empty",
                "max_nest_level": max_nest_level,
            }
        ]
    )


@dataclass(eq=False)
class ForumLayoutGroup:
    """
    A single forum group entry from `saveForumLayout`'s `groups` array

    Attributes
    ----------
    name : str
    description : str
    visible : bool
    _raw : dict[str, Any]
        Original response object (holds `group_id` and any other field
        this library does not model), kept so `to_dict()` round-trips
        fields it does not know about instead of dropping them. Empty for
        a group created locally via `ForumLayout.add_group` (Wikidot
        assigns `group_id` on save)

    Notes
    -----
    Compares by identity (`eq=False`), not by field values: `ForumLayout`
    looks up a group's index with `list.index()`/`is`, and two distinct
    groups can legitimately share the same name/description/visible
    values.
    """

    name: str
    description: str
    visible: bool = True
    _raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ForumLayoutGroup":
        """Parse a single `groups` array element"""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            visible=bool(data.get("visible", True)),
            _raw=data,
        )

    def to_dict(self) -> dict[str, Any]:
        """Rebuild a `groups` array element for sending back to Wikidot"""
        result = dict(self._raw)
        result.update(name=self.name, description=self.description, visible=self.visible)
        return result


@dataclass(eq=False)
class ForumLayoutCategory:
    """
    A single forum category entry from `saveForumLayout`'s `categories` array

    Attributes
    ----------
    name : str
    description : str
    max_nest_level : int | None
        0-10, or None to inherit the forum's site-wide default
        (40_admin-managesite.md "Forum layout")
    category_id : int | None
        None for a category created locally that Wikidot has not assigned
        an ID to yet (assigned on save)
    number_threads : int | None
        Thread count as last reported by Wikidot. Read-only local info,
        not sent back on save (kept only so callers can guard against
        removing a non-empty category)
    _raw : dict[str, Any]
        Original response object, round-tripped like ForumLayoutGroup._raw

    Notes
    -----
    Compares by identity (`eq=False`) for the same reason as
    ForumLayoutGroup.
    """

    name: str
    description: str
    max_nest_level: int | None = None
    category_id: int | None = None
    number_threads: int | None = None
    _raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ForumLayoutCategory":
        """Parse a single `categories[groupIndex]` array element"""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            max_nest_level=data.get("max_nest_level"),
            category_id=data.get("category_id"),
            number_threads=data.get("number_threads"),
            _raw=data,
        )

    def to_dict(self) -> dict[str, Any]:
        """Rebuild a `categories[groupIndex]` array element for sending back"""
        result = dict(self._raw)
        result.update(name=self.name, description=self.description, max_nest_level=self.max_nest_level)
        if self.category_id is not None:
            result["category_id"] = self.category_id
        else:
            result.pop("category_id", None)
        return result


@dataclass
class ForumLayout:
    """
    The full forum group/category layout for a site (`saveForumLayout`'s
    read-modify-write cycle)

    `categories` is Wikidot's own two-dimensional shape: `categories[i]`
    holds the ForumLayoutCategory list belonging to `groups[i]` (same
    index). Adding/removing a group keeps both lists in sync so this
    invariant is never violated by calling code.

    `default_nesting` is informational only (as returned alongside the
    layout by `managesite/ManageSiteGetForumLayoutModule`); changing it
    goes through `set_forum_default_nesting` /
    `ManageSiteForumAction/saveForumDefaultNesting` instead, a separate
    event from `saveForumLayout` — this class does not send it back.

    Never cached: call `ForumLayout.fetch` again for the latest state
    before editing, consistent with `SiteCategoryCollection` (30_plan.md D3).
    """

    site: "Site"
    groups: list[ForumLayoutGroup]
    categories: list[list[ForumLayoutCategory]]
    default_nesting: int | None
    _deleted_groups: list[dict[str, Any]] = field(default_factory=list, repr=False)
    _deleted_category_ids: list[int] = field(default_factory=list, repr=False)

    @classmethod
    def fetch(cls, site: "Site") -> "ForumLayout":
        """
        Fetch the current forum layout

        Parameters
        ----------
        site : Site

        Returns
        -------
        ForumLayout

        Raises
        ------
        ResponseDataException
            If the response has no `groups`/`categories` field
        """
        response = site.amc_request([{"moduleName": _MODULE_GET_FORUM_LAYOUT}])[0]
        data = response.json()
        raw_groups = data.get("groups")
        raw_categories = data.get("categories")
        if raw_groups is None or raw_categories is None:
            raise ResponseDataException(f"Response has no 'groups'/'categories' field: {_MODULE_GET_FORUM_LAYOUT}")
        return cls(
            site=site,
            groups=[ForumLayoutGroup.from_dict(g) for g in raw_groups],
            categories=[[ForumLayoutCategory.from_dict(c) for c in group_cats] for group_cats in raw_categories],
            default_nesting=data.get("defaultNesting"),
        )

    def _group_index(self, group: ForumLayoutGroup) -> int:
        """Look up a group's index by identity, not by field equality"""
        for index, candidate in enumerate(self.groups):
            if candidate is group:
                return index
        raise ValueError("group does not belong to this ForumLayout")

    def add_group(self, name: str, description: str = "", visible: bool = True) -> ForumLayoutGroup:
        """
        Add a new (empty) group to the layout

        Parameters
        ----------
        name : str
        description : str, default ""
        visible : bool, default True

        Returns
        -------
        ForumLayoutGroup
            The newly created group (append categories to it via
            `add_category`)
        """
        new_group = ForumLayoutGroup(name=name, description=description, visible=visible)
        self.groups.append(new_group)
        self.categories.append([])
        return new_group

    def add_category(
        self,
        group: ForumLayoutGroup,
        name: str,
        description: str = "",
        max_nest_level: int | None = None,
    ) -> ForumLayoutCategory:
        """
        Add a new category to a group in this layout

        Parameters
        ----------
        group : ForumLayoutGroup
            Must be a group already in this layout (from `fetch` or
            `add_group`)
        name : str
        description : str, default ""
        max_nest_level : int | None, default None
            0-10, or None to inherit the forum's default

        Returns
        -------
        ForumLayoutCategory
        """
        index = self._group_index(group)
        new_category = ForumLayoutCategory(name=name, description=description, max_nest_level=max_nest_level)
        self.categories[index].append(new_category)
        return new_category

    def remove_group(self, group: ForumLayoutGroup, *, confirm: bool) -> None:
        """
        Remove a group and every category in it. Destructive and irreversible

        Wikidot's own UI refuses to delete a non-empty group client-side;
        whether the server re-validates this is unconfirmed, so this
        method does not attempt the same check — pass confirm=True to
        acknowledge you want the group (and its categories) gone
        regardless.

        Parameters
        ----------
        group : ForumLayoutGroup
            Must be a group already in this layout
        confirm : bool
            Must be explicitly True to proceed

        Raises
        ------
        ValueError
            If confirm is not True, or group does not belong to this layout
        """
        if not confirm:
            raise ValueError("remove_group is destructive; pass confirm=True to proceed")
        index = self._group_index(group)
        removed_group = self.groups.pop(index)
        removed_categories = self.categories.pop(index)
        self._deleted_groups.append(removed_group.to_dict())
        self._deleted_category_ids.extend(c.category_id for c in removed_categories if c.category_id is not None)

    def remove_category(self, group: ForumLayoutGroup, category: ForumLayoutCategory, *, confirm: bool) -> None:
        """
        Remove a single category from a group. Destructive and irreversible

        Wikidot's own UI refuses to delete a category that still has
        threads client-side (see `category.number_threads`); whether the
        server re-validates this is unconfirmed, so pass confirm=True to
        acknowledge you want it gone regardless.

        Parameters
        ----------
        group : ForumLayoutGroup
            Must be a group already in this layout
        category : ForumLayoutCategory
            Must be a category currently in `group`
        confirm : bool
            Must be explicitly True to proceed

        Raises
        ------
        ValueError
            If confirm is not True, or group/category do not belong to
            this layout
        """
        if not confirm:
            raise ValueError("remove_category is destructive; pass confirm=True to proceed")
        index = self._group_index(group)
        try:
            self.categories[index].remove(category)
        except ValueError:
            raise ValueError("category does not belong to the given group") from None
        if category.category_id is not None:
            self._deleted_category_ids.append(category.category_id)

    def save(self) -> None:
        """
        Send the layout back to Wikidot (`ManageSiteForumAction/saveForumLayout`)

        Sends `groups`, `categories`, `deleted_groups`, `deleted_categories`
        every time (Wikidot's own client always builds and submits all
        four, whether or not anything was deleted this round). Clears the
        pending-deletion lists on success.
        """
        self.site.amc_request(
            [
                {
                    "action": "ManageSiteForumAction",
                    "event": "saveForumLayout",
                    "moduleName": "Empty",
                    "groups": json_param([g.to_dict() for g in self.groups]),
                    "categories": json_param([[c.to_dict() for c in group_cats] for group_cats in self.categories]),
                    "deleted_groups": json_param(self._deleted_groups),
                    "deleted_categories": json_param(self._deleted_category_ids),
                }
            ]
        )
        self._deleted_groups = []
        self._deleted_category_ids = []


@dataclass(frozen=True)
class ForumCategoryPermissionOverride:
    """
    A single element of `saveForumPermissions`'s `categories` array:
    one forum category's permission override

    Attributes
    ----------
    category_id : int
    permissions : ForumPermissions | None
        None means "inherit the site-wide default permissions"
        (40_admin-managesite.md: "フォーラムカテゴリの permissions が null
        の場合は「サイト既定を使う」")
    """

    category_id: int
    permissions: ForumPermissions | None

    def to_dict(self) -> dict[str, Any]:
        """
        Encode as the `{category_id, permissions}` shape `saveForumPermissions` expects

        This field shape (`category_id` + `permissions`) was not directly
        observed for this specific event — no corresponding "get forum
        permissions" module response was captured during the survey,
        unlike `ManageSiteGetForumLayoutModule` for the layout side (see
        40_admin-managesite.md). It is inferred from the same two field
        names Wikidot uses consistently elsewhere for a forum category
        object (`ForumLayoutCategory.category_id`, `SiteCategory.permissions`),
        not invented from scratch. Treat `save_forum_permissions` as
        unverified against a live site until confirmed
        """
        return {
            "category_id": self.category_id,
            "permissions": self.permissions.encode() if self.permissions is not None else None,
        }


def save_forum_permissions(
    site: "Site",
    default_permissions: ForumPermissions,
    category_permissions: list[ForumCategoryPermissionOverride] | None = None,
) -> None:
    """
    Save forum-wide default permissions and any per-category overrides

    `ManageSiteForumAction/saveForumPermissions` sends the *entire*
    `categories` array like every other categories-backed save in this
    library (30_plan.md D3) — there is no read endpoint confirmed for
    this specific event (see `ForumCategoryPermissionOverride.to_dict`),
    so unlike `Site.settings`'s categories helpers this cannot offer a
    fetch-mutate-save cycle. Callers must pass the complete desired set of
    overrides; categories left out of `category_permissions` are not
    guaranteed to keep their current override (server behavior for
    omitted categories is unconfirmed).

    Parameters
    ----------
    site : Site
    default_permissions : ForumPermissions
        Site-wide default forum permissions
    category_permissions : list[ForumCategoryPermissionOverride] | None, default None
        Per forum-category overrides. Treated as empty (no overrides) if
        None

    Notes
    -----
    Does not call `login_check()` before sending, matching the convention
    already established by `site_settings.py`'s Manage Site save methods
    (none of them gate locally either — a `no_permission` response
    surfaces as `ForbiddenException` from the transport layer instead)
    """
    site.amc_request(
        [
            {
                "action": "ManageSiteForumAction",
                "event": "saveForumPermissions",
                "moduleName": "Empty",
                "default_permissions": default_permissions.encode(),
                "categories": json_param([o.to_dict() for o in (category_permissions or [])]),
            }
        ]
    )
