# -*- coding: utf-8 -*-

""""wikidot.exceptions

Custom Exceptions for wikidot.py

version:
    1.0.0
copyright:
    (c) 2020 ukwhatn
license:
    MIT License
    legal: http://expunged.xyz/assets/docs/MIT.txt

"""


class WikidotError(Exception):
    """Parent"""
    pass


class UnexpectedError(WikidotError):
    """Unexpected Error Occurred"""
    pass


class ArgumentsError(WikidotError):
    """Arguments are invalid."""
    pass


class AMCRequestError(WikidotError):
    # ajax-module-connector.php returns error
    pass


class RequestFailedError(AMCRequestError):
    # Error occurred while requesting
    pass


class ReturnedDataError(AMCRequestError):
    # Returned Data is not applopliate
    pass


class StatusIsNotOKError(AMCRequestError):
    # ajax-module-connector.php returns error
    pass


class SessionError(WikidotError):
    # Error occurred while login session
    pass


class SessionCreateError(SessionError):
    # There is no available session when you try to do any actions.
    pass


class NoAvailableSessionError(SessionError):
    # There is no available session when you try to do any actions.
    pass
