"""
Module for handling Wikidot page edit history (revisions)

This module provides classes and functions related to Wikidot page edit history (revisions).
It enables operations such as retrieving revisions, getting source code, and displaying HTML.
"""

import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal, Optional

import httpx
from bs4 import BeautifulSoup

from ..common.exceptions import NoElementException
from ..connector.ajax import require_body
from ..util.amc_body import omit_falsy
from ..util.parser import odate as odate_parser
from ..util.parser import user as user_parser
from .page_source import PageSource

if TYPE_CHECKING:
    from .page import Page
    from .user import AbstractUser


#: The 7 change-type flags accepted by history/PageRevisionListModule's
#: `options` JSON. Distinct from UserChangesListModule's Dashboard-side
#: options, which lack "tags" (see 32_tasks.md Task 3-3).
HistoryOptionKey = Literal["all", "source", "title", "move", "tags", "files", "meta"]


def parse_revision_list_html(page: "Page", body_html: BeautifulSoup) -> list["PageRevision"]:
    """
    Parse a history/PageRevisionListModule response body into PageRevision objects

    Shared by PageCollection._acquire_page_revisions (page.py, the eager
    full-history fetch behind Page.revisions) and
    PageRevisionCollection.acquire (filtered/paginated fetch), so the
    table-row parsing logic lives in one place.

    Parameters
    ----------
    page : Page
        Page the revisions belong to
    body_html : BeautifulSoup
        Parsed response body

    Returns
    -------
    list[PageRevision]
        Parsed revisions, in the order they appear in the table

    Raises
    ------
    NoElementException
        When a required element is not found in a revision row
    """
    revs: list[PageRevision] = []
    for rev_element in body_html.select("table.page-history > tr[id^=revision-row-]"):
        rev_id = int(str(rev_element["id"]).removeprefix("revision-row-"))

        tds = rev_element.select("td")
        rev_no = int(tds[0].text.strip().removesuffix("."))
        created_by_elem = tds[4].select_one("span.printuser")
        if created_by_elem is None:
            raise NoElementException(f"Cannot find created by element for page: {page.fullname}, revision: {rev_id}")
        created_by = user_parser(page.site.client, created_by_elem)

        created_at_elem = tds[5].select_one("span.odate")
        if created_at_elem is None:
            raise NoElementException(f"Cannot find created at element for page: {page.fullname}, revision: {rev_id}")
        created_at = odate_parser(created_at_elem)

        comment = tds[6].text.strip()

        revs.append(
            PageRevision(
                page=page,
                id=rev_id,
                rev_no=rev_no,
                created_by=created_by,
                created_at=created_at,
                comment=comment,
            )
        )
    return revs


