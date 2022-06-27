from abc import ABC

import confuse

from ob.ob_config import SingletonConfig


class BaseCommunicationObject(ABC):

    DEFAULT_NAME = 'BaseCommunicationObject'

    def __init__(self, name: str = None, **kwargs):
        self.name = name if name else self.DEFAULT_NAME

    def _get_cfg(self, name_cfg: str, default=None):
        """
        The method looks for a value in the configuration file and returns it.

        :param name_cfg: name of config value
        :param default: default value if key not exist in config
        :return: config value or None if method can't find it
        """
        try:
            value = SingletonConfig.get_config()['router'][self.name][name_cfg].get()
        except confuse.exceptions.NotFoundError:
            value = default
        return value
