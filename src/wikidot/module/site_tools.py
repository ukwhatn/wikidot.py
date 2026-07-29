"""
Module for site-wide tooling views: Site Tools, Wanted Pages, Orphaned
Pages, Drafts, the category-driven page list (manage:listpages), and a
filtered recent-changes feed.

Access through `Site.tools`.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any, Literal

from bs4 import BeautifulSoup

from ..common.exceptions import NoElementException
from ..connector.ajax import require_body
from ..util.amc_body import flag, omit_falsy
from ..util.parser import odate as odate_parser
from ..util.parser import user as user_parser

if TYPE_CHECKING:
    from .site import Site, SiteChange

#: The 8 change-type flags accepted by changes/SiteChangesListModule's
#: `options` JSON (distinct from history/PageRevisionListModule's 7 -- this
#: one adds "new" and lacks nothing page history has).
RecentChangesOptionKey = Literal["all", "source", "title", "tags", "move", "files", "new", "meta"]


class SiteToolsAccessor:
    """
    Accessor for site-wide tooling views (Site Tools, Wanted/Orphaned
    Pages, Drafts, category page lists, filtered recent changes)

    Access through `Site.tools`.
    """

    def __init__(self, site: Site) -> None:
        """
        Initialize method

        Parameters
        ----------
        site : Site
            Parent site instance
        """
        self.site = site

    def get_overview(self) -> str:
        """
        Get the rendered Site Tools overview page (sitetools/SiteToolsModule)

        Returns
        -------
        str
            Rendered HTML body
        """
        response = self.site.amc_request([{"moduleName": "sitetools/SiteToolsModule"}])[0]
        return require_body(response, "sitetools/SiteToolsModule")

    def get_wanted_pages(self, page: int | None = None, embed: bool = False) -> str:
        """
        Get the Wanted Pages list (sitetools/WantedPagesModule)

        Parameters
        ----------
        page : int | None, default None
            Page number for pagination
        embed : bool, default False
            Whether to render in embedded (no-chrome) mode

        Returns
        -------
        str
            Rendered HTML body
        """
        body: dict[str, Any] = {
            "moduleName": "sitetools/WantedPagesModule",
            **omit_falsy(p=page, embed=flag(embed)),
        }
        response = self.site.amc_request([body])[0]
        return require_body(response, "sitetools/WantedPagesModule")

    def get_orphaned_pages(self) -> str:
        """
        Get the Orphaned Pages list (sitetools/OrphanedPagesModule)

        Returns
        -------
        str
            Rendered HTML body
        """
        response = self.site.amc_request([{"moduleName": "sitetools/OrphanedPagesModule"}])[0]
        return require_body(response, "sitetools/OrphanedPagesModule")

    def get_drafts(self) -> str:
        """
        Get the drafts list, scoped to Site Tools (list/ListDraftsModule)

        Returns
        -------
        str
            Rendered HTML body
        """
        response = self.site.amc_request([{"moduleName": "list/ListDraftsModule", "location": "sitetools"}])[0]
        return require_body(response, "list/ListDraftsModule")

    def get_categories(self) -> str:
        """
        Get the category list for manage:listpages (list/WikiCategoriesModule)

        Notes
        -----
        Per 50_page.md, the outer page-list body on manage:listpages is
        static HTML shipped with the page itself, not fetched via this
        module; this wraps the same module for programmatic access. Use
        `expand_category()` to get an individual category's page list.

        Returns
        -------
        str
            Rendered HTML body
        """
        response = self.site.amc_request([{"moduleName": "list/WikiCategoriesModule"}])[0]
        return require_body(response, "list/WikiCategoriesModule")

    def expand_category(self, category_id: int, include_hidden: bool = False) -> str:
        """
        Get the page list for a single category (list/WikiCategoriesPageListModule)

        Parameters
        ----------
        category_id : int
            Category ID to expand
        include_hidden : bool, default False
            Whether to include hidden pages

        Returns
        -------
        str
            Rendered HTML body
        """
        body = {
            "moduleName": "list/WikiCategoriesPageListModule",
            "category_id": category_id,
            **omit_falsy(includeHidden=flag(include_hidden)),
        }
        response = self.site.amc_request([body])[0]
        return require_body(response, "list/WikiCategoriesPageListModule")

    def get_recent_changes(
        self,
        category_id: int | None = None,
        page_id: int | None = None,
        options: dict[RecentChangesOptionKey, bool] | None = None,
        perpage: Literal[10, 20, 50, 100, 200] = 20,
        page_no: int = 1,
    ) -> list[SiteChange]:
        """
        Get recent changes with server-side filtering (changes/SiteChangesListModule)

        Unlike `Site.get_recent_changes()` (which always requests the
        unfiltered "all" feed and paginates internally up to a `limit`),
        this exposes the categoryId/pageId filtering and change-type
        options flags Wikidot's own system:recent-changes view uses. Kept
        as a separate method on this accessor, rather than as a change to
        the existing one, to avoid modifying site.py (shared with other
        in-flight work) beyond registering this accessor.

        Parameters
        ----------
        category_id : int | None, default None
            Restrict to a single category. Omitted (all categories) when None
        page_id : int | None, default None
            Restrict to a single page
        options : dict[RecentChangesOptionKey, bool] | None, default None
            Change-type filter flags. Defaults to `{"all": True}` when
            omitted. Valid keys are this module's 8 kinds --
            "all"/"source"/"title"/"tags"/"move"/"files"/"new"/"meta" --
            which differ from history/PageRevisionListModule's 7 (no "new"
            there); do not mix the two up
        perpage : Literal[10, 20, 50, 100, 200], default 20
            Items per page
        page_no : int, default 1
            Page number (1-indexed)

        Returns
        -------
        list[SiteChange]
            Changes on the requested page

        Raises
        ------
        NoElementException
            When HTML element parsing fails
        """
        from .site import SiteChange

        body: dict[str, Any] = {
            "moduleName": "changes/SiteChangesListModule",
            "perpage": str(perpage),
            "page": page_no,
            "options": json.dumps(options or {"all": True}),
            **omit_falsy(categoryId=category_id, pageId=page_id),
        }
        response = self.site.amc_request([body])[0]
        html = BeautifulSoup(require_body(response, "changes/SiteChangesListModule"), "lxml")

        changes: list[SiteChange] = []
        for item in html.select("div.changes-list-item"):
            comment_elem = item.select_one("td.comments")
            comment = comment_elem.get_text().strip() if comment_elem else None
            if comment == "":
                comment = None

            title_elem = item.select_one("td.title a")
            if title_elem is None:
                raise NoElementException("Title element is not found.")

            page_title = title_elem.get_text().strip()
            href = title_elem.get("href", "")
            page_fullname = str(href).strip("/")

            odate_elem = item.select_one("td.mod-date span.odate")
            if odate_elem is None:
                raise NoElementException("Odate element is not found.")
            changed_at = odate_parser(odate_elem)

            rev_elem = item.select_one("td.revision-no")
            if rev_elem is None:
                raise NoElementException("Revision number element is not found.")
            rev_text = rev_elem.get_text()
            rev_match = re.search(r"(\d+)", rev_text)
            if rev_match is None:
                raise NoElementException("Revision number is not found.")
            revision_no = int(rev_match.group(1))

            user_elem = item.select_one("td.mod-by span.printuser")
            if user_elem is None:
                raise NoElementException("User element is not found.")
            changed_by = user_parser(self.site.client, user_elem)

            flags_elem = item.select("td.flags span")
            change_flags = [span.get_text().strip() for span in flags_elem]

            changes.append(
                SiteChange(
                    site=self.site,
                    page_fullname=page_fullname,
                    page_title=page_title,
                    revision_no=revision_no,
                    changed_by=changed_by,
                    changed_at=changed_at,
                    flags=change_flags,
                    comment=comment,
                )
            )

        return changes
