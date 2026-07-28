"""
Encoders/decoders for Wikidot's compact permission and rating strings

Manage Site's category objects hold permissions as a single semicolon-
separated string (e.g. ``v:armo;c:m;...``), forum permissions in a similar
but distinct format, and rating configuration as a fixed 4-character code
(e.g. ``drvM``). These are typed here instead of being passed around as raw
strings so callers get validation and IDE support; see 30_plan.md D4 for the
design rationale (in particular: unknown symbols are preserved through a
decode/encode round trip rather than dropped, since at least one forum
permission symbol ("s") is defined in Wikidot's client JS but has an
unconfirmed purpose).
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Literal

Actor = Literal["anonymous", "registered", "member", "author"]

#: Fixed column order used when encoding an actor set back to symbols.
#: Matches the "users" column order documented in 40_admin-managesite.md
#: (a/r/m/o), which the "v:armo" example relies on.
_ACTOR_ORDER: tuple[Actor, ...] = ("anonymous", "registered", "member", "author")

_ACTOR_TO_SYMBOL: dict[Actor, str] = {
    "anonymous": "a",
    "registered": "r",
    "member": "m",
    "author": "o",
}
_SYMBOL_TO_ACTOR: dict[str, Actor] = {v: k for k, v in _ACTOR_TO_SYMBOL.items()}


def _encode_actors(actors: frozenset[Actor]) -> str:
    """Encode an actor set into its fixed-order symbol string (e.g. "armo")"""
    return "".join(_ACTOR_TO_SYMBOL[actor] for actor in _ACTOR_ORDER if actor in actors)


def _decode_actors(symbols: str) -> frozenset[Actor] | None:
    """
    Decode a symbol string into an actor set

    Returns None (instead of a partial set) if any character is not a known
    actor symbol, so the caller can preserve the whole segment verbatim
    rather than silently drop the unrecognized part.
    """
    actors: set[Actor] = set()
    for symbol in symbols:
        actor = _SYMBOL_TO_ACTOR.get(symbol)
        if actor is None:
            return None
        actors.add(actor)
    return frozenset(actors)


# Row (permission) order is fixed by 40_admin-managesite.md.
_PAGE_PERM_ORDER: tuple[str, ...] = ("v", "c", "e", "m", "d", "a", "r", "z", "o")
_PAGE_PERM_FIELD: dict[str, str] = {
    "v": "view",
    "c": "create",
    "e": "edit",
    "m": "move",
    "d": "delete",
    "a": "upload_files",
    "r": "rename_files",
    "z": "replace_files",
    "o": "show_options",
}


@dataclass(frozen=True)
class PagePermissions:
    """
    Decoded form of a category's `permissions` string

    Attributes
    ----------
    view, create, edit, move, delete, upload_files, rename_files,
    replace_files, show_options : frozenset[Actor]
        Actors granted each permission. Empty by default (no one)
    """

    view: frozenset[Actor] = frozenset()
    create: frozenset[Actor] = frozenset()
    edit: frozenset[Actor] = frozenset()
    move: frozenset[Actor] = frozenset()
    delete: frozenset[Actor] = frozenset()
    upload_files: frozenset[Actor] = frozenset()
    rename_files: frozenset[Actor] = frozenset()
    replace_files: frozenset[Actor] = frozenset()
    show_options: frozenset[Actor] = frozenset()
    #: Raw "letter:users" segments this library did not recognize, preserved
    #: verbatim so a decode -> encode round trip never loses data
    _unknown: tuple[str, ...] = field(default_factory=tuple)

    def encode(self) -> str:
        """
        Encode back into Wikidot's `permissions` string format

        Returns
        -------
        str
            e.g. "v:armo;c:m;e:m;m:m;d:m;a:m;r:m;z:m;o:rm"
        """
        segments = [
            f"{symbol}:{_encode_actors(getattr(self, _PAGE_PERM_FIELD[symbol]))}" for symbol in _PAGE_PERM_ORDER
        ]
        segments.extend(self._unknown)
        return ";".join(segments)

    @classmethod
    def decode(cls, s: str) -> "PagePermissions":
        """
        Decode a category's `permissions` string

        Parameters
        ----------
        s : str
            Raw string, e.g. "v:armo;c:m;e:m;m:m;d:m;a:m;r:m;z:m;o:rm"

        Returns
        -------
        PagePermissions
        """
        fields: dict[str, frozenset[Actor]] = {}
        unknown: list[str] = []
        for segment in s.split(";"):
            if not segment:
                continue
            symbol, _, users = segment.partition(":")
            field_name = _PAGE_PERM_FIELD.get(symbol)
            actors = _decode_actors(users) if field_name is not None else None
            if field_name is not None and actors is not None:
                fields[field_name] = actors
            else:
                unknown.append(segment)
        return cls(**fields, _unknown=tuple(unknown))

    def validate(self) -> list[str]:
        """
        Check the anonymous ⊂ registered ⊂ member containment convention

        Wikidot's Manage Site UI enforces this relationship client-side
        (granting anonymous access implies registered and member access,
        and so on), but it is unconfirmed whether the server enforces it
        too. This library does not auto-correct the containment (doing so
        could silently grant permissions the caller did not ask for); call
        this explicitly if you want to check before saving.

        Returns
        -------
        list[str]
            Human-readable description of each violated field. Empty if
            everything is consistent
        """
        violations: list[str] = []
        for symbol in _PAGE_PERM_ORDER:
            field_name = _PAGE_PERM_FIELD[symbol]
            actors = getattr(self, field_name)
            if "anonymous" in actors and not {"registered", "member"} <= actors:
                violations.append(f"{field_name}: anonymous access requires registered and member access too")
            elif "registered" in actors and "member" not in actors:
                violations.append(f"{field_name}: registered access requires member access too")
        return violations


# Forum permission row order per 40_admin-managesite.md ("t"=Create new
# threads / "p"=Add new posts / "e"=Edit posts). The "s" symbol is defined
# in Wikidot's client JS (vars.permissions) but not rendered in the
# permission table on any site checked during the survey, so its meaning
# is unconfirmed; it round-trips through `_unknown` like any other
# unrecognized segment instead of being modeled as a known field.
_FORUM_PERM_ORDER: tuple[str, ...] = ("t", "p", "e")
_FORUM_PERM_FIELD: dict[str, str] = {
    "t": "create_threads",
    "p": "add_posts",
    "e": "edit_posts",
}


@dataclass(frozen=True)
class ForumPermissions:
    """
    Decoded form of `ManageSiteForumAction/saveForumPermissions`'s
    per-category `permissions` string (a separate encoding from
    PagePermissions despite the similar shape)

    Attributes
    ----------
    create_threads, add_posts, edit_posts : frozenset[Actor]
        Actors granted each permission
    """

    create_threads: frozenset[Actor] = frozenset()
    add_posts: frozenset[Actor] = frozenset()
    edit_posts: frozenset[Actor] = frozenset()
    #: Raw "letter:users" segments this library did not recognize (e.g. the
    #: unconfirmed "s" symbol), preserved verbatim
    _unknown: tuple[str, ...] = field(default_factory=tuple)

    def encode(self) -> str:
        """
        Encode back into the forum `permissions` string format

        Returns
        -------
        str
        """
        segments = [
            f"{symbol}:{_encode_actors(getattr(self, _FORUM_PERM_FIELD[symbol]))}" for symbol in _FORUM_PERM_ORDER
        ]
        segments.extend(self._unknown)
        return ";".join(segments)

    @classmethod
    def decode(cls, s: str) -> "ForumPermissions":
        """
        Decode a forum category's `permissions` string

        Parameters
        ----------
        s : str

        Returns
        -------
        ForumPermissions
        """
        fields: dict[str, frozenset[Actor]] = {}
        unknown: list[str] = []
        for segment in s.split(";"):
            if not segment:
                continue
            symbol, _, users = segment.partition(":")
            field_name = _FORUM_PERM_FIELD.get(symbol)
            actors = _decode_actors(users) if field_name is not None else None
            if field_name is not None and actors is not None:
                fields[field_name] = actors
            else:
                unknown.append(segment)
        return cls(**fields, _unknown=tuple(unknown))


_VOTER_TO_SYMBOL: dict[str, str] = {"registered": "r", "member": "m"}
_SYMBOL_TO_VOTER: dict[str, Literal["registered", "member"]] = {"r": "registered", "m": "member"}
_KIND_TO_SYMBOL: dict[str, str] = {"plus_only": "P", "plus_minus": "M", "stars": "S"}
_SYMBOL_TO_KIND: dict[str, Literal["plus_only", "plus_minus", "stars"]] = {
    "P": "plus_only",
    "M": "plus_minus",
    "S": "stars",
}


@dataclass(frozen=True)
class RatingSettings:
    """
    Decoded form of a category's 4-character `rating` code (e.g. "drvM")

    Attributes
    ----------
    enabled : bool
        Whether rating is enabled for the category
    voters : Literal["registered", "member"]
        Who can vote
    anonymous : bool
        Whether votes are anonymous (True) or show the voter (False)
    kind : Literal["plus_only", "plus_minus", "stars"]
        Rating widget type
    """

    enabled: bool
    voters: Literal["registered", "member"]
    anonymous: bool
    kind: Literal["plus_only", "plus_minus", "stars"]

    def encode(self) -> str:
        """
        Encode back into Wikidot's 4-character `rating` code

        Returns
        -------
        str
            e.g. "drvM"
        """
        return "".join(
            [
                "e" if self.enabled else "d",
                _VOTER_TO_SYMBOL[self.voters],
                "a" if self.anonymous else "v",
                _KIND_TO_SYMBOL[self.kind],
            ]
        )

    @classmethod
    def decode(cls, s: str) -> "RatingSettings":
        """
        Decode a category's `rating` code

        Parameters
        ----------
        s : str
            4-character code, e.g. "drvM"

        Returns
        -------
        RatingSettings

        Raises
        ------
        ValueError
            If `s` is not a recognized 4-character code. Unlike
            PagePermissions/ForumPermissions, no unrecognized-but-real
            variant of this code was found during the survey (each of the
            4 positions has exactly 2 documented values), so this raises
            instead of silently guessing at an unknown format
        """
        if (
            len(s) != 4
            or s[0] not in "ed"
            or s[1] not in _SYMBOL_TO_VOTER
            or s[2] not in "av"
            or s[3] not in _SYMBOL_TO_KIND
        ):
            raise ValueError(f"Invalid rating code: {s!r}")
        return cls(
            enabled=s[0] == "e",
            voters=_SYMBOL_TO_VOTER[s[1]],
            anonymous=s[2] == "a",
            kind=_SYMBOL_TO_KIND[s[3]],
        )


def replace_actors(permissions: PagePermissions, **updates: Iterable[Actor]) -> PagePermissions:
    """
    Return a copy of `permissions` with only the specified fields replaced

    Convenience for the common "change one permission, leave the rest"
    pattern. Built as an explicit field-by-field copy rather than
    `dataclasses.replace(permissions, **updates)`: mypy's dataclass plugin
    cannot type-check a `**dict` splat against per-field types, so this
    keeps every field statically checked instead of relying on `# type:
    ignore`

    Parameters
    ----------
    permissions : PagePermissions
        Base permissions to copy
    **updates : Iterable[Actor]
        Field name to new actor iterable (e.g. view=("anonymous",))

    Returns
    -------
    PagePermissions
    """
    unknown_names = set(updates) - set(_PAGE_PERM_FIELD.values())
    if unknown_names:
        raise ValueError(f"Unknown PagePermissions field(s): {sorted(unknown_names)}")

    def _field(name: str) -> frozenset[Actor]:
        return frozenset(updates[name]) if name in updates else getattr(permissions, name)

    return PagePermissions(
        view=_field("view"),
        create=_field("create"),
        edit=_field("edit"),
        move=_field("move"),
        delete=_field("delete"),
        upload_files=_field("upload_files"),
        rename_files=_field("rename_files"),
        replace_files=_field("replace_files"),
        show_options=_field("show_options"),
        _unknown=permissions._unknown,
    )
