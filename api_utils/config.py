"""Loader for config.ini in root dir
"""

from configparser import ConfigParser
import os
from api_utils.logging import get_logger

this_path = os.path.dirname(__file__)
logger = get_logger(__name__)


class LoadConfig:
    def __init__(self, file_name: str):
        self.parser = ConfigParser()
        self.parser.optionxform = str  # make option names case sensitive
        self._load_config_from_file(file_name)

    def _load_config_from_file(self, file_name: str, defaults: bool = False):
        found = self.parser.read(file_name)
        if not found and not defaults:
            logger.error(
                f"No config file found at {file_name}. Add one to use your own values. See an example at `config/config.sample.ini`."
            )
        for section in self.parser.sections():
            config_items = self.parser.items(section)

            self.__dict__.update(config_items)


config = LoadConfig(os.path.join(this_path, "../config.ini"))
