# -*- coding: utf-8 -*-

""""wikidot.site

Site functions for wikidot.py

version:
    1.0.0
copyright:
    (c) 2020 ukwhatn
license:
    MIT License
    legal: http://expunged.xyz/assets/docs/MIT.txt

"""

from . import base, decorator
from typing import Optional


@decorator.execute
async def getmembers(*, limit: int = 10, url: str):
    return await base.site_getmembers_mass(limit=limit, url=url)


@decorator.execute
async def gethistory(*, url: str, limitpage: Optional[int] = None):
    return await base.site_gethistory(url=url, limitpage=limitpage)
