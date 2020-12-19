import logging

# getlogger
logger = logging.getLogger("wikidot")

logger.setLevel(logging.WARNING)

# stream handler
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(levelname)s:wikidot:%(asctime)s: %(message)s (%(funcName)s)"))
logger.addHandler(sh)
del sh
