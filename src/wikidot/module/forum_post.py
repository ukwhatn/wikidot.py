"""
Module for handling Wikidot forum posts

This module provides classes and functionality related to Wikidot forum posts (individual messages within threads).
It enables operations such as retrieving post information and display.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from bs4 import BeautifulSoup, Tag

from ..common.exceptions import NoElementException
from ..util.parser import odate as odate_parser
from ..util.parser import user as user_parser

if TYPE_CHECKING:
    from .forum_post_revision import ForumPostRevisionCollection
    from .forum_thread import ForumThread
    from .user import AbstractUser


class ForumPostCollection(list["ForumPost"]):
    """
    Class representing a collection of forum posts

    A list extension class for storing multiple posts within a forum thread and performing batch operations。
    """

    thread: "ForumThread"

    def __init__(
        self,
        thread: Optional["ForumThread"] = None,
        posts: list["ForumPost"] | None = None,
    ):
        """
        Initialization method

        Parameters
        ----------
        thread : ForumThread | None, default None
            The thread the posts belong to。If None, inferred from the first post
        posts : list[ForumPost] | None, default None
            List of posts to store
        """
        super().__init__(posts or [])

        if thread is not None:
            self.thread = thread
        else:
            self.thread = self[0].thread

    def __iter__(self) -> Iterator["ForumPost"]:
        """
        Iterator that returns posts in the collection sequentially

        Returns
        -------
        Iterator[ForumPost]
            Iterator of post objects
        """
        return super().__iter__()

    def find(self, id: int) -> Optional["ForumPost"]:
        """
        Retrieve a post with the specified ID

        Parameters
        ----------
        id : int
            Post ID to retrieve

        Returns
        -------
        ForumPost | None
            Post with the specified ID, or None if it does not exist
        """
        for post in self:
            if post.id == id:
                return post
        return None

    @staticmethod
    def _parse(thread: "ForumThread", html: BeautifulSoup) -> list["ForumPost"]:
        """
        Parse post list from HTML

        Parameters
        ----------
        thread : ForumThread
            The thread the posts belong to
        html : BeautifulSoup
            HTML to parse

        Returns
        -------
        list[ForumPost]
            List of parsed posts

        Raises
        ------
        NoElementException
            If required elements are not found
        """
        posts: list[ForumPost] = []
        # Use attribute selector to get only top-level posts (with id starting with "post-")
        post_elements = html.select("div.post[id^='post-']")

        for post_elem in post_elements:
            post_id_attr = post_elem.get("id")
            if post_id_attr is None:
                raise NoElementException("Post ID attribute is not found.")
            post_id = int(str(post_id_attr).removeprefix("post-"))

            # 親Post IDの取得
            parent_id: int | None = None
            parent_container = post_elem.parent
            if parent_container is not None:
                grandparent = parent_container.parent
                if grandparent is not None and grandparent.name != "body":
                    grandparent_class = grandparent.get("class")
                    if isinstance(grandparent_class, list) and "post-container" in grandparent_class:
                        parent_post = grandparent.find("div", class_="post", recursive=False)
                        if parent_post is not None and hasattr(parent_post, "get"):
                            parent_id_attr = parent_post.get("id")
                            if parent_id_attr is not None:
                                parent_id = int(str(parent_id_attr).removeprefix("post-"))

            # タイトルと本文の取得
            # Use :scope > to get direct children only (avoid matching nested pseudo-posts)
            wrapper = post_elem.select_one(":scope > div.long")
            if wrapper is None:
                raise NoElementException("Post wrapper element is not found.")

            head = wrapper.select_one(":scope > div.head")
            if head is None:
                raise NoElementException("Post head element is not found.")

            title_elem = head.select_one(":scope > div.title")
            if title_elem is None:
                raise NoElementException("Post title element is not found.")
            title = title_elem.get_text().strip()

            content_elem = wrapper.select_one(":scope > div.content")
            if content_elem is None:
                raise NoElementException("Post content element is not found.")
            text = str(content_elem)

            # 投稿者と日時
            info_elem = head.select_one(":scope > div.info")
            if info_elem is None:
                raise NoElementException("Post info element is not found.")

            user_elem = info_elem.select_one("span.printuser")
            if user_elem is None:
                raise NoElementException("Post user element is not found.")
            created_by = user_parser(thread.site.client, user_elem)

            odate_elem = info_elem.select_one("span.odate")
            if odate_elem is None:
                raise NoElementException("Post odate element is not found.")
            created_at = odate_parser(odate_elem)

            # 編集情報（存在する場合）
            edited_by = None
            edited_at = None
            changes_elem = wrapper.select_one("div.changes")
            if changes_elem is not None:
                edit_user_elem = changes_elem.select_one("span.printuser")
                edit_odate_elem = changes_elem.select_one("span.odate")
                if edit_user_elem is not None and edit_odate_elem is not None:
                    edited_by = user_parser(thread.site.client, edit_user_elem)
                    edited_at = odate_parser(edit_odate_elem)

            post = ForumPost(
                thread=thread,
                id=post_id,
                title=title,
                text=text,
                element=post_elem,
                created_by=created_by,
                created_at=created_at,
                edited_by=edited_by,
                edited_at=edited_at,
                _parent_id=parent_id,
            )
            posts.append(post)

        return posts

    @staticmethod
    def acquire_all_in_thread(thread: "ForumThread") -> "ForumPostCollection":
        """
        Retrieve all posts in a thread

        Retrieves all posts in the specified thread。
        Traverses all pages if pagination exists。

        Parameters
        ----------
        thread : ForumThread
            Thread to retrieve posts from

        Returns
        -------
        ForumPostCollection
            Collection containing all posts in the thread

        Raises
        ------
        NoElementException
            If HTML element parsing fails
        """
        posts: list[ForumPost] = []

        first_response = thread.site.amc_request(
            [
                {
                    "moduleName": "forum/ForumViewThreadPostsModule",
                    "pageNo": "1",
                    "t": str(thread.id),
                }
            ]
        )[0]

        first_body = first_response.json()["body"]
        first_html = BeautifulSoup(first_body, "lxml")

        posts.extend(ForumPostCollection._parse(thread, first_html))

        # ページネーション確認
        pager = first_html.select_one("div.pager")
        if pager is None:
            return ForumPostCollection(thread=thread, posts=posts)

        pager_targets = pager.select("span.target")
        if len(pager_targets) < 2:
            return ForumPostCollection(thread=thread, posts=posts)

        last_page = int(pager_targets[-2].get_text().strip())
        if last_page <= 1:
            return ForumPostCollection(thread=thread, posts=posts)

        # 残りのページを取得
        responses = thread.site.amc_request(
            [
                {
                    "moduleName": "forum/ForumViewThreadPostsModule",
                    "pageNo": str(page),
                    "t": str(thread.id),
                }
                for page in range(2, last_page + 1)
            ]
        )

        for response in responses:
            body = response.json()["body"]
            html = BeautifulSoup(body, "lxml")
            posts.extend(ForumPostCollection._parse(thread, html))

        return ForumPostCollection(thread=thread, posts=posts)

    @staticmethod
    def acquire_all_in_threads(
        threads: list["ForumThread"],
    ) -> dict[int, "ForumPostCollection"]:
        """
        Retrieve all posts from multiple threads

        Batch retrieves all posts from the specified threads.
        Handles pagination for each thread.

        Parameters
        ----------
        threads : list[ForumThread]
            List of threads to retrieve posts from

        Returns
        -------
        dict[int, ForumPostCollection]
            Dictionary mapping thread ID to ForumPostCollection

        Raises
        ------
        NoElementException
            If HTML element parsing fails
        """
        if len(threads) == 0:
            return {}

        result: dict[int, ForumPostCollection] = {}
        site = threads[0].site

        # Step 1: Get the first page of all threads
        first_page_responses = site.amc_request(
            [
                {
                    "moduleName": "forum/ForumViewThreadPostsModule",
                    "pageNo": "1",
                    "t": str(thread.id),
                }
                for thread in threads
            ]
        )

        # Step 2: Parse first pages and determine pagination
        additional_requests: list[tuple[ForumThread, int]] = []

        for thread, response in zip(threads, first_page_responses, strict=True):
            body = response.json()["body"]
            html = BeautifulSoup(body, "lxml")

            posts = ForumPostCollection._parse(thread, html)
            result[thread.id] = ForumPostCollection(thread=thread, posts=posts)

            # Check pagination
            pager = html.select_one("div.pager")
            if pager is None:
                continue

            pager_targets = pager.select("span.target")
            if len(pager_targets) < 2:
                continue

            last_page = int(pager_targets[-2].get_text().strip())
            if last_page <= 1:
                continue

            # Queue additional page requests
            for page in range(2, last_page + 1):
                additional_requests.append((thread, page))

        # Step 3: Fetch additional pages
        if len(additional_requests) > 0:
            additional_responses = site.amc_request(
                [
                    {
                        "moduleName": "forum/ForumViewThreadPostsModule",
                        "pageNo": str(page),
                        "t": str(thread.id),
                    }
                    for thread, page in additional_requests
                ]
            )

            for (thread, _page), response in zip(additional_requests, additional_responses, strict=True):
                body = response.json()["body"]
                html = BeautifulSoup(body, "lxml")
                posts = ForumPostCollection._parse(thread, html)
                result[thread.id].extend(posts)

        return result

    @staticmethod
    def _acquire_post_sources(thread: "ForumThread", posts: list["ForumPost"]) -> list["ForumPost"]:
        """
        Internal method to retrieve post sources

        Batch retrieves source code (Wikidot syntax) for specified posts.

        Parameters
        ----------
        thread : ForumThread
            Thread to which posts belong
        posts : list[ForumPost]
            List of target posts

        Returns
        -------
        list[ForumPost]
            List of posts with updated source information

        Raises
        ------
        NoElementException
            When source elements are not found
        """
        if len(posts) == 0:
            return posts

        target_posts = [post for post in posts if post._source is None]

        if len(target_posts) == 0:
            return posts

        responses = thread.site.amc_request(
            [
                {
                    "moduleName": "forum/sub/ForumEditPostFormModule",
                    "threadId": thread.id,
                    "postId": post.id,
                }
                for post in target_posts
            ]
        )

        for post, response in zip(target_posts, responses, strict=True):
            html = BeautifulSoup(response.json()["body"], "lxml")
            source_elem = html.select_one("textarea[name='source']")
            if source_elem is None:
                raise NoElementException(f"Source textarea is not found for post: {post.id}")
            post._source = source_elem.get_text()

        return posts

    def get_post_sources(self) -> "ForumPostCollection":
        """
        Get source code for all posts in the collection

        Batch retrieves source code (Wikidot syntax) for posts and sets the source property for each post.

        Returns
        -------
        ForumPostCollection
            Self (for method chaining)
        """
        ForumPostCollection._acquire_post_sources(self.thread, self)
        return self


@dataclass
class ForumPost:
    """
    Class representing a Wikidot forum post

    Holds information about individual posts (messages) within a forum thread.
    Provides information such as post title, body, author, and creation date.

    Attributes
    ----------
    thread : ForumThread
        The thread the post belongs to
    id : int
        Post ID
    title : str
        Post title
    text : str
        Post body (HTML text)
    element : Tag
        HTML element of the post (for parsing)
    created_by : AbstractUser
        Post creator
    created_at : datetime
        Post creation date and time
    edited_by : AbstractUser | None, default None
        Post editor (None if not edited)
    edited_at : datetime | None, default None
        Post edit date and time (None if not edited)
    _parent_id : int | None, default None
        Parent post ID (ID of the post being replied to)
    _source : str | None, default None
        Post source (Wikidot syntax)
    """

    thread: "ForumThread"
    id: int
    title: str
    text: str
    element: Tag
    created_by: "AbstractUser"
    created_at: datetime
    edited_by: Optional["AbstractUser"] = None
    edited_at: datetime | None = None
    _parent_id: int | None = None
    _source: str | None = None
    _revisions: Optional["ForumPostRevisionCollection"] = None

    def __str__(self) -> str:
        """
        String representation of the object

        Returns
        -------
        str
            String representation of the post
        """
        return (
            f"ForumPost(thread={self.thread}, id={self.id}, title={self.title}, "
            f"text={self.text}, created_by={self.created_by}, created_at={self.created_at}, "
            f"edited_by={self.edited_by}, edited_at={self.edited_at})"
        )

    @property
    def parent_id(self) -> int | None:
        """
        Retrieve the parent post ID

        Returns
        -------
        int | None
            Parent post ID, or None if no parent
        """
        return self._parent_id

    @property
    def has_revisions(self) -> bool:
        """
        Check if the post has been edited (has revisions)

        Returns
        -------
        bool
            True if the post has been edited, False otherwise
        """
        return self.edited_by is not None

    @property
    def revisions(self) -> "ForumPostRevisionCollection":
        """
        Retrieve all revisions for this post

        Automatically retrieves if revisions have not been fetched.

        Returns
        -------
        ForumPostRevisionCollection
            Collection of all revisions for this post
        """
        if self._revisions is None:
            from .forum_post_revision import ForumPostRevisionCollection

            result = ForumPostRevisionCollection.acquire_all_for_posts([self])
            self._revisions = result.get(self.id, ForumPostRevisionCollection(post=self, revisions=[]))
        return self._revisions

    @property
    def source(self) -> str:
        """
        Retrieve the post source (Wikidot syntax)

        Automatically retrieves if source has not been fetched.

        Returns
        -------
        str
            Post source (Wikidot syntax)

        Raises
        ------
        NoElementException
            If source element is not found
        """
        if self._source is None:
            ForumPostCollection(self.thread, [self]).get_post_sources()

        if self._source is None:
            raise NoElementException("Source textarea is not found.")

        # self._source is guaranteed to be str here (either from cache or just fetched)
        assert self._source is not None
        return self._source

    def edit(self, source: str, title: str | None = None) -> "ForumPost":
        """
        Edit the post

        Updates the post content. Maintains the current title if not specified。

        Parameters
        ----------
        source : str
            New source (Wikidot syntax)
        title : str | None, default None
            New title (maintains current title if None)

        Returns
        -------
        ForumPost
            Self (for method chaining)

        Raises
        ------
        LoginRequiredException
            If not logged in
        WikidotStatusCodeException
            If editing fails
        NoElementException
            If revision ID element is not found
        """
        self.thread.site.client.login_check()

        # 現在のリビジョンIDを取得
        form_response = self.thread.site.amc_request(
            [
                {
                    "moduleName": "forum/sub/ForumEditPostFormModule",
                    "threadId": self.thread.id,
                    "postId": self.id,
                }
            ]
        )[0]

        html = BeautifulSoup(form_response.json()["body"], "lxml")
        revision_elem = html.select_one("input[name='currentRevisionId']")
        if revision_elem is None:
            raise NoElementException("Current revision ID input is not found.")
        current_revision_id = int(str(revision_elem["value"]))

        # 編集を保存
        self.thread.site.amc_request(
            [
                {
                    "action": "ForumAction",
                    "event": "saveEditPost",
                    "moduleName": "Empty",
                    "postId": self.id,
                    "currentRevisionId": current_revision_id,
                    "title": title if title is not None else self.title,
                    "source": source,
                }
            ]
        )

        # ローカル状態を更新
        if title is not None:
            self.title = title
        self._source = source

        return self
