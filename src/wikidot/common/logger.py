"""
ロギング機能を提供するモジュール

このモジュールは、ライブラリ全体で使用されるロガーを設定し、提供する。
NullHandlerを使用してアプリケーション側でのログ制御を可能にする。
"""

import logging


def get_logger(name: str = "wikidot") -> logging.Logger:
    """
    ライブラリ用ロガーを取得

    Parameters
    ----------
    name : str, default "wikidot"
        ロガーの名前

    Returns
    -------
    logging.Logger
        ロガーインスタンス
    """
    _logger = logging.getLogger(name)

    if not _logger.handlers:
        _logger.addHandler(logging.NullHandler())

    return _logger


def setup_console_handler(logger: logging.Logger, level: str | int = logging.WARNING) -> None:
    """
    コンソール出力用ハンドラを設定

    Parameters
    ----------
    logger : logging.Logger
        設定するロガー
    level : str | int, default logging.WARNING
        ログレベル
    """
    # 既存のStreamHandlerを削除（重複回避）
    for handler in logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.NullHandler):
            logger.removeHandler(handler)

    # 新しいStreamHandlerを追加
    formatter = logging.Formatter("%(asctime)s [%(name)s/%(levelname)s] %(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # ログレベルを設定（文字列の場合は変換）
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.WARNING)
    logger.setLevel(level)


# パッケージ全体で使用されるデフォルトロガー
logger = get_logger()
