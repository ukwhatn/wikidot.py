from typing import TYPE_CHECKING

import bs4

from wikidot.module import user

if TYPE_CHECKING:
    from wikidot.module.client import Client


def user_parse(client: "Client", elem: bs4.Tag) -> user.AbstractUser:
    """printuser要素をパースし、ユーザーオブジェクトを返す

    Parameters
    ----------
    elem: bs4.Tag
        パース対象の要素（printuserクラスがついた要素）
    client: Client
        クライアント

    Returns
    -------
    user.AbstractUser
        パースされて得られたユーザーオブジェクト
        User | DeletedUser | AnonymousUser | GuestUser | WikidotUser のいずれか
    """

    if "class" in elem.attrs and "deleted" in elem["class"]:
        return user.DeletedUser(client=client, id=int(elem["data-id"]))

    elif "class" in elem.attrs and "anonymous" in elem["class"]:
        ip = (
            elem.find("span", class_="ip")
            .get_text()
            .replace("(", "")
            .replace(")", "")
            .strip()
        )
        return user.AnonymousUser(client=client, ip=ip)

    # TODO: [[user ukwhatn]]構文をパースできなくなる（aが1つしかない）ので、一度無効化 -> GuestUserの例を探して実装を戻す
    # elif len(elem.find_all("a", recursive=False)) == 1:
    #     return user.GuestUser(
    #         name=elem.get_text().strip()
    #     )

    elif elem.get_text() == "Wikidot":
        return user.WikidotUser(client=client)

    else:
        _user = elem.find_all("a")[-1]
        user_name = _user.get_text()
        user_unix = str(_user["href"]).replace("http://www.wikidot.com/user:info/", "")
        user_id = int(
            str(_user["onclick"])
            .replace("WIKIDOT.page.listeners.userInfo(", "")
            .replace("); return false;", "")
        )

        return user.User(
            client=client,
            id=user_id,
            name=user_name,
            unix_name=user_unix,
            avatar_url=f"http://www.wikidot.com/avatar.php?userid={user_id}",
        )
