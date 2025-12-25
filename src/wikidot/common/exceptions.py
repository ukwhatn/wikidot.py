# ---
# Base class
# ---


class WikidotException(Exception):
    """
    Base class for wikidot.py specific exceptions

    This serves as the parent class for all exceptions raised within the library.
    Specific exceptions are defined in each subclass.

    Parameters
    ----------
    message : str
        Exception message
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


# ---
# Wildcard
# ---


class UnexpectedException(WikidotException):
    """
    Exception raised when an unexpected error occurs

    Raised in unexpected situations that cannot be classified into a specific error state.
    Usually indicates an internal error or bug.

    Parameters
    ----------
    message : str
        Exception message
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


# ---
# Session related
# ---


class SessionCreateException(WikidotException):
    """
    Exception raised when session creation fails

    Used when a problem occurs during login processing or session establishment.
    Usually caused by incorrect credentials or server-side issues.

    Parameters
    ----------
    message : str
        Exception message
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


class LoginRequiredException(WikidotException):
    """
    Exception raised when calling a method that requires login while not logged in

    Used when checking login status before executing an operation that requires authentication.

    Parameters
    ----------
    message : str
        Exception message
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


# ---
# AMC related
# ---
class AjaxModuleConnectorException(WikidotException):
    """
    Base class for exceptions related to Ajax Module Connector requests

    Parent class for exceptions that occur during API request processing
    to ajax-module-connector.php.
    Specific error states are expressed in each subclass.

    Parameters
    ----------
    message : str
        Exception message
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


class AMCHttpStatusCodeException(AjaxModuleConnectorException):
    """
    Exception raised when the AMC HTTP status code is not 200

    Used when an HTTP-level error occurs in a request to the Ajax Module Connector.

    Parameters
    ----------
    message : str
        Exception message
    status_code : int
        The HTTP status code that caused the error

    Attributes
    ----------
    status_code : int
        The HTTP status code that caused the error
    """

    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class WikidotStatusCodeException(AjaxModuleConnectorException):
    """
    Exception raised when the response status from AMC is not "ok"

    Used when HTTP communication itself succeeds but a processing error
    occurs on the Wikidot side.
    AMCHttpStatusCodeException is used instead when the HTTP status is not 200.

    Parameters
    ----------
    message : str
        Exception message
    status_code : str
        Error status code returned by Wikidot

    Attributes
    ----------
    status_code : str
        Error status code returned by Wikidot
    """

    def __init__(self, message: str, status_code: str) -> None:
        super().__init__(message)
        self.status_code = status_code


class ResponseDataException(AjaxModuleConnectorException):
    """
    Exception raised when response data from AMC is invalid

    Used when response parsing fails or data in an unexpected format is returned.

    Parameters
    ----------
    message : str
        Exception message
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


# ---
# Target error related
# ---


class NotFoundException(WikidotException):
    """
    Exception raised when the requested resource is not found

    Used when the specified resource such as site, page, user, or revision
    does not exist on Wikidot.

    Parameters
    ----------
    message : str
        Exception message
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


class TargetExistsException(WikidotException):
    """
    Exception raised when attempting to create a resource that already exists

    Used when a creation operation conflicts with an existing resource.

    Parameters
    ----------
    message : str
        Exception message
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


class TargetErrorException(WikidotException):
    """
    Exception raised when an operation cannot be applied to the target object

    Used when the resource exists but the requested operation cannot be
    executed in its current state (e.g., trying to edit a locked page).

    Parameters
    ----------
    message : str
        Exception message
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


class ForbiddenException(WikidotException):
    """
    Exception raised when an operation is denied due to insufficient permissions

    Used when the user does not have the required permissions for an operation,
    or when access to a private site is denied.

    Parameters
    ----------
    message : str
        Exception message
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


# ---
# Processing error related
# ---


class NoElementException(WikidotException):
    """
    Exception raised when a required element is not found

    Used when expected elements are not found during HTML parsing,
    or when required data is missing during processing.

    Parameters
    ----------
    message : str
        Exception message
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