class PageRevisionCollection(list["PageRevision"]):
    """
    Class representing a collection of page revisions

    A list extension class for storing and operating on multiple versions of a page's
    edit history (revisions) in bulk. Provides convenient functions such as
    batch retrieval of source code and HTML.
    """

    page: "Page | None"

    def __init__(
        self,
        page: Optional["Page"] = None,
        revisions: list["PageRevision"] | None = None,
    ):
        """
        Initialize the collection

        Parameters
        ----------
        page : Page | None, default None
            The page the revisions belong to. If None, inferred from the first revision
        revisions : list[PageRevision] | None, default None
            List of revisions to store
        """
        super().__init__(revisions or [])
        self.page = page or self[0].page if len(self) > 0 else None

    def __iter__(self) -> Iterator["PageRevision"]:
        """
        Return an iterator over the revisions in the collection

        Returns
        -------
        Iterator[PageRevision]
            Iterator of revision objects
        """
        return super().__iter__()

    def find(self, id: int) -> Optional["PageRevision"]:
        """
        Get the revision with the specified ID

        Parameters
        ----------
        id : int
            The ID of the revision to retrieve

        Returns
        -------
        PageRevision | None
            The revision with the specified ID, or None if not found
        """
        for revision in self:
            if revision.id == id:
                return revision
        return None

    @staticmethod
    def _generic_acquire(
        page: "Page",
        revisions: list["PageRevision"],
        check_acquired_func: Callable[["PageRevision"], bool],
        module_name: str,
        process_response_func: Callable[["PageRevision", httpx.Response, "Page"], None],
    ) -> list["PageRevision"]:
        """
        Generic method for batch retrieval of revision data

        Parameters
        ----------
        page : Page
            The page the revisions belong to
        revisions : list[PageRevision]
            List of revisions to retrieve data for
        check_acquired_func : callable
            Function to check if data is already acquired
        module_name : str
            Module name to use in AMC request
        process_response_func : callable
            Function to process the response (revision, response, page) -> None

        Returns
        -------
        list[PageRevision]
            List of revisions with updated data
        """
        target_revisions = [revision for revision in revisions if not check_acquired_func(revision)]

        if len(target_revisions) == 0:
            return revisions

        responses = page.site.amc_request(
            [{"moduleName": module_name, "revision_id": revision.id} for revision in target_revisions]
        )

        for revision, response in zip(target_revisions, responses, strict=True):
            process_response_func(revision, response, page)

        return revisions

    @staticmethod
    def _acquire_sources(page: "Page", revisions: list["PageRevision"]) -> list["PageRevision"]:
        """
        Internal method to batch retrieve source code for multiple revisions

        Requests and retrieves source code for revisions that haven't been fetched yet.

        Parameters
        ----------
        page : Page
            The page the revisions belong to
        revisions : list[PageRevision]
            List of revisions to retrieve source code for

        Returns
        -------
        list[PageRevision]
            List of revisions with updated source code information

        Raises
        ------
        NoElementException
            If source element is not found
        """

        def process_source_response(revision: "PageRevision", response: httpx.Response, page: "Page") -> None:
            body = require_body(response, "history/PageSourceModule")
            # Replace nbsp with space
            body = body.replace("&nbsp;", " ")
            body_html = BeautifulSoup(body, "lxml")
            wiki_text_elem = body_html.select_one("div.page-source")
            if wiki_text_elem is None:
                raise NoElementException("Wiki text element not found")
            revision.source = PageSource(
                page=page,
                wiki_text=wiki_text_elem.get_text().strip(),
            )

        return PageRevisionCollection._generic_acquire(
            page,
            revisions,
            lambda r: r.is_source_acquired(),
            "history/PageSourceModule",
            process_source_response,
        )

    def get_sources(self) -> "PageRevisionCollection":
        """
        Get source code for all revisions in the collection

        Returns
        -------
        PageRevisionCollection
            Self (for method chaining)
        """
        if self.page is None:
            raise ValueError("Page is not set for this collection")
        self._acquire_sources(self.page, self)
        return self

    @staticmethod
    def _acquire_htmls(page: "Page", revisions: list["PageRevision"]) -> list["PageRevision"]:
        """
        Internal method to batch retrieve HTML display for multiple revisions

        Requests and retrieves HTML for revisions that haven't been fetched yet.

        Parameters
        ----------
        page : Page
            The page the revisions belong to
        revisions : list[PageRevision]
            List of revisions to retrieve HTML for

        Returns
        -------
        list[PageRevision]
            List of revisions with updated HTML information
        """

        def process_html_response(revision: "PageRevision", response: httpx.Response, page: "Page") -> None:
            body = require_body(response, "history/PageVersionModule")
            # onclick="document.getElementById('page-version-info').style.display='none'">(.*?)</a>\n\t</div>\n\n\n\n
            # 以降をソースとして取得
            source = body.split(
                "onclick=\"document.getElementById('page-version-info').style.display='none'\">",
                maxsplit=1,
            )[1]
            source = source.split("</a>\n\t</div>\n\n\n\n", maxsplit=1)[1]
            revision._html = source

        return PageRevisionCollection._generic_acquire(
            page,
            revisions,
            lambda r: r.is_html_acquired(),
            "history/PageVersionModule",
            process_html_response,
        )

    def get_htmls(self) -> "PageRevisionCollection":
        """
        Get HTML display for all revisions in the collection

        Returns
        -------
        PageRevisionCollection
            Self (for method chaining)
        """
        if self.page is None:
            raise ValueError("Page is not set for this collection")
        self._acquire_htmls(self.page, self)
        return self

    @staticmethod
    def get_diff(page: "Page", from_revision_id: int, to_revision_id: int, show_type: str = "inline") -> str:
        """
        Get an HTML diff between two revisions (history/PageDiffModule)

        Parameters
        ----------
        page : Page
            Page the revisions belong to
        from_revision_id : int
            Revision ID to diff from
        to_revision_id : int
            Revision ID to diff to
        show_type : str, default "inline"
            Diff display type

        Returns
        -------
        str
            Rendered diff HTML
        """
        response = page.site.amc_request(
            [
                {
                    "moduleName": "history/PageDiffModule",
                    "from_revision_id": from_revision_id,
                    "to_revision_id": to_revision_id,
                    "show_type": show_type,
                }
            ]
        )[0]
        return require_body(response, "history/PageDiffModule")

    @staticmethod
    def acquire(
        page: "Page",
        options: "dict[HistoryOptionKey, bool] | None" = None,
        perpage: Literal[20, 50, 100, 200] = 20,
        page_no: int = 1,
    ) -> "PageRevisionCollection":
        """
        Get a page's revision history with server-side filtering (history/PageRevisionListModule)

        Unlike the eager full-history fetch behind `Page.revisions`
        (`PageCollection._acquire_page_revisions`, which always requests
        `{"all": True}` with a huge perpage to populate the whole
        collection), this exposes the change-type filter and pagination
        Wikidot's own history view uses.

        Parameters
        ----------
        page : Page
            Page to fetch history for
        options : dict[HistoryOptionKey, bool] | None, default None
            Change-type filter flags. Defaults to `{"all": True}` when
            omitted. Valid keys are the page history view's 7 kinds --
            "all"/"source"/"title"/"move"/"tags"/"files"/"meta" -- which
            differ from the Dashboard-side UserChangesListModule's options
            (no "tags" there); do not mix the two up
        perpage : Literal[20, 50, 100, 200], default 20
            Items per page (matches Wikidot's own #h-perpage choices)
        page_no : int, default 1
            Page number (1-indexed)

        Returns
        -------
        PageRevisionCollection
            Revisions on the requested page of history
        """
        response = page.site.amc_request(
            [
                {
                    "moduleName": "history/PageRevisionListModule",
                    "page_id": page.id,
                    "page": page_no,
                    "perpage": perpage,
                    "options": json.dumps(options or {"all": True}),
                }
            ]
        )[0]
        body = require_body(response, "history/PageRevisionListModule")
        body_html = BeautifulSoup(body, "lxml")
        return PageRevisionCollection(page, parse_revision_list_html(page, body_html))


