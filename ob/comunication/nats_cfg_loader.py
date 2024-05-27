import logging
import os
from typing import Optional

import nats
import yaml

from serverish.messenger import Messenger, get_singlereader

logger = logging.getLogger("NatsCfgLoader")


class NatsCfgLoader:
    _default_config_file = os.path.join(os.path.dirname(__file__), 'integrations.yml')

    def __init__(self, stream: str, fallback_file: Optional[str] = _default_config_file):
        self._stream: str = stream
        self._cfg_all: dict = {}
        self.fallback_file: str = fallback_file

    def get_cfg(self) -> dict:
        """Return all configuration"""
        return self._cfg_all

    async def load_cfg(self, timeout: Optional[float] = None):
        nats_messenger = Messenger()
        if not nats_messenger.is_open:
            logger.warning(f"Loading configuration from nats FAILED. Can not find opened connection to NATS server.")
            return
        reader = get_singlereader(self._stream)
        try:
            data, meta = await reader.read(wait=timeout)
            self._cfg_all = data.get("config", {})
        except Exception as e:
            if self.fallback_file:
                logger.warning(f"Loading configuration from nats FAILED, "
                               f"reading configuration from{self.fallback_file}. Error: {e}")
                self._cfg_all = await self.load_cfg_from_file(self.fallback_file)
            else:
                logger.error(f"Loading configuration from nats FAILED. Error: {e}")

    async def load_cfg_from_file(self, file: str) -> dict:
        try:
            with open(file, 'r') as f:
                return yaml.load(f)
        except Exception as e:
            logger.error(f"Loading configuration from file {file} FAILED. Error: {e}")
            return {}

    def get_cfg_connection_client(self, client_name: str) -> dict:
        """Return configuration for specific client name"""
        return self.get_cfg_client(client_name=client_name).get("ticconnection", {})

    def get_cfg_client(self, client_name: str) -> dict:
        """Return configuration for specific client name"""
        return self.get_cfg().get("site", {}).get("client", {}).get(client_name, {})


