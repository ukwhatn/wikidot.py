from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from bs4 import BeautifulSoup

from wikidot.common import exceptions

if TYPE_CHECKING:
    from wikidot.module.forum import Forum
    from wikidot.module.forum_thread import ForumThread
    from wikidot.module.site import Site
    from wikidot.module.user import AbstractUser


class ForumPostCollection(list["ForumPost"]):
    def __init__(self, thread: "ForumThread", posts: list["ForumPost"]):
        super().__init__(posts)
        self.thread = thread

    def __iter__(self) -> Iterator["ForumPost"]:
        return super().__iter__()

    def find(self, target_id: int) -> Optional["ForumPost"]:
        for post in self:
            if target_id == post.id:
                return post

    @staticmethod
    def _acquire_parent_post(thread: "ForumThread", posts: list["ForumPost"]):
        if len(posts) == 0:
            return posts

        for post in posts:
            post._parent = thread.get(post.parent_id)

        return posts

    def get_parent_post(self):
        return ForumPostCollection._acquire_parent_post(self.thread, self)

    @staticmethod
    def _acquire_post_info(thread: "ForumThread", posts: list["ForumPost"]):
        if len(posts) == 0:
            return posts

        responses = thread.site.amc_request(
            [
                {
                    "postId": post.id,
                    "threadId": thread.id,
                    "moduleName": "forum/sub/ForumEditPostFormModule",
                }
                for post in posts
            ]
        )

        for post, response in zip(posts, responses):
            html = BeautifulSoup(response.json()["body"], "lxml")

            title = html.select_one("input#np-title").text.strip()
            source = html.select_one("textarea#np-text").text.strip()
            post._title = title
            post._source = source

        return posts

    def get_post_info(self):
        return ForumPostCollection._acquire_post_info(self.thread, self)


@dataclass
class ForumPost:
    site: "Site"
    id: int
    forum: "Forum"
    thread: "ForumThread" = None
    parent_id: int = None
    created_by: "AbstractUser" = None
    created_at: datetime = None
    edited_by: "AbstractUser" = None
    edited_at: datetime = None
    source_text: str = None
    source_ele: BeautifulSoup = None
    _parent: "ForumPost" = None
    _title: str = None
    _source: str = None

    def reply(self, title: str = "", source: str = ""):
        client = self.site.client
        client.login_check()
        if source == "":
            raise exceptions.UnexpectedException("Post body can not be left empty.")

        response = self.site.amc_request(
            [
                {
                    "parentId": self.id,
                    "title": title,
                    "source": source,
                    "action": "ForumAction",
                    "event": "savePost",
                }
            ]
        )[0]
        body = response.json()

        return ForumPost(
            site=self.site,
            id=int(body["postId"]),
            forum=self.forum,
            title=title,
            source=source,
            thread=self.thread,
            parent_id=self.id,
            created_by=client.user.get(client.username),
            created_at=body["CURRENT_TIMESTAMP"],
        )

    def get_url(self):
        return f"{self.thread.get_url()}#post-{self.id}"

    @property
    def parent(self):
        if self._parent is None:
            ForumPostCollection(self.thread, [self]).get_parent_post()
        return self._parent

    @parent.setter
    def parent(self, value: "ForumPost"):
        self._parent = value

    @property
    def title(self):
        if self._title is None:
            ForumPostCollection(self.thread, [self]).get_post_info()
        return self._title

    @title.setter
    def title(self, value: str):
        self._title = value

    @property
    def source(self):
        if self._source is None:
            ForumPostCollection(self.thread, [self]).get_post_info()
        return self._source

    @source.setter
    def source(self, value: str):
        self._source = value

    def edit(self, title: str = None, source: str = None):
        client = self.site.client
        client.login_check()

        if title is None and source is None:
            return self

        if source == "":
            raise exceptions.UnexpectedException("Post source can not be left empty.")
        try:
            response = self.site.amc_request(
                [
                    {
                        "postId": self.id,
                        "threadId": self.thread.id,
                        "moduleName": "forum/sub/ForumEditPostFormModule",
                    }
                ]
            )[0]
            html = BeautifulSoup(response.json()["body"], "lxml")
            current_id = int(html.select("form#edit-post-form>input")[1].get("value"))

            response = self.site.amc_request(
                [
                    {
                        "postId": self.id,
                        "currentRevisionId": current_id,
                        "title": title if title is not None else self.title,
                        "source": source if source is not None else self.source,
                        "action": "ForumAction",
                        "event": "saveEditPost",
                        "moduleName": "Empty",
                    }
                ]
            )[0]
        except exceptions.WikidotStatusCodeException:
            return self

        body = response.json()
        self.edited_by = client.user.get(client.username)
        self.edited_at = datetime.fromtimestamp(body["CURRENT_TIMESTAMP"])
        self.title = title if title is not None else self.title
        self.source = source if source is not None else self.source

        return self

    def destroy(self):
        self.site.client.login_check()
        self.site.amc_request(
            [
                {
                    "postId": self.id,
                    "action": "ForumAction",
                    "event": "deletePost",
                    "moduleName": "Empty",
                }
            ]
        )
