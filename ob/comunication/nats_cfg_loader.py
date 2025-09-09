import asyncio
import logging
import os
from typing import Optional
from importlib.resources import files

import nats
import yaml

from serverish.messenger import Messenger, get_singlereader

logger = logging.getLogger("NatsCfgLoader")


class NatsCfgLoader:
    # _DEFAULT_CONFIG_FILE = os.path.join(OB_DIR, 'data', 'default_site_config.yml')
    default_config_file_path = files('ob.data') / 'default_site_config.yml'

    def __init__(self, stream: str, use_file: bool = False, fallback_file: Optional[str] = None):
        self._stream: str = stream
        self._cfg_all: dict = {}
        self.fallback_file: str = fallback_file if fallback_file else str(self.default_config_file_path)
        self._use_file = use_file

    def get_cfg(self) -> dict:
        """Return all configuration"""
        return self._cfg_all

    async def load_cfg(self, timeout: Optional[float] = None):
        nats_messenger = Messenger()
        if nats_messenger.is_open and self._stream:
            reader = get_singlereader(self._stream)
            try:
                data, meta = await reader.read(wait=timeout)
                self._cfg_all = data.get("config", {})
                logger.debug("Loading config from nats successfully finished.")
                return
            except asyncio.TimeoutError:
                logger.warning(f"Loading configuration from nats FAILED. Receive Timeout when requesting NATS.")
        else:
            logger.warning(f"Loading configuration from nats FAILED. Can not find opened connection to NATS server, "
                           f"or given stream name is empty string.")

        if self._use_file and self.fallback_file:
            logger.warning(f"Loading configuration from nats FAILED, "
                           f"reading configuration from{self.fallback_file}.")
            self._cfg_all = (await self.load_cfg_from_file(self.fallback_file)).get("config", {})

    @staticmethod
    async def load_cfg_from_file(file: str) -> dict:
        try:
            with open(file, 'r') as f:
                return yaml.safe_load(f)
        except asyncio.CancelledError:
            raise
        except KeyboardInterrupt:
            raise
        except Exception as e:
            logger.error(f"Loading configuration from file {file} FAILED. Error: {e}")
            return {}

    def get_cfg_connection_client(self, client_name: str) -> dict:
        """Return configuration for specific client name"""
        return self.get_cfg_client(client_name=client_name).get("ticconnection", {})

    def get_cfg_client(self, client_name: str) -> dict:
        """Return configuration for specific client name"""
        return self.get_cfg().get("site", {}).get("client", {}).get(client_name, {})
