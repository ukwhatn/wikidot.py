"""
ロギング機能を提供するモジュール

このモジュールは、ライブラリ全体で使用されるロガーを設定し、提供する。
ログレベルの設定やフォーマットの指定などが可能。
"""

import logging


def setup_logger(name: str = "wikidot", level=logging.INFO):
    """
    ロガーを設定する関数

    指定された名前とログレベルでロガーを設定し、適切なフォーマットのハンドラを追加する。
    デフォルトでは、時刻、ロガー名、ログレベル、メッセージを表示する形式となる。

    Parameters
    ----------
    name : str, default "wikidot"
        ロガーの名前
    level : int, default logging.INFO
        初期ログレベル

    Returns
    -------
    logging.Logger
        設定されたロガーインスタンス
    """
    _logger = logging.getLogger(name)
    _logger.setLevel(level)

    # ログフォーマット
    formatter = logging.Formatter("%(asctime)s [%(name)s/%(levelname)s] %(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    _logger.addHandler(stream_handler)

    return _logger


# パッケージ全体で使用されるデフォルトロガー
logger = setup_logger()
