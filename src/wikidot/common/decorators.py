"""
Module providing various decorators

This module provides common decorators used within the library.
Currently, authentication-related decorators are implemented.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


def login_required(func: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator to apply to methods or functions that require login

    Methods or functions with this decorator automatically check login status before execution.
    If not logged in, LoginRequiredException is raised.

    The client instance is searched in the following priority order:
    1. Argument named "client"
    2. Argument that is an instance of Client class
    3. self.client (attribute of the calling object)
    4. Client class held by an attribute of self (e.g., self.site.client)

    Parameters
    ----------
    func : callable
        Function or method to decorate

    Returns
    -------
    callable
        Wrapped function or method

    Raises
    ------
    ValueError
        If client instance is not found
    LoginRequiredException
        If not logged in (determined by client.login_check())
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        # Import inside function to avoid circular references
        from wikidot.module.client import Client

        client: Client | None = None
        if "client" in kwargs:
            kwarg_client = kwargs["client"]
            if isinstance(kwarg_client, Client):
                client = kwarg_client

        if client is None:
            for arg in args:
                if isinstance(arg, Client):
                    client = arg
                    break

        # Check if it exists in self
        if client is None and args:
            self_obj: Any = args[0]
            if hasattr(self_obj, "client"):
                maybe_client = getattr(self_obj, "client")
                if isinstance(maybe_client, Client):
                    client = maybe_client
            else:
                # Search for client in attributes held by self
                for attr_name in dir(self_obj):
                    if attr_name.startswith("_"):
                        continue
                    attr = getattr(self_obj, attr_name)
                    if hasattr(attr, "client"):
                        maybe_client = getattr(attr, "client")
                        if isinstance(maybe_client, Client):
                            client = maybe_client
                            break

        if client is None:
            raise ValueError("Client is not found")

        client.login_check()

        return func(*args, **kwargs)

    return wrapper
