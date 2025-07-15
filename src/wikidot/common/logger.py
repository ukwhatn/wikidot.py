"""
ロギング機能を提供するモジュール

このモジュールは、ライブラリ全体で使用されるロガーを設定し、提供する。
NullHandlerを使用してアプリケーション側でのログ制御を可能にする。
"""

import logging


def get_logger(name: str = "wikidot"):
    """ライブラリ用ロガーを取得"""
    _logger = logging.getLogger(name)
    
    if not _logger.handlers:
        _logger.addHandler(logging.NullHandler())
    
    return _logger


def setup_console_handler(logger: logging.Logger, level=logging.WARNING):
    """コンソール出力用ハンドラを設定"""
    # 既存のStreamHandlerを削除（重複回避）
    for handler in logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.NullHandler):
            logger.removeHandler(handler)
    
    # 新しいStreamHandlerを追加
    formatter = logging.Formatter("%(asctime)s [%(name)s/%(levelname)s] %(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    logger.setLevel(level)


# パッケージ全体で使用されるデフォルトロガー
logger = get_logger()
