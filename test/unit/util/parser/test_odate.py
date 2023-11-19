import unittest
import bs4
from wikidot.util import parser
from wikidot.type import user
import random
from datetime import datetime


class OdateParseTestCase(unittest.TestCase):
    source = ("<span class=\"odate time_<<placeholder>> format_%25e%20%25b%20%25Y%2C%20%25H%3A%25M%7Cagohover\" "
              "style=\"cursor: help;\">19 Nov 2023, 20:45</span>")

    def test_random(self):
        for _ in range(10):
            random_num = random.randint(0, 9999999999)
            elem = bs4.BeautifulSoup(self.source.replace("<<placeholder>>", str(random_num)), "lxml").find("span",
                                                                                                           class_="odate")
            self.assertEqual(parser.odate(elem), datetime.fromtimestamp(random_num))


if __name__ == '__main__':
    unittest.main()
