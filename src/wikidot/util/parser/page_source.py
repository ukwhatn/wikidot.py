from bs4 import BeautifulSoup

_PRIVATE_USE_START = 0xE000
_PRIVATE_USE_END = 0xF8FF


def _unused_char(text: str) -> str:
    for code in range(_PRIVATE_USE_START, _PRIVATE_USE_END + 1):
        char = chr(code)
        if char not in text:
            return char
    raise ValueError("No unused private-use character available")


def page_source_parse(body: str) -> str | None:
    """Extract the source text from a Wikidot source module response

    Converts ``&nbsp;`` entities to ASCII spaces while keeping literal
    U+00A0 characters in the source as they are.

    Parameters
    ----------
    body: str
        HTML body of viewsource/ViewSourceModule or history/PageSourceModule

    Returns
    -------
    str | None
        Text of the ``div.page-source`` element, or None if the element is not found
    """
    # &nbsp; を解析前に空白へ置換すると、BeautifulSoup がタグ間の空白のみの文字列
    # （例: "</a>&nbsp;&nbsp;<br />"）を1文字に畳むため、解析後に戻す
    placeholder = _unused_char(body)
    html = BeautifulSoup(body.replace("&nbsp;", placeholder), "lxml")
    element = html.select_one("div.page-source")
    if element is None:
        return None
    return element.get_text().replace(placeholder, " ")
