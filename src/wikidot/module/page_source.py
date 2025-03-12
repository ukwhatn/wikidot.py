from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .page import Page


@dataclass
class PageSource:
    page: "Page"
    wiki_text: str
