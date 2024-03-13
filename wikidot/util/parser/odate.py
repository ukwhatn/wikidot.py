from datetime import datetime

import bs4


def odate_parse(odate_element: bs4.Tag) -> datetime:
    """odate要素を解析し、datetimeオブジェクトを返す

    Parameters
    ----------
    odate_element: bs4.Tag
        odate要素

    Returns
    -------
    datetime
        odate要素が表す日時

    Raises
    ------
    ValueError
        odate要素が有効なunix timeを含んでいない場合

    """
    _odate_classes = odate_element["class"]
    for _odate_class in _odate_classes:
        if "time_" in str(_odate_class):
            unix_time = int(str(_odate_class).replace("time_", ""))
            return datetime.fromtimestamp(unix_time)

    raise ValueError("odate element does not contain a valid unix time")
