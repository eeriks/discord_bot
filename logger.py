import datetime
import json
import logging
import os
import sys
from json import JSONDecodeError
from typing import Union
import time

APP_NAME = "discord_bot"

os.chdir(os.path.abspath(os.path.dirname(sys.argv[0])))

logger = logging.getLogger(APP_NAME)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

file_logger = logging.FileHandler(f"./logging.log", "w")
file_logger.setLevel(logging.WARNING)
file_logger.setFormatter(formatter)
logger.addHandler(file_logger)

stream_logger = logging.StreamHandler()
stream_logger.setLevel(logging.INFO)
stream_logger.setFormatter(formatter)
logger.addHandler(stream_logger)

logger.setLevel(logging.INFO)


def main():
    logger.info('Info message')
    logger.debug('Debug message')
    logger.warning('Warning message')
    logger.error('Error message')
    logger.critical('Critical message')


if __name__ == "__main__":
    main()
