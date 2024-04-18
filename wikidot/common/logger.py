import logging


# Logger設定
def setup_logger(name: str = "wikidot", level=logging.INFO):
    _logger = logging.getLogger(name)
    _logger.setLevel(level)

    # ログフォーマット
    formatter = logging.Formatter("%(asctime)s [%(name)s/%(levelname)s] %(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    _logger.addHandler(stream_handler)

    return _logger


logger = setup_logger()
