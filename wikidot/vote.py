# -*- coding: utf-8 -*-

""""wikidot.vote

Vote functions for wikidot.py

version:
    1.0.0
copyright:
    (c) 2020 ukwhatn
license:
    MIT License
    legal: http://expunged.xyz/assets/docs/MIT.txt

"""

from typing import List
from . import base, decorator


@decorator.execute
async def getvoter(*, limit: int = 10, url: str, targets: List[int]):
    return await base.vote_getvoter_mass(limit=limit, url=url, targets=targets)


@decorator.execute
async def postvote(*, url: str, pageid: int, vote: int):
    return await base.vote_postvote(url=url, pageid=pageid, vote=vote)


@decorator.execute
async def cancelvote(*, url: str, pageid: int):
    return await base.vote_cancelvote(url=url, pageid=pageid)
