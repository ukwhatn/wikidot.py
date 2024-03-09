import bs4
from wikidot.type import user


def user_parse(elem: bs4.Tag) -> user.AbstractUser:
    """ printuser要素をパースし、ユーザーオブジェクトを返す

    Parameters
    ----------
    elem: bs4.Tag
        パース対象の要素（printuserクラスがついた要素）

    Returns
    -------
    user.AbstractUser
        パースされて得られたユーザーオブジェクト
        User | DeletedUser | AnonymousUser | GuestUser | WikidotUser のいずれか
    """

    if "class" in elem.attrs and "deleted" in elem["class"]:
        return user.DeletedUser(
            id=int(elem["data-id"])
        )

    elif "class" in elem.attrs and "anonymous" in elem["class"]:
        ip = elem.find("span", class_="ip").get_text().replace("(", "").replace(")", "").strip()
        return user.AnonymousUser(
            ip=ip
        )

    elif len(elem.find_all("a", recursive=False)) == 1:
        return user.GuestUser(
            name=elem.get_text().strip()
        )

    elif elem.get_text() == "Wikidot":
        return user.WikidotUser()

    else:
        _user = elem.find_all("a")[1]
        user_name = _user.get_text()
        user_unix = str(_user["href"]).replace("http://www.wikidot.com/user:info/", "")
        user_id = int(
            str(_user["onclick"]).replace("WIKIDOT.page.listeners.userInfo(", "").replace("); return false;", "")
        )

        return user.User(
            id=user_id,
            name=user_name,
            unix_name=user_unix,
            avatar_url=f"http://www.wikidot.com/avatar.php?userid={user_id}"
        )
