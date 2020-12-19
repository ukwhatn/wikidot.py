# -*- coding: utf-8 -*-

""""wikidot.decorator

Decorators for wikidot.py

version:
    1.0.0
copyright:
    (c) 2020 ukwhatn
license:
    MIT License
    legal: http://expunged.xyz/assets/docs/MIT.txt

"""

import asyncio
from functools import wraps

from . import exceptions, variables, logger


def execute(func):
    @wraps(func)
    def _innerfunc(**kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(func(**kwargs))
    return _innerfunc


def require_session(func):
    @wraps(func)
    def _innerfunc(*args, **kwargs):
        logger.logger.info(
            f"Session checking... created: {variables.logged_in}, user: {variables.username}"
        )
        if variables.logged_in is True:
            return func(*args, **kwargs)
        else:
            logger.logger.error(
                "Available session is not found."
            )
            raise exceptions.NoAvailableSessionError(
                f"You need login to wikidot to use this function - {func.__name__}"
            )

    return _innerfunc
