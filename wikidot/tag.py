# -*- coding: utf-8 -*-

"""wikidot.tag

Set tags to specific page on wikidot.

version:
    1.0.0
copyright:
    (c) 2020 ukwhatn
license:
    MIT License
    legal: http://expunged.xyz/assets/docs/MIT.txt

"""

from . import base, exceptions, decorator

from typing import Union, Optional


@decorator.execute
async def set_with_pageid(*, url: str, pageid: int, tags: Union[list, tuple]) -> bool:
    return await base.tag_set(url=url, pageid=pageid, tags=tags)


@decorator.execute
async def set_with_fullname(*, url: str, fullname: int, tags: Union[list, tuple]) -> bool:
    pageid = await base.page_getid(url=url, fullname=fullname)

    if pageid is None:
        raise exceptions.TargetPageIsNotFoundError("Target page is not found.")

    return await base.tag_set(url=url, pageid=pageid, tags=tags)


@decorator.execute
async def replace(*, limit: int = 10, url: str, before: str, after: str, selector: Optional[dict] = None):
    return await base.tag_replace(limit=limit, url=url, before=before, after=after, selector=selector)


@decorator.execute
async def reset(*, limit: int = 10, url: str, tagset: Union[list, tuple], selector: dict):
    return await base.tag_reset(limit=limit, url=url, tagset=tagset, selector=selector)
