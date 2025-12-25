"""
Module for handling Wikidot forum categories

This module provides classes and functionality related to Wikidot forum categories.
It enables operations such as retrieving category information and thread lists.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from bs4 import BeautifulSoup

from ..common.exceptions import NoElementException
from .forum_thread import ForumThread, ForumThreadCollection

if TYPE_CHECKING:
    from .site import Site


class ForumCategoryCollection(list["ForumCategory"]):
    """
    Class representing a collection of forum categories

    A list extension class for storing multiple forum categories and performing batch operations.
    """

    site: "Site"

    def __init__(
        self,
        site: Optional["Site"] = None,
        categories: list["ForumCategory"] | None = None,
    ):
        """
        Initialization method

        Parameters
        ----------
        site : Site | None, default None
            The site the categories belong to。If None, inferred from the first category
        categories : list[ForumCategory] | None, default None
            List of categories to store
        """
        super().__init__(categories or [])

        if site is not None:
            self.site = site
        else:
            self.site = self[0].site

    def __iter__(self) -> Iterator["ForumCategory"]:
        """
        Iterator that returns categories in the collection sequentially

        Returns
        -------
        Iterator[ForumCategory]
            Iterator of category objects
        """
        return super().__iter__()

    def find(self, id: int) -> Optional["ForumCategory"]:
        """
        Search for a category by category ID

        Returns the category object if a category with the specified ID exists。

        Parameters
        ----------
        id : int
            Category ID to search for

        Returns
        -------
        ForumCategory | None
            Category object if found, None otherwise
        """
        for category in self:
            if category.id == id:
                return category
        return None

    @staticmethod
    def acquire_all(site: "Site") -> "ForumCategoryCollection":
        """
        Retrieve all forum categories of a site

        Accesses the forum page of the specified site and retrieves
        information about all available categories。

        Parameters
        ----------
        site : Site
            The site to retrieve categories from

        Returns
        -------
        ForumCategoryCollection
            Collection of retrieved forum categories

        Raises
        ------
        NoElementException
            If required HTML elements are not found
        """
        categories = []

        response = site.amc_request([{"moduleName": "forum/ForumStartModule", "hidden": "true"}])[0]

        body = response.json()["body"]
        html = BeautifulSoup(body, "lxml")

        for row in html.select("table tr.head~tr"):
            name_elem = row.select_one("td.name")
            if name_elem is None:
                raise NoElementException("Name element is not found.")
            name_link_elem = name_elem.select_one("a")
            if name_link_elem is None:
                raise NoElementException("Name link element is not found.")
            name_link_href = name_link_elem.get("href")
            if name_link_href is None:
                raise NoElementException("Name link href is not found.")
            thread_count_elem = row.select_one("td.threads")
            if thread_count_elem is None:
                raise NoElementException("Thread count element is not found.")
            post_count_elem = row.select_one("td.posts")
            if post_count_elem is None:
                raise NoElementException("Post count element is not found.")
            category_id_match = re.search(r"c-(\d+)", str(name_link_href))
            if category_id_match is None:
                raise NoElementException("Category ID is not found.")
            category_id_str = category_id_match.group(1)
            title_elem = name_elem.select_one("a")
            if title_elem is None:
                raise NoElementException("Title element is not found.")
            description_elem = name_elem.select_one("div.description")
            if description_elem is None:
                raise NoElementException("Description element is not found.")

            category = ForumCategory(
                site=site,
                id=int(category_id_str),
                title=title_elem.text,
                description=description_elem.text,
                threads_count=int(thread_count_elem.text),
                posts_count=int(post_count_elem.text),
            )

            categories.append(category)

        return ForumCategoryCollection(site=site, categories=categories)


@dataclass
class ForumCategory:
    """
    Class representing a Wikidot forum category

    Provides basic forum category information and access to thread lists。

    Attributes
    ----------
    site : Site
        The site the categories belong to
    id : int
        Category ID
    title : str
        Category title
    description : str
        Category description
    threads_count : int
        Number of threads in the category
    posts_count : int
        Number of posts in the category
    _threads : ForumThreadCollection | None
        Thread collection in the category (for internal caching)
    """

    site: "Site"
    id: int
    title: str
    description: str
    threads_count: int
    posts_count: int
    _threads: ForumThreadCollection | None = None

    def __str__(self) -> str:
        """
        String representation of the object

        Returns
        -------
        str
            String representation of the category
        """
        return (
            f"ForumCategory(id={self.id}, "
            f"title={self.title}, description={self.description}, "
            f"threads_count={self.threads_count}, posts_count={self.posts_count})"
        )

    @property
    def threads(self) -> ForumThreadCollection:
        """
        Retrieve the list of threads in the category

        Automatically retrieves if the thread list has not been fetched。

        Returns
        -------
        ForumThreadCollection
            Thread collection in the category
        """
        if self._threads is None:
            self._threads = ForumThreadCollection.acquire_all_in_category(self)
        return self._threads

    @threads.setter
    def threads(self, value: ForumThreadCollection) -> None:
        """
        Set the list of threads in the category

        Parameters
        ----------
        value : ForumThreadCollection
            Thread collection to set
        """
        self._threads = value

    def reload_threads(self) -> ForumThreadCollection:
        """
        Re-retrieve the list of threads in the category

        Retrieves the latest thread list ignoring the cache。

        Returns
        -------
        ForumThreadCollection
            Latest thread collection
        """
        self._threads = ForumThreadCollection.acquire_all_in_category(self)
        return self._threads

    def create_thread(self, title: str, description: str, source: str) -> ForumThread:
        """
        Create a new thread in the category

        Parameters
        ----------
        title : str
            Thread title
        description : str
            Thread description
        source : str
            Thread body (Wikidot syntax)

        Returns
        -------
        ForumThread
            Created thread object
        """
        self.site.client.login_check()

        # 作成リクエスト
        response = self.site.amc_request(
            [
                {
                    "moduleName": "Empty",
                    "action": "ForumAction",
                    "event": "newThread",
                    "category_id": self.id,
                    "title": title,
                    "description": description,
                    "source": source,
                }
            ]
        )[0].json()

        # responseからthreadIdを取得
        if "threadId" not in response and isinstance(response["threadId"], int):
            raise NoElementException("Thread ID is not found.")

        thread_id: int = response["threadId"]

        return ForumThread.get_from_id(self.site, thread_id, self)
