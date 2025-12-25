"""
Module for handling Wikidot site members

This module provides classes and functionality related to Wikidot site members.
It enables operations such as retrieving member information and changing permissions.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

from ..common.exceptions import (
    TargetErrorException,
    WikidotStatusCodeException,
)
from ..util.parser import odate as odate_parser
from ..util.parser import user as user_parser

if TYPE_CHECKING:
    from .site import Site
    from .user import AbstractUser


@dataclass
class SiteMember:
    """
    Class representing a member of a Wikidot site

    Holds site member information and provides functionality for operations such as permission changes.

    Attributes
    ----------
    site : Site
        The site the member belongs to
    user : AbstractUser
        The member user
    joined_at : datetime | None
        Date and time the member joined the site (None if unavailable)
    """

    site: "Site"
    user: "AbstractUser"
    joined_at: datetime | None

    @staticmethod
    def _parse(site: "Site", html: BeautifulSoup) -> list["SiteMember"]:
        """
        Internal method to extract member information from member list page HTML

        Parameters
        ----------
        site : Site
            The site the members belong to
        html : BeautifulSoup
            HTML to parse

        Returns
        -------
        list[SiteMember]
            List of extracted members
        """
        members: list[SiteMember] = []

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
        """
        Retrieve the member list of a site

        Retrieves a list of members of the specified group (admins, moderators, etc.).

        Parameters
        ----------
        site : Site
            The site to retrieve members from
        group : str | None, default None
            Group of members to retrieve ("admins", "moderators", or "" for all members)

        Returns
        -------
        list[SiteMember]
            List of members

        Raises
        ------
        ValueError
            If an invalid group is specified
        """
        if group is None:
            group = ""

        if group not in ["admins", "moderators", ""]:
            raise ValueError("Invalid group")

        members: list[SiteMember] = []

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

    def _change_group(self, event: str) -> None:
        """
        Internal method to change a member's group (permissions)

        Common method for promoting to or demoting from moderator or admin.

        Parameters
        ----------
        event : str
            Change event ("toModerators", "removeModerator", "toAdmins", "removeAdmin")

        Raises
        ------
        ValueError
            If an invalid event is specified
        ForbiddenException
            If insufficient permissions
        TargetErrorException
            If the user already has or doesn't have the specified permission
        WikidotStatusCodeException
            If other errors occur
        """
        if event not in [
            "toModerators",
            "removeModerator",
            "toAdmins",
            "removeAdmin",
        ]:
            raise ValueError("Invalid event")

        try:
            self.site.amc_request(
                [
                    {
                        "action": "ManageSiteMembershipAction",
                        "event": event,
                        "user_id": self.user.id,
                        "moduleName": "",
                    }
                ]
            )
        except WikidotStatusCodeException as e:
            if e.status_code == "not_already":
                raise TargetErrorException(f"User is not moderator/admin: {self.user.name}") from e

            if e.status_code in ("already_admin", "already_moderator"):
                raise TargetErrorException(
                    f"User is already {e.status_code.removeprefix('already_')}: {self.user.name}"
                ) from e

            raise e

    def to_moderator(self) -> None:
        """
        Promote a member to moderator

        Raises
        ------
        ForbiddenException
            If insufficient permissions
        TargetErrorException
            If the user is already a moderator
        WikidotStatusCodeException
            If other errors occur
        """
        self._change_group("toModerators")

    def remove_moderator(self) -> None:
        """
        Remove moderator permissions from a member

        Raises
        ------
        ForbiddenException
            If insufficient permissions
        TargetErrorException
            If the user is not a moderator
        WikidotStatusCodeException
            If other errors occur
        """
        self._change_group("removeModerator")

    def to_admin(self) -> None:
        """
        Promote a member to admin

        Raises
        ------
        ForbiddenException
            If insufficient permissions
        TargetErrorException
            If the user is already an admin
        WikidotStatusCodeException
            If other errors occur
        """
        self._change_group("toAdmins")

    def remove_admin(self) -> None:
        """
        Remove admin permissions from a member

        Raises
        ------
        ForbiddenException
            If insufficient permissions
        TargetErrorException
            If the user is not an admin
        WikidotStatusCodeException
            If other errors occur
        """
        self._change_group("removeAdmin")
