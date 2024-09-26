import logging

import coloredlogs

_logger = logging.getLogger("bdmc")
coloredlogs.install(logger=_logger, level=logging.DEBUG)


def set_log_level(level: int | str):
    """
    Set log level.
    :param level: 
    :return:
    """
    _logger.setLevel(level)


set_log_level(logging.INFO)

if __name__ == "__main__":

    _logger.debug("This is a debug log.")
    _logger.info("This is a info log.")
    _logger.warning("This is a warning log.")
    _logger.error("This is a error log.")
    _logger.critical("This is a critical log.")
