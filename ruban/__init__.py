import logging
import config
from utils.log import get_logger


log_level = logging.DEBUG if config.DEBUG else logging.INFO

path = config.LOGGER_PATH
filename = config.FILENAME

logger = get_logger(__name__, level=log_level, path=path, filename=filename)

__all__ = ["logger"]
