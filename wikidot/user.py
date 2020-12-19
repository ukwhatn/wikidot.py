# -*- coding: utf-8 -*-

"""wikidot.user

Manage sessions on wikidot for wikidot.py

version:
    1.0.0
copyright:
    (c) 2020 ukwhatn
license:
    MIT License
    legal: http://expunged.xyz/assets/docs/MIT.txt

"""

from . import base, decorator, variables


@decorator.execute
async def login(*, user, password) -> bool:
    return await base.user_login(user=user, password=password)


@decorator.execute
async def logout() -> bool:
    return await base.user_logout()


def status() -> bool:
    """Return login status

    Usage
    -----
    >>> wikidot.user.status()

    Returns
    -------
    bool : if you logged-in to wikidot(T/F)

    """
    return variables.logged_in
