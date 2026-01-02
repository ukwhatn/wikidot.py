"""HTTP utilities with retry mechanism."""

import asyncio
import random
import time

import httpx


def _is_retryable_status(status_code: int) -> bool:
    """Check if HTTP status code is retryable (5xx server errors)."""
    return 500 <= status_code < 600


def calculate_backoff(
    retry_count: int,
    base_interval: float,
    backoff_factor: float,
    max_backoff: float,
) -> float:
    """Calculate backoff time with exponential backoff and jitter.

    Parameters
    ----------
    retry_count
        Current retry count (1-based)
    base_interval
        Base interval in seconds
    backoff_factor
        Exponential backoff factor
    max_backoff
        Maximum backoff time in seconds

    Returns
    -------
    float
        Backoff time in seconds
    """
    backoff = (backoff_factor ** (retry_count - 1)) * base_interval
    jitter = random.uniform(0, backoff * 0.1)
    return min(backoff + jitter, max_backoff)


async def async_get_with_retry(
    url: str,
    *,
    timeout: float = 20.0,
    attempt_limit: int = 5,
    retry_interval: float = 1.0,
    max_backoff: float = 60.0,
    backoff_factor: float = 2.0,
    headers: dict[str, str] | None = None,
    follow_redirects: bool = True,
) -> httpx.Response:
    """Async GET request with retry on timeout/network errors.

    Parameters
    ----------
    url
        URL to fetch
    timeout
        Request timeout in seconds
    attempt_limit
        Maximum number of attempts
    retry_interval
        Base retry interval in seconds
    max_backoff
        Maximum backoff time in seconds
    backoff_factor
        Exponential backoff factor
    headers
        Optional HTTP headers
    follow_redirects
        Whether to follow redirects

    Returns
    -------
    httpx.Response
        HTTP response

    Raises
    ------
    httpx.TimeoutException
        If all retries exhausted due to timeout
    httpx.NetworkError
        If all retries exhausted due to network error
    httpx.HTTPStatusError
        If all retries exhausted due to HTTP error
    """
    for attempt in range(attempt_limit):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, headers=headers, follow_redirects=follow_redirects)
                response.raise_for_status()
                return response
        except httpx.HTTPStatusError as e:
            # Don't retry 4xx errors - they are client errors that won't change on retry
            if not _is_retryable_status(e.response.status_code):
                raise
            if attempt >= attempt_limit - 1:
                raise
            backoff = calculate_backoff(
                attempt + 1,
                retry_interval,
                backoff_factor,
                max_backoff,
            )
            await asyncio.sleep(backoff)
        except (httpx.TimeoutException, httpx.NetworkError):
            if attempt >= attempt_limit - 1:
                raise
            backoff = calculate_backoff(
                attempt + 1,
                retry_interval,
                backoff_factor,
                max_backoff,
            )
            await asyncio.sleep(backoff)
    raise RuntimeError("Unreachable")


def sync_get_with_retry(
    url: str,
    *,
    timeout: float = 20.0,
    attempt_limit: int = 5,
    retry_interval: float = 1.0,
    max_backoff: float = 60.0,
    backoff_factor: float = 2.0,
    headers: dict[str, str] | None = None,
    follow_redirects: bool = True,
    raise_for_status: bool = True,
) -> httpx.Response:
    """Sync GET request with retry on timeout/network errors.

    Parameters
    ----------
    url
        URL to fetch
    timeout
        Request timeout in seconds
    attempt_limit
        Maximum number of attempts
    retry_interval
        Base retry interval in seconds
    max_backoff
        Maximum backoff time in seconds
    backoff_factor
        Exponential backoff factor
    headers
        Optional HTTP headers
    follow_redirects
        Whether to follow redirects
    raise_for_status
        Whether to raise HTTPStatusError for 4xx/5xx responses

    Returns
    -------
    httpx.Response
        HTTP response

    Raises
    ------
    httpx.TimeoutException
        If all retries exhausted due to timeout
    httpx.NetworkError
        If all retries exhausted due to network error
    httpx.HTTPStatusError
        If all retries exhausted due to HTTP error (when raise_for_status=True)
    """
    for attempt in range(attempt_limit):
        try:
            response = httpx.get(
                url,
                headers=headers,
                timeout=timeout,
                follow_redirects=follow_redirects,
            )
            if raise_for_status:
                response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            # Don't retry 4xx errors - they are client errors that won't change on retry
            if not _is_retryable_status(e.response.status_code):
                raise
            if attempt >= attempt_limit - 1:
                raise
            backoff = calculate_backoff(
                attempt + 1,
                retry_interval,
                backoff_factor,
                max_backoff,
            )
            time.sleep(backoff)
        except (httpx.TimeoutException, httpx.NetworkError):
            if attempt >= attempt_limit - 1:
                raise
            backoff = calculate_backoff(
                attempt + 1,
                retry_interval,
                backoff_factor,
                max_backoff,
            )
            time.sleep(backoff)
    raise RuntimeError("Unreachable")


def sync_post_with_retry(
    url: str,
    *,
    data: dict | None = None,
    timeout: float = 20.0,
    attempt_limit: int = 5,
    retry_interval: float = 1.0,
    max_backoff: float = 60.0,
    backoff_factor: float = 2.0,
    headers: dict[str, str] | None = None,
    raise_for_status: bool = True,
) -> httpx.Response:
    """Sync POST request with retry on timeout/network errors.

    Parameters
    ----------
    url
        URL to post to
    data
        Form data to send
    timeout
        Request timeout in seconds
    attempt_limit
        Maximum number of attempts
    retry_interval
        Base retry interval in seconds
    max_backoff
        Maximum backoff time in seconds
    backoff_factor
        Exponential backoff factor
    headers
        Optional HTTP headers
    raise_for_status
        Whether to raise HTTPStatusError for 4xx/5xx responses

    Returns
    -------
    httpx.Response
        HTTP response

    Raises
    ------
    httpx.TimeoutException
        If all retries exhausted due to timeout
    httpx.NetworkError
        If all retries exhausted due to network error
    httpx.HTTPStatusError
        If all retries exhausted due to HTTP error (when raise_for_status=True)
    """
    for attempt in range(attempt_limit):
        try:
            response = httpx.post(
                url,
                data=data,
                headers=headers,
                timeout=timeout,
            )
            if raise_for_status:
                response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            # Don't retry 4xx errors - they are client errors that won't change on retry
            if not _is_retryable_status(e.response.status_code):
                raise
            if attempt >= attempt_limit - 1:
                raise
            backoff = calculate_backoff(
                attempt + 1,
                retry_interval,
                backoff_factor,
                max_backoff,
            )
            time.sleep(backoff)
        except (httpx.TimeoutException, httpx.NetworkError):
            if attempt >= attempt_limit - 1:
                raise
            backoff = calculate_backoff(
                attempt + 1,
                retry_interval,
                backoff_factor,
                max_backoff,
            )
            time.sleep(backoff)
    raise RuntimeError("Unreachable")
