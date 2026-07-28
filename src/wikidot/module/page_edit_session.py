"""
Module for managing Wikidot page edit sessions

Wraps the lock lifecycle of `edit/PageEditModule` (acquire on entering the
session, keep alive via `synchronize`, release via `removePageEditLock`)
behind a context manager. Wikidot holds the lock for up to 15 minutes once
`edit/PageEditModule` is requested; any code path that acquires the lock
but does not reach a successful `savePage` must release it explicitly, or
the page stays uneditable for other users until the lock expires. See
`30_plan.md` D5 in the sibling wikidot.py repo's memory directory
(`.local/memory/260728_wikidot-ajax-modules/`) for the design rationale.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from ..common import exceptions, wd_logger
from ..connector.ajax import require_body
from ..util.amc_body import checkbox, omit_falsy

if TYPE_CHECKING:
    from .site import Site

#: Edit mode accepted by edit/PageEditModule. "section" requires `section`
#: to be set; savePage then takes `range_start`/`range_end` instead.
EditMode = Literal["page", "section", "append"]


@dataclass
class PageEditSession:
    """
    A context manager representing a single Wikidot page edit session

    Acquiring the lock (via `open()` or entering the `with` block) talks to
    `edit/PageEditModule`. From that point on the lock is held until either
    `save()` succeeds or the session is released (explicitly via
    `release()`, or automatically on `__exit__` if `save()` never
    succeeded).

    Parameters
    ----------
    site : Site
        Site the page belongs to
    fullname : str
        Fullname of the page being edited
    page_id : int | None, default None
        Page ID when editing an existing page (omitted from requests, and
        must be None, when creating a new page)
    mode : Literal["page", "section", "append"], default "page"
        Edit mode
    section : int | None, default None
        Section number to edit. Required when mode is "section", used only
        when acquiring the lock (savePage instead takes range_start/range_end)
    force_lock : bool, default False
        Whether to forcibly take over a lock held by another user when
        opening the session

    Attributes
    ----------
    lock_id : str | None
        Lock ID, set once the session is open
    lock_secret : str | None
        Lock secret, set once the session is open
    revision_id : str
        Revision ID to submit with save/synchronize requests. Starts as the
        `page_revision_id` returned when the lock was acquired (empty
        string for a new page) and is not otherwise updated by this class
        (Wikidot's `and_continue` response carries a new `revisionId`, but
        that is returned to the caller from `save()` rather than folded
        back into the session, since a session is expected to end after a
        successful save)
    time_left : int | None
        Remaining lock time in seconds, last refreshed by open/synchronize/
        forceLockIntercept/recreateExpiredLock
    is_existing_page : bool
        Whether the page already existed when the lock was acquired
        (`page_revision_id` was present in the lock response)
    """

    site: Site
    fullname: str
    page_id: int | None = None
    mode: EditMode = "page"
    section: int | None = None
    force_lock: bool = False

    lock_id: str | None = field(default=None, init=False)
    lock_secret: str | None = field(default=None, init=False)
    revision_id: str = field(default="", init=False)
    time_left: int | None = field(default=None, init=False)
    is_existing_page: bool = field(default=False, init=False)
    _saved: bool = field(default=False, init=False, repr=False)
    _locked: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.mode == "section" and self.section is None:
            raise ValueError('section must be specified when mode is "section"')

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def open(self) -> PageEditSession:
        """
        Acquire the edit lock (edit/PageEditModule)

        Equivalent to entering the session via `with`; provided separately
        for callers that need finer control over when release() happens
        than a single `with` block allows.

        Returns
        -------
        PageEditSession
            Self, for chaining (`with PageEditSession(...).open() as ed:`
            also works, though entering via `with` alone already opens it)

        Raises
        ------
        LoginRequiredException
            When not logged in
        TargetErrorException
            When the page is locked by another user (lock was never
            acquired, so nothing needs releasing)
        """
        self.site.client.login_check()

        body: dict[str, Any] = {
            "mode": self.mode,
            "wiki_page": self.fullname,
            "moduleName": "edit/PageEditModule",
        }
        if self.page_id is not None:
            body["page_id"] = self.page_id
        if self.mode == "section":
            body["section"] = self.section
        if self.force_lock:
            body["force_lock"] = "yes"

        response = self.site.amc_request([body])[0]
        data = response.json()

        if data.get("locked") or data.get("other_locks"):
            raise exceptions.TargetErrorException(f"Page {self.fullname} is locked or other locks exist")

        self.is_existing_page = "page_revision_id" in data
        self.lock_id = data["lock_id"]
        self.lock_secret = data["lock_secret"]
        self.revision_id = str(data.get("page_revision_id", ""))
        self.time_left = data.get("timeLeft")
        self._locked = True
        return self

    def __enter__(self) -> PageEditSession:
        return self.open()

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._locked and not self._saved:
            self.release()

    def _require_open(self) -> None:
        if not self._locked:
            raise exceptions.UnexpectedException("Edit session is not open; call open() or enter it via 'with' first")

    def _lock_params(self) -> dict[str, Any]:
        """Common lock-identifying params shared by save/synchronize."""
        self._require_open()
        params: dict[str, Any] = {
            "mode": self.mode,
            "wiki_page": self.fullname,
            "lock_id": self.lock_id,
            "lock_secret": self.lock_secret,
            "revision_id": self.revision_id,
        }
        if self.page_id is not None:
            params["page_id"] = self.page_id
        return params

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------

    def save(
        self,
        title: str = "",
        source: str = "",
        comment: str = "",
        and_continue: bool = False,
        range_start: int | None = None,
        range_end: int | None = None,
        tags: str | None = None,
        parent_page: str | None = None,
        dont_notify_watchers: bool = False,
    ) -> dict[str, Any]:
        """
        Save the page (WikiPageAction/savePage)

        Parameters
        ----------
        title : str, default ""
            New title
        source : str, default ""
            New source code (Wikidot markup)
        comment : str, default ""
            Edit comment
        and_continue : bool, default False
            Save and keep the lock/editor open (Wikidot returns a fresh
            `revisionId` in this case, exposed via the returned dict)
        range_start : int | None, default None
            Start of the edited range. Only meaningful when mode is "section"
        range_end : int | None, default None
            End of the edited range. Only meaningful when mode is "section"
        tags : str | None, default None
            Space-separated tags, only used when creating a page via a
            /tags/... URL
        parent_page : str | None, default None
            Parent page fullname, only used when creating a page via a
            /parentPage/... URL
        dont_notify_watchers : bool, default False
            Suppress the "page updated" notification to watchers

        Returns
        -------
        dict[str, Any]
            Raw response data (e.g. `pageUnixName` on rename, `revisionId`
            when and_continue is set)

        Raises
        ------
        FormErrorsException
            Validation failure (raised by the AMC client layer; the
            per-field messages are under `errors`)
        WikidotStatusCodeException
            Any other non-"ok" status
        TargetErrorException
            The lock was lost mid-edit (`noLockError` in the response)
        """
        body = {
            "action": "WikiPageAction",
            "event": "savePage",
            "moduleName": "Empty",
            **self._lock_params(),
            "title": title,
            "source": source,
            "comments": comment,
            **omit_falsy(
                and_continue="yes" if and_continue else False,
                range_start=range_start,
                range_end=range_end,
                tags=tags,
                parentPage=parent_page,
                dont_notify_watchers=checkbox(dont_notify_watchers),
            ),
        }

        response = self.site.amc_request([body])[0]
        data = response.json()

        if data["status"] != "ok":
            raise exceptions.WikidotStatusCodeException(f"Failed to save page: {self.fullname}", data["status"], data)

        # Wikidot reports lock loss as `noLockError: true` alongside status
        # "ok", not as a distinct status value (per 50_page.md), so this is
        # checked separately from the status branch above.
        if data.get("noLockError"):
            raise exceptions.TargetErrorException(
                f"Edit lock lost while saving page {self.fullname}: {data.get('body', '')}"
            )

        self._saved = True
        return data

    def synchronize(self, since_last_input: int = 0) -> dict[str, Any]:
        """
        Keep the edit lock alive (WikiPageAction/synchronize)

        Call periodically (Wikidot's own client does so every 60 seconds,
        or sooner if fewer than 60 seconds remain and there has been
        input) while the editor stays open without saving.

        Parameters
        ----------
        since_last_input : int, default 0
            Seconds elapsed since the last user input

        Returns
        -------
        dict[str, Any]
            Raw response data (`timeLeft`, `savedDraft`, `lockRecreated`, ...)

        Raises
        ------
        TargetErrorException
            The lock was lost (`noLockError` in the response)
        """
        body = {
            "action": "WikiPageAction",
            "event": "synchronize",
            "moduleName": "Empty",
            **self._lock_params(),
            "since_last_input": since_last_input,
        }
        response = self.site.amc_request([body])[0]
        data = response.json()

        if data.get("noLockError"):
            raise exceptions.TargetErrorException(f"Edit lock lost for page {self.fullname}")

        # Wikidot may recreate the lock transparently (e.g. after a brief
        # server-side expiry); the response then carries fresh
        # camelCase lockId/lockSecret that must replace the ones used to
        # acquire the lock, or subsequent save()/synchronize() calls fail.
        if data.get("lockRecreated"):
            self.lock_id = data["lockId"]
            self.lock_secret = data["lockSecret"]

        self.time_left = data.get("timeLeft")
        return data

    def check_draft_exists(self, title: str = "", source: str = "", comment: str = "") -> bool:
        """
        Check whether a draft already exists for this lock (WikiPageAction/checkDraftExists)

        Parameters
        ----------
        title : str, default ""
            Current in-progress title
        source : str, default ""
            Current in-progress source
        comment : str, default ""
            Current in-progress comment

        Returns
        -------
        bool
            Whether a draft exists

        Notes
        -----
        The wire format echoes `form(edit-page-form)` back to the server
        alongside the lock identifiers (per 30_action-catalog.md); this
        implementation sends title/source/comments for that form, but the
        exact reason the server wants the in-progress content for this
        check (as opposed to just the lock id) is not documented upstream,
        so this is an implementation judgment call rather than a confirmed
        wire contract.
        """
        body = {
            "action": "WikiPageAction",
            "event": "checkDraftExists",
            "moduleName": "Empty",
            "wiki_page": self.fullname,
            "lock_id": self.lock_id,
            "title": title,
            "source": source,
            "comments": comment,
            **omit_falsy(page_id=self.page_id),
        }
        response = self.site.amc_request([body])[0]
        return bool(response.json().get("draftExists"))

    def force_lock_intercept(self) -> dict[str, Any]:
        """
        Forcibly take over another user's lock (WikiPageAction/forceLockIntercept)

        Unlike `force_lock=True` on the session (used when first acquiring
        the lock), this is for a session that already holds a lock and
        wants to intercept a newer lock taken by someone else in the
        meantime.

        Returns
        -------
        dict[str, Any]
            Raw response data (`timeLeft`, `nonrecoverable`, `body`,
            `error`, ...). On success this session's lock_id/lock_secret
            are updated in place
        """
        body = {
            "action": "WikiPageAction",
            "event": "forceLockIntercept",
            "moduleName": "Empty",
            **self._lock_params(),
        }
        response = self.site.amc_request([body])[0]
        data = response.json()

        if "lock_id" in data:
            self.lock_id = data["lock_id"]
        if "lock_secret" in data:
            self.lock_secret = data["lock_secret"]
        self.time_left = data.get("timeLeft")
        return data

    def recreate_expired_lock(self) -> dict[str, Any]:
        """
        Recreate an expired lock (WikiPageAction/recreateExpiredLock)

        Returns
        -------
        dict[str, Any]
            Raw response data (`lockRecreated`, `lockId`, `lockSecret`,
            `timeLeft`). On success this session's lock_id/lock_secret are
            updated in place
        """
        body = {
            "action": "WikiPageAction",
            "event": "recreateExpiredLock",
            "moduleName": "Empty",
            **self._lock_params(),
            "since_last_input": 0,
        }
        response = self.site.amc_request([body])[0]
        data = response.json()

        if data.get("lockRecreated"):
            self.lock_id = data["lockId"]
            self.lock_secret = data["lockSecret"]
        self.time_left = data.get("timeLeft")
        return data

    def release(self, leave_draft: bool = False) -> None:
        """
        Release the edit lock (WikiPageAction/removePageEditLock)

        Safe to call multiple times or on a session that was never opened
        (no-op in that case). Failures are logged, not raised, so calling
        this from `__exit__` never masks whatever error triggered the exit.

        Parameters
        ----------
        leave_draft : bool, default False
            Whether to keep the in-progress content as a draft instead of
            discarding it
        """
        if not self._locked:
            return
        body: dict[str, Any] = {
            "action": "WikiPageAction",
            "event": "removePageEditLock",
            "moduleName": "Empty",
            "lock_id": self.lock_id,
            "lock_secret": self.lock_secret,
            "wiki_page": self.fullname,
            **omit_falsy(leave_draft=leave_draft, page_id=self.page_id),
        }
        try:
            self.site.amc_request([body])
        except Exception:
            wd_logger.exception(f"Failed to release page edit lock for {self.fullname} (lock_id={self.lock_id})")
        finally:
            self._locked = False

    def preview(
        self,
        title: str = "",
        source: str = "",
        page_unix_name: str | None = None,
        range_start: int | None = None,
        range_end: int | None = None,
    ) -> dict[str, str]:
        """
        Render a preview of in-progress content (edit/PagePreviewModule)

        Parameters
        ----------
        title : str, default ""
            In-progress title
        source : str, default ""
            In-progress source
        page_unix_name : str | None, default None
            Page unix name to preview under. Defaults to this session's
            fullname
        range_start : int | None, default None
            Start of the edited range (mode="section" only)
        range_end : int | None, default None
            End of the edited range (mode="section" only)

        Returns
        -------
        dict[str, str]
            `{"body": <rendered HTML>, "title": <rendered title>}`
        """
        self._require_open()
        body = {
            "moduleName": "edit/PagePreviewModule",
            "mode": self.mode,
            "revision_id": self.revision_id,
            "title": title,
            "source": source,
            "page_unix_name": page_unix_name or self.fullname,
            **omit_falsy(pageId=self.page_id, range_start=range_start, range_end=range_end),
        }
        response = self.site.amc_request([body])[0]
        data = response.json()
        return {"body": require_body(response, "edit/PagePreviewModule"), "title": data.get("title", "")}

    def diff(
        self,
        title: str = "",
        source: str = "",
        range_start: int | None = None,
        range_end: int | None = None,
    ) -> str:
        """
        Render a diff of in-progress content against the base revision (edit/PageEditDiffModule)

        Parameters
        ----------
        title : str, default ""
            In-progress title
        source : str, default ""
            In-progress source
        range_start : int | None, default None
            Start of the edited range (mode="section" only)
        range_end : int | None, default None
            End of the edited range (mode="section" only)

        Returns
        -------
        str
            Rendered diff HTML
        """
        self._require_open()
        body = {
            "moduleName": "edit/PageEditDiffModule",
            "mode": self.mode,
            "revision_id": self.revision_id,
            "title": title,
            "source": source,
            **omit_falsy(range_start=range_start, range_end=range_end),
        }
        response = self.site.amc_request([body])[0]
        return require_body(response, "edit/PageEditDiffModule")
