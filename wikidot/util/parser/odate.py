import bs4
from datetime import datetime


def odate_parse(odate_element: bs4.Tag) -> datetime:
    """Parses an odate element and returns a datetime object

    Parameters
    ----------
    odate_element: bs4.Tag
        The odate element to parse

    Returns
    -------
    datetime
        The datetime object parsed from the odate element

    Raises
    ------
    ValueError
        If the odate element does not contain a valid unix time

    """
    _odate_classes = odate_element["class"]
    for _odate_class in _odate_classes:
        if "time_" in str(_odate_class):
            unix_time = int(str(_odate_class).replace("time_", ""))
            return datetime.fromtimestamp(unix_time)

    raise ValueError("odate element does not contain a valid unix time")
