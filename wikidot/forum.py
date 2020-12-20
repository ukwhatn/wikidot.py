# -*- coding: utf-8 -*-

""""wikidot.forum

Forum functions for wikidot.py

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
async def getcategoies(*, url: str, includehidden: bool = True):
    return await base.forum_getcategories(url=url, includehidden=includehidden)


@decorator.execute
async def getthreadspercategory(*, limit: int = 10, url: str, categoryid: int):
    return await base.forum_getthreads_percategory(limit=limit, url=url, categoryid=categoryid)


@decorator.execute
async def getthreads(*, limit: int = 10, url: str, includehidden: bool = True):
    return await base.forum_getthreads_mass(limit=limit, url=url, includehidden=includehidden)


@decorator.execute
async def getposts(*, limit: int = 10, url: str, threadid: int):
    return await base.forum_getposts_perthread(limit=limit, url=url, threadid=threadid)


@decorator.execute
async def getparentpage(*, url: str, threadid: int, forumcategoryname: str = "forum"):
    return await base.forum_getparentpage(url=url, threadid=threadid, forumcategoryname=forumcategoryname)


@decorator.execute
async def getpagediscussion(*, url: str, pageid: int):
    return await base.forum_getpagediscussion(url=url, pageid=pageid)


@decorator.execute
async def post(*, url: str, threadid: int, parentid: Optional[int] = None, title: str = "", content: str):
    return await base.forum_post(url=url, threadid=threadid, parentid=parentid, title=title, content=content)


@decorator.execute
async def edit(*, url: str, threadid: int, postid: int, title: str = "", content: str):
    return await base.forum_edit(url=url, threadid=threadid, postid=postid, title=title, content=content)


@decorator.execute
async def rss(*, url: str, code: str):
    return await base.rss_get(url=url, code=code)
