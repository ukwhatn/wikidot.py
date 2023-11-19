import unittest
import bs4
from wikidot.util import parser
from wikidot.type import user


class UserParseTestCase(unittest.TestCase):
    normal_element = "<span class=\"printuser avatarhover\"><a href=\"http://www.wikidot.com/user:info/ukwhatn\" onclick=\"WIKIDOT.page.listeners.userInfo(3396310); return false;\"><img class=\"small\" src=\"http://www.wikidot.com/avatar.php?userid=3396310&amp;amp;size=small&amp;amp;timestamp=1700405183\" alt=\"ukwhatn\" style=\"background-image:url(http://www.wikidot.com/userkarma.php?u=3396310)\"></a><a href=\"http://www.wikidot.com/user:info/ukwhatn\" onclick=\"WIKIDOT.page.listeners.userInfo(3396310); return false;\">ukwhatn</a></span>"

    deleted_element = "<span class=\"printuser deleted\" data-id=\"3396310\"><img class=\"small\" src=\"http://www.wikidot.com/common--images/avatars/default/a16.png\" alt=\"\">(account deleted)</span>"

    anonymous_element = "<span class=\"printuser anonymous\"><a href=\"javascript:;\" onclick=\"WIKIDOT.page.listeners.anonymousUserInfo('111.222.333.444'); return false;\"><img class=\"small\" src=\"https://www.wikidot.com/common--images/avatars/default/a16.png\" alt=\"\"></a><a href=\"javascript:;\" onclick=\"WIKIDOT.page.listeners.anonymousUserInfo('111.222.333.444'); return false;\">Anonymous <span class=\"ip\">(111.222.333.444)</span></a></span>"

    guest_element = "<span class=\"printuser avatarhover\"><a href=\"javascript:;\"><img class=\"small\" src=\"http://www.gravatar.com/avatar.php?gravatar_id=23463b99b62a72f26ed677cc556c44e8&amp;default=http://www.wikidot.com/common--images/avatars/default/a16.png&amp;size=16\" alt=\"\"></a>ukwhatn (ゲスト)</span>"

    wikidot_element = "<span class=\"printuser\">Wikidot</span>"

    def test_normal_element(self):
        elem = bs4.BeautifulSoup(self.normal_element, "lxml").find("span", class_="printuser")
        self.assertEqual(parser.user(elem), user.User(
            id=3396310,
            name="ukwhatn",
            unix_name="ukwhatn",
            avatar_url="http://www.wikidot.com/avatar.php?userid=3396310"
        ))

    def test_deleted_element(self):
        elem = bs4.BeautifulSoup(self.deleted_element, "lxml").find("span", class_="printuser")
        self.assertEqual(parser.user(elem), user.DeletedUser(
            id=3396310
        ))

    def test_anonymous_element(self):
        elem = bs4.BeautifulSoup(self.anonymous_element, "lxml").find("span", class_="printuser")
        self.assertEqual(parser.user(elem), user.AnonymousUser(
            ip="111.222.333.444"
        ))

    def test_guest_element(self):
        elem = bs4.BeautifulSoup(self.guest_element, "lxml").find("span", class_="printuser")
        self.assertEqual(parser.user(elem), user.GuestUser(
            name="ukwhatn (ゲスト)"
        ))

    def test_wikidot_element(self):
        elem = bs4.BeautifulSoup(self.wikidot_element, "lxml").find("span", class_="printuser")
        self.assertEqual(parser.user(elem), user.WikidotUser())


if __name__ == '__main__':
    unittest.main()
