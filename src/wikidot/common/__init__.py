"""
Common functionality module for the Wikidot library

This package provides common functionality used throughout the library.
It includes generic features such as exception classes, decorators, and logging functionality.
"""

from .logger import logger as wd_logger

__all__ = ["wd_logger"]
