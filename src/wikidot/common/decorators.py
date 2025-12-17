"""
各種デコレータを提供するモジュール

このモジュールは、ライブラリ内で使用される共通のデコレータを提供する。
現在は認証関連のデコレータが実装されている。
"""

from collections.abc import Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


def login_required(func: Callable[P, T]) -> Callable[P, T]:
    """
    ログインが必要なメソッドや関数に適用するデコレータ

    このデコレータを適用したメソッドや関数は、実行前に自動的にログイン状態をチェックする。
    ログインしていない場合はLoginRequiredExceptionが送出される。

    クライアントインスタンスは以下の優先順位で検索される：
    1. client という名前の引数
    2. Client クラスのインスタンスである引数
    3. self.client（呼び出し元オブジェクトの属性）
    4. selfが持つ属性が持つclientクラス（例：self.site.client）

    Parameters
    ----------
    func : callable
        デコレートする関数またはメソッド

    Returns
    -------
    callable
        ラップされた関数またはメソッド

    Raises
    ------
    ValueError
        クライアントインスタンスが見つからない場合
    LoginRequiredException
        ログインしていない場合（client.login_check()による）
    """

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        # 循環参照を避けるため、関数内でインポート
        from wikidot.module.client import Client

        client: Client | None = None
        if "client" in kwargs:
            kwarg_client = kwargs["client"]
            if isinstance(kwarg_client, Client):
                client = kwarg_client

        if client is None:
            for arg in args:
                if isinstance(arg, Client):
                    client = arg
                    break

        # selfに存在するか？
        if client is None and args:
            self_obj: Any = args[0]
            if hasattr(self_obj, "client"):
                maybe_client = getattr(self_obj, "client")
                if isinstance(maybe_client, Client):
                    client = maybe_client
            else:
                # selfが持つ属性にclientが存在するか探索する
                for attr_name in dir(self_obj):
                    if attr_name.startswith("_"):
                        continue
                    attr = getattr(self_obj, attr_name)
                    if hasattr(attr, "client"):
                        maybe_client = getattr(attr, "client")
                        if isinstance(maybe_client, Client):
                            client = maybe_client
                            break

        if client is None:
            raise ValueError("Client is not found")

        client.login_check()

        return func(*args, **kwargs)

    return wrapper
