"""
Module providing logging functionality

This module configures and provides loggers used throughout the library.
It uses NullHandler to enable log control on the application side.
"""

import logging


def get_logger(name: str = "wikidot") -> logging.Logger:
    """
    Get the library logger

    Parameters
    ----------
    name : str, default "wikidot"
        Logger name

    Returns
    -------
    logging.Logger
        Logger instance
    """
    _logger = logging.getLogger(name)

    if not _logger.handlers:
        _logger.addHandler(logging.NullHandler())

    return _logger


def setup_console_handler(logger: logging.Logger, level: str | int = logging.WARNING) -> None:
    """
    Configure console output handler

    Parameters
    ----------
    logger : logging.Logger
        Logger to configure
    level : str | int, default logging.WARNING
        Log level
    """
    # Remove existing StreamHandler (to avoid duplicates)
    for handler in logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.NullHandler):
            logger.removeHandler(handler)

    # Add new StreamHandler
    formatter = logging.Formatter("%(asctime)s [%(name)s/%(levelname)s] %(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # Set log level (convert if string)
    if isinstance(level, str):
        level_attr = level.upper()
        level_value = getattr(logging, level_attr, None)
        if level_value is None:
            raise ValueError(f"Invalid logging level: {level}")
        level = level_value
    logger.setLevel(level)


# Default logger used throughout the package
logger = get_logger()
