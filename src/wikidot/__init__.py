"""
A Python library for interacting with Wikidot sites

This package abstracts Wikidot site API operations and provides an intuitive interface.
It contains various classes for accessing major Wikidot elements such as users, sites, and pages.
"""

import importlib
import inspect
import os
import sys

from .module.client import Client

__all__ = ["Client"]
__version__ = "4.3.1"


def _import_submodules() -> None:
    """
    Import classes from all submodules in the package and expose them at the top level

    Scans Python files within each subdirectory and imports contained classes
    into the top-level namespace. This allows access to classes in the format
    `wikidot.ClassName`.

    Notes
    -----
    Filenames starting with '_' are ignored.
    Import failures are silently ignored.
    """
    current_module = sys.modules[__name__]
    package_dir = os.path.dirname(__file__)

    for base_dir in ["common", "connector", "module", "util"]:
        base_path = os.path.join(package_dir, base_dir)
        if not os.path.isdir(base_path):
            continue

        for filename in os.listdir(base_path):
            if filename.startswith("_") or not filename.endswith(".py"):
                continue

            module_name = filename[:-3]
            full_module_name = f"{__name__}.{base_dir}.{module_name}"

            try:
                module = importlib.import_module(full_module_name)
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if obj.__module__ == full_module_name:
                        setattr(current_module, name, obj)
            except ImportError:
                pass


_import_submodules()
