# -*- coding: utf-8 -*-

""""wikidot.file

FIle functions for wikidot.py

version:
    1.0.0
copyright:
    (c) 2020 ukwhatn
license:
    MIT License
    legal: http://expunged.xyz/assets/docs/MIT.txt

"""

from . import base, decorator


@decorator.execute
async def getlist(*, limit: int = 10, url: str, targets: list[int]):
    return await base.file_getlist_mass(limit=limit, url=url, targets=targets)
