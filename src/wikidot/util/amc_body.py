"""Helpers for building Ajax Module Connector request bodies.

Wikidot's client-side form serialization (OZONE.utils.formToArray) has a
rule that a plain Python dict does not reproduce on its own: an unchecked
checkbox is not sent as `False`, its key is omitted entirely. Sending
`"false"` or an empty string instead means "turn this off" silently
becomes "no change". These helpers let call sites pass plain `bool` /
`None` values and get the correct AMC wire format.
"""

import json
from typing import Any, Literal


def checkbox(value: bool | None) -> "str | Literal[False]":
    """
    Encode a checkbox-style boolean for an AMC request

    Mirrors `OZONE.utils.formToArray`: a checked checkbox is sent as the
    literal string "on"; an unchecked one is omitted from the request
    entirely (not sent as "false"). Pass the result through omit_falsy()
    so the False case drops the key instead of being sent.

    Parameters
    ----------
    value : bool | None
        Checkbox state. None is treated the same as False (omitted)

    Returns
    -------
    str | Literal[False]
        "on" if value is truthy, otherwise False for omit_falsy() to drop
    """
    return "on" if value else False


def flag(value: bool | None) -> "str | Literal[False]":
    """
    Encode a JS-boolean-style flag for an AMC request

    Some modules build the request body by hand in JS instead of via
    formToArray (e.g. `if (checkbox.checked) { p.sticky = true; }`), which
    sends the literal string "true" when set and omits the key otherwise.

    Parameters
    ----------
    value : bool | None
        Flag state. None is treated the same as False (omitted)

    Returns
    -------
    str | Literal[False]
        "true" if value is truthy, otherwise False for omit_falsy() to drop
    """
    return "true" if value else False


def json_param(obj: Any) -> Any:
    """
    Encode a value as a JSON string for an AMC request parameter

    Used for parameters such as `categories` / `options` / `addresses`
    that Wikidot expects as a JSON-encoded string, not a native array/object.

    Parameters
    ----------
    obj : Any
        Value to encode. None is passed through for omit_falsy() to drop

    Returns
    -------
    Any
        JSON string of obj, or None if obj is None
    """
    if obj is None:
        return None
    return json.dumps(obj)


def omit_falsy(**kwargs: Any) -> dict[str, Any]:
    """
    Build an AMC request body fragment, dropping None / False values

    httpx serializes a request body value of Python True/False as the
    literal strings "true"/"false" (see httpx._utils.primitive_value_to_str),
    which is wrong for Wikidot's checkbox semantics: an unchecked checkbox
    must be represented by the key being absent from the request entirely,
    not present with value "false" (formToArray never emits it; see
    10_transport.md). This is the single place that enforces that rule, so
    call sites can pass plain bool/None values — or checkbox(v)/flag(v)/
    json_param(v) results — without hand-rolling the omission themselves.

    Uses identity comparison (`is False`, not `== False`) so a legitimate
    `0` value is kept; only the None and False singletons are dropped.

    Parameters
    ----------
    **kwargs : Any
        Candidate key-value pairs

    Returns
    -------
    dict[str, Any]
        kwargs with None and False values removed
    """
    return {key: value for key, value in kwargs.items() if value is not None and value is not False}
