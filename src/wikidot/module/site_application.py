from dataclasses import dataclass
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

from wikidot.common import exceptions
from wikidot.common.decorators import login_required
from wikidot.util.parser import user as user_parser

if TYPE_CHECKING:
    from wikidot.module.site import Site
    from wikidot.module.user import AbstractUser


@dataclass
class SiteApplication:
    site: "Site"
    user: "AbstractUser"
    text: str

    def __str__(self):
        return f"SiteApplication(user={self.user}, site={self.site}, text={self.text})"

    @staticmethod
    @login_required
    def acquire_all(site: "Site") -> list["SiteApplication"]:
        """サイトへの未処理の申請を取得する

        Parameters
        ----------
        site: Site
            サイト

        Returns
        -------
        list[SiteApplication]
            申請のリスト
        """
        response = site.amc_request(
            [{"moduleName": "managesite/ManageSiteMembersApplicationsModule"}]
        )[0]

        body = response.json()["body"]

        if "WIKIDOT.page.listeners.loginClick(event)" in body:
            raise exceptions.ForbiddenException(
                "You are not allowed to access this page"
            )

        html = BeautifulSoup(response.json()["body"], "lxml")

        applications = []

        user_elements = html.select("h3 span.printuser")
        text_wrapper_elements = html.select("table")

        if len(user_elements) != len(text_wrapper_elements):
            raise exceptions.UnexpectedException(
                "Length of user_elements and text_wrapper_elements are different"
            )

        for i in range(len(user_elements)):
            user_element = user_elements[i]
            text_wrapper_element = text_wrapper_elements[i]

            user = user_parser(site.client, user_element)
            text = text_wrapper_element.select("td")[1].text.strip()

            applications.append(SiteApplication(site, user, text))

        return applications

    @login_required
    def _process(self, action: str):
        """申請を処理する

        Parameters
        ----------
        action: str
            処理の種類
        """
        if action not in ["accept", "decline"]:
            raise ValueError(f"Invalid action: {action}")

        try:
            self.site.amc_request(
                [
                    {
                        "action": "ManageSiteMembershipAction",
                        "event": "acceptApplication",
                        "user_id": self.user.id,
                        "text": f"your application has been {action}ed",
                        "type": action,
                        "moduleName": "Empty",
                    }
                ]
            )
        except exceptions.WikidotStatusCodeException as e:
            if e.status_code == "no_application":
                raise exceptions.NotFoundException(
                    f"Application not found: {self.user}"
                ) from e
            else:
                raise e

    def accept(self):
        """申請を承認する"""
        self._process("accept")

    def decline(self):
        """申請を拒否する"""
        self._process("decline")
