"""odateパーサーのユニットテスト"""

from collections.abc import Callable
from datetime import datetime

import pytest
from bs4 import BeautifulSoup

from wikidot.util.parser.odate import odate_parse


class TestOdateParse:
    """odate_parse関数のテスト"""

    def test_parse_valid_odate(self, odate_html_factory: Callable[[int], str]) -> None:
        """有効なodate要素をパースできる"""
        # 2023-12-17 12:00:00 UTC = 1702814400
        html = odate_html_factory(1702814400)
        soup = BeautifulSoup(html, "lxml")
        elem = soup.select_one("span.odate")
        assert elem is not None

        result = odate_parse(elem)

        assert isinstance(result, datetime)
        assert result == datetime.fromtimestamp(1702814400)

    def test_parse_odate_epoch(self, odate_html_factory: Callable[[int], str]) -> None:
        """Unix epoch (0) をパースできる"""
        html = odate_html_factory(0)
        soup = BeautifulSoup(html, "lxml")
        elem = soup.select_one("span.odate")
        assert elem is not None

        result = odate_parse(elem)

        assert result == datetime.fromtimestamp(0)

    def test_parse_odate_with_multiple_classes(self, odate_html_multiple_classes: str) -> None:
        """複数クラスを持つodate要素をパースできる"""
        soup = BeautifulSoup(odate_html_multiple_classes, "lxml")
        elem = soup.select_one("span.odate")
        assert elem is not None

        result = odate_parse(elem)

        assert isinstance(result, datetime)
        assert result == datetime.fromtimestamp(1702828800)

    def test_parse_odate_without_time_class_raises(self, odate_html_no_time: str) -> None:
        """time_クラスがない場合はValueErrorを発生させる"""
        soup = BeautifulSoup(odate_html_no_time, "lxml")
        elem = soup.select_one("span.odate")
        assert elem is not None

        with pytest.raises(ValueError) as exc_info:
            odate_parse(elem)

        assert "valid unix time" in str(exc_info.value)

    def test_parse_odate_recent_timestamp(self, odate_html_factory: Callable[[int], str]) -> None:
        """最近のタイムスタンプをパースできる"""
        # 2024-01-01 00:00:00 UTC = 1704067200
        html = odate_html_factory(1704067200)
        soup = BeautifulSoup(html, "lxml")
        elem = soup.select_one("span.odate")
        assert elem is not None

        result = odate_parse(elem)

        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1

    def test_parse_odate_old_timestamp(self, odate_html_factory: Callable[[int], str]) -> None:
        """古いタイムスタンプをパースできる"""
        # 2007-06-21 00:00:00 UTC (SCP wiki creation date)
        html = odate_html_factory(1182384000)
        soup = BeautifulSoup(html, "lxml")
        elem = soup.select_one("span.odate")
        assert elem is not None

        result = odate_parse(elem)

        assert result.year == 2007
        assert result.month == 6
