import bs4
from wikidot.type import user


def user_parse(print_user_element: bs4.Tag) -> user.AbstractUser:
    """ Parses a print user element and returns a tuple of the user's name, unix, and id

    Parameters
    ----------
    print_user_element: bs4.Tag
        The print user element to parse

    Returns
    -------
    user.AbstractUser
        The user object parsed from the print user element
    """

    if "class" in print_user_element.attrs and "deleted" in print_user_element["class"]:
        return user.DeletedUser(
            id=int(print_user_element["data-id"])
        )

    elif "class" in print_user_element.attrs and "anonymous" in print_user_element["class"]:
        ip = print_user_element.find("span", class_="ip").get_text().replace("(", "").replace(")", "").strip()
        return user.AnonymousUser(
            ip=ip
        )

    elif len(print_user_element.find_all("a", recursive=False)) == 1:
        return user.GuestUser(
            name=print_user_element.get_text().strip()
        )

    elif print_user_element.get_text() == "Wikidot":
        return user.WikidotUser()

    else:
        _user = print_user_element.find_all("a")[1]
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