@dataclass
class PageRevision:
    """
    Class representing a page revision (version in edit history)

    Holds information about a specific version of a page. Provides basic information
    such as revision number, creator, creation date, and edit comment, along with
    access to source code and HTML display.

    Attributes
    ----------
    page : Page
        The page this revision belongs to
    id : int
        Revision ID
    rev_no : int
        Revision number
    created_by : AbstractUser
        The creator of the revision
    created_at : datetime
        The creation date and time of the revision
    comment : str
        Edit comment
    _source : PageSource | None, default None
        The revision's source code (internal cache)
    _html : str | None, default None
        The revision's HTML display (internal cache)
    """

    page: "Page"
    id: int
    rev_no: int
    created_by: "AbstractUser"
    created_at: datetime
    comment: str
    _source: Optional["PageSource"] = None
    _html: str | None = None

    def is_source_acquired(self) -> bool:
        """
        Check if source code has already been acquired

        Returns
        -------
        bool
            True if source code is acquired, False otherwise
        """
        return self._source is not None

    def is_html_acquired(self) -> bool:
        """
        Check if HTML display has already been acquired

        Returns
        -------
        bool
            True if HTML display is acquired, False otherwise
        """
        return self._html is not None

    @property
    def source(self) -> Optional["PageSource"]:
        """
        Get the revision's source code

        Automatically fetches the source code if not yet acquired.

        Returns
        -------
        PageSource | None
            The revision's source code
        """
        if not self.is_source_acquired():
            PageRevisionCollection(self.page, [self]).get_sources()
        return self._source

    @source.setter
    def source(self, value: "PageSource") -> None:
        """
        Set the revision's source code

        Parameters
        ----------
        value : PageSource
            The source code to set
        """
        self._source = value

    @property
    def html(self) -> str | None:
        """
        Get the revision's HTML display

        Automatically fetches the HTML display if not yet acquired.

        Returns
        -------
        str | None
            The revision's HTML display
        """
        if not self.is_html_acquired():
            PageRevisionCollection(self.page, [self]).get_htmls()
        return self._html

    @html.setter
    def html(self, value: str) -> None:
        """
        Set the revision's HTML display

        Parameters
        ----------
        value : str
            The HTML display to set
        """
        self._html = value

    def revert(self, force: bool = False) -> dict[str, Any]:
        """
        Revert the page to this revision (WikiPageAction/revert)

        Parameters
        ----------
        force : bool, default False
            Whether to force the revert despite an active edit lock held
            by someone else

        Returns
        -------
        dict[str, Any]
            Raw response data. On a lock conflict (force not set, or set
            but still refused), the response carries `locks` + `body`
            describing the conflicting lock instead of completing the
            revert; the caller is responsible for inspecting this rather
            than the exception being raised here, since a lock conflict is
            reported as `status: "ok"` with these extra keys

        Raises
        ------
        LoginRequiredException
            When not logged in
        """
        self.page.site.client.login_check()
        body = {
            "action": "WikiPageAction",
            "event": "revert",
            "moduleName": "Empty",
            "pageId": self.page.id,
            "revisionId": self.id,
            **omit_falsy(force="yes" if force else False),
        }
        response = self.page.site.amc_request([body])[0]
        return response.json()
