"""
Utility module for parsing various elements of Wikidot sites

This package contains utility functions for parsing HTML and specific format elements
retrieved from Wikidot sites.
"""

from .odate import odate_parse as odate
from .user import user_parse as user

__all__ = ["odate", "user"]
