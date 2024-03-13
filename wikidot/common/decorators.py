from functools import wraps

from wikidot.module.client import Client
from .exceptions import LoginRequiredException


def login_required(func):
    """ログインが必要な関数につけるデコレータ

    関数のパラメータに存在するclientを取得し、ログインしていない場合は例外を送出する
    clientはパラメータ、もしくはself.clientで取得できる
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        client = None
        if 'client' in kwargs:
            client = kwargs['client']
        else:
            for arg in args:
                if isinstance(arg, Client):
                    client = arg
                    break

            # selfに存在するか？
            if client is None:
                if hasattr(args[0], 'client'):
                    client = args[0].client

        if client is None:
            raise ValueError('Client is not found')

        if not client.is_logged_in:
            raise LoginRequiredException('Login is required to execute this function')

        return func(*args, **kwargs)

    return wrapper
