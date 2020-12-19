# -*- coding: utf-8 -*-

"""wikidot.page

Do actions on wikidot page

version:
    1.0.0
copyright:
    (c) 2020 ukwhatn
license:
    MIT License
    legal: http://expunged.xyz/assets/docs/MIT.txt

"""

from . import base, decorator
from typing import Union, Optional

# --------------------
# ListPages
# --------------------


@decorator.execute
async def getdata(*, limit: int = 10, url: str, main_key: str = "fullname", module_body: Optional[list[str]] = None, **kwargs):
    return await base.page_getdata_mass(limit=limit, url=url, main_key=main_key, module_body=module_body, **kwargs)


# --------------------
# Page ID
# --------------------


@decorator.execute
async def getid(*, limit: int = 10, url: str, targets: Union[list, tuple]) -> list:
    return await base.page_getid_mass(limit=limit, url=url, targets=targets)


# --------------------
# Page Source
# --------------------


@decorator.execute
async def getsource(*, url: str, targets: Union[list[int], tuple[int]]) -> list:
    return await base.page_getsource_mass(url=url, targets=targets)


# --------------------
# Page History
# --------------------


@decorator.execute
async def gethistory(*, limit: int = 10, url: str, targets: list[int]):
    return await base.page_gethistory_mass(limit=limit, url=url, targets=targets)


# --------------------
# Edit
# --------------------


@decorator.execute
async def edit(*, url: str, fullname: str, pageid: Optional[int] = None, title: str = "", content: str = "", comment: str = "", forceedit: bool = False) -> bool:
    return await base.page_edit(url=url, fullname=fullname, pageid=pageid, title=title, content=content, comment=comment, forceedit=forceedit)


# --------------------
# RenamePage
# --------------------


async def rename(*, limit: int = 10, url: str, targets: list):
    return await base.page_rename_mass(limit=limit, url=url, targets=targets)


# --------------------
# ParentPage
# --------------------


@decorator.execute
async def setparent(*, url: str, targets: Union[list[int], tuple[int]], parentpage: str):
    return await base.page_setparent_mass(url=url, targets=targets, parentpage=parentpage)

