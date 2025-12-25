"""
Module for handling Wikidot page source code

This module provides classes and functions related to Wikidot page source code (Wikidot markup).
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .page import Page


@dataclass
class PageSource:
    """
    Class representing a page's source code (Wikidot markup)

    Holds the source code (Wikidot markup) of a Wikidot page and provides basic operations.
    Represents the source code of a page's current or specific revision.

    Attributes
    ----------
    page : Page
        The page this source code belongs to
    wiki_text : str
        The page's source code (Wikidot markup)
    """

    page: "Page"
    wiki_text: str
