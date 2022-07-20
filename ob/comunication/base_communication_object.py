import logging
from abc import ABC
import confuse
from ob.ob_config import SingletonConfig
from zmq.asyncio import Context

logger = logging.getLogger(__name__)


class BaseCommunicationObject(ABC):
    DEFAULT_NAME = 'BaseCommunicationObject'
    _TYPE = 'default'

    def __init__(self, name: str = None, port: int = None, **kwargs):
        self.name = name if name else self.DEFAULT_NAME
        self._port = port if port else self._get_cfg('port')
        if not self._port or not isinstance(self._port, int):
            logger.error(f"Can not get correct port for {self._TYPE}")
            raise RuntimeError
        # OMQ
        self.context = Context()  # TODO One for all router (Context.instance()) or one for everyone router (Context())?

    def _get_cfg(self, name_cfg: str, default=None, use_default_settings=True):
        """
        The method looks for a value in the configuration file and returns it.

        :param name_cfg: name of config value
        :param default: default value if key not exist in config
        :param use_default_settings: use default settings if default value is None and can not get settings
        :return: config value or None if method can't find it
        """
        try:
            value = SingletonConfig.get_config()[self._TYPE][self.name][name_cfg].get()
        except confuse.exceptions.NotFoundError:
            if default is None and use_default_settings:
                try:
                    value = SingletonConfig.get_config()[self._TYPE][self.DEFAULT_NAME][name_cfg].get()
                except confuse.exceptions.NotFoundError:
                    value = default
            else:
                value = default
        return value

    def __del__(self):
        self.context.destroy()  # without this zmq not close socket when BaseCommunicationObject is destroy
