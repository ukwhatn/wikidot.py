from functools import wraps
from .exceptions import LoginRequiredException


def login_required(func):
    """ログインが必要な関数につけるデコレータ

    self.client.is_logged_in()がFalseの場合、LoginExceptionをraiseする
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.client.is_logged_in():
            raise LoginRequiredException("You must be logged in to use this function.")
        return func(self, *args, **kwargs)

    return wrapper
