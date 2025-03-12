from typing import TYPE_CHECKING

import bs4

from ...module import user

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

    if ("class" in elem.attrs and "deleted" in elem["class"]) or (
        isinstance(elem, str) and elem.strip() == "(user deleted)"
    ):
        if isinstance(elem, str):
            return user.DeletedUser(client=client, id=0)
        else:
            return user.DeletedUser(client=client, id=int(str(elem["data-id"])))

    if not isinstance(elem, bs4.Tag):
        raise ValueError("elem must be bs4.Tag except DeletedUser")

    if "class" in elem.attrs and "anonymous" in elem["class"]:
        ip_elem = elem.find("span", class_="ip")
        if ip_elem is None:
            return user.AnonymousUser(client=client)
        ip = ip_elem.get_text().replace("(", "").replace(")", "").strip()
        return user.AnonymousUser(client=client, ip=ip)

    # Gravatar URLを持つ場合はGuestUserとする
    img_elem = elem.find("img")
    if isinstance(img_elem, bs4.Tag) and "gravatar.com" in img_elem["src"]:
        avatar_url = img_elem["src"]
        guest_name = elem.get_text().strip().split(" ")[0]
        return user.GuestUser(
            client=client,
            name=guest_name,
            avatar_url=str(avatar_url) if avatar_url else None,
        )

    if elem.get_text() == "Wikidot":
        return user.WikidotUser(client=client)

    _user = elem.find_all("a")[-1]
    if not isinstance(_user, bs4.Tag):
        raise ValueError("link element is not found")
    user_name = _user.get_text()
    user_unix = str(_user.get("href")).replace("http://www.wikidot.com/user:info/", "")
    user_id = int(
        str(_user.get("onclick")).replace("WIKIDOT.page.listeners.userInfo(", "").replace("); return false;", "")
    )

    return user.User(
        client=client,
        id=user_id,
        name=user_name,
        unix_name=user_unix,
        avatar_url=f"http://www.wikidot.com/avatar.php?userid={user_id}",
    )
