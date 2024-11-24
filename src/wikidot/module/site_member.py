from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

from ..util.parser import odate as odate_parser
from ..util.parser import user as user_parser

if TYPE_CHECKING:
    from .site import Site
    from .user import AbstractUser


@dataclass
class SiteMember:
    site: "Site"
    user: "AbstractUser"
    joined_at: datetime | None

    @staticmethod
    def _parse(site: "Site", html: BeautifulSoup) -> list["SiteMember"]:
        members: list["SiteMember"] = []

        for row in html.select("table tr"):
            tds = row.select("td")
            user_elem = tds[0].select_one(".printuser")

            if user_elem is None:
                continue

            user = user_parser(site.client, user_elem)

            # tdsが2つあったら加入日時がある
            if len(tds) == 2:
                joined_at_elem = tds[1].select_one(".odate")
                if joined_at_elem is None:
                    joined_at = None
                else:
                    joined_at = odate_parser(joined_at_elem)
            else:
                joined_at = None

            members.append(SiteMember(site, user, joined_at))

        return members

    @staticmethod
    def get(site: "Site", group: str | None = None) -> list["SiteMember"]:
        if group is None:
            group = ""

        if group not in ["admins", "moderators", ""]:
            raise ValueError("Invalid group")

        members: list["SiteMember"] = []

        first_response = site.amc_request(
            [
                {
                    "moduleName": "membership/MembersListModule",
                    "page": 1,
                    "group": group,
                }
            ]
        )[0]

        first_body = first_response.json()["body"]
        first_html = BeautifulSoup(first_body, "lxml")

        members.extend(SiteMember._parse(site, first_html))

        pager = first_html.select_one("div.pager")
        if pager is None:
            return members

        last_page = int(pager.select("a")[-2].text)
        if last_page == 1:
            return members

        responses = site.amc_request(
            [
                {
                    "moduleName": "membership/MembersListModule",
                    "page": page,
                    "group": group,
                }
                for page in range(2, last_page + 1)
            ]
        )

        for response in responses:
            body = response.json()["body"]
            html = BeautifulSoup(body, "lxml")
            members.extend(SiteMember._parse(site, html))

        return members
