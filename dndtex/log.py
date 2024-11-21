"""
dndtext.log - provide common configuration for logging

Usage:
  from dndtex.log import logger
"""
# import structlog

# structlog.stdlib.recreate_defaults()

# logging = structlog.get_logger()

import logging
import logging.config
from colorlog import ColoredFormatter

LOG_LEVEL = "INFO"
logging.root.setLevel(LOG_LEVEL)

LOG_PARTS = (
    "%(log_color)s%(levelname)8s%(reset)s",
    "%(filename)22s → %(funcName)-18s",
    "|",
    "%(log_color)s%(message)s%(reset)s"
)

LOG_FORMAT = " ".join(LOG_PARTS)

formatter = ColoredFormatter(LOG_FORMAT)

stream = logging.StreamHandler()
stream.setLevel(LOG_LEVEL)
stream.setFormatter(formatter)

logging = logging.getLogger('dndtex')
logging.setLevel(LOG_LEVEL)
logging.addHandler(stream)