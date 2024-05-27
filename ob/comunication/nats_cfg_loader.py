import logging
from typing import Optional

import nats
from serverish.messenger import Messenger, get_singlereader

logger = logging.getLogger("NatsCfgLoader")


class NatsCfgLoader:

    def __init__(self, stream: str):
        self._stream: str = stream
        self._cfg_all: dict = {}

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
        except nats.errors.TimeoutError:
            logger.warning(f"Loading configuration from nats FAILED. Receive Timeout when requesting NATS.")
            return

    def get_cfg_connection_client(self, client_name: str) -> dict:
        """Return configuration for specific client name"""
        return self.get_cfg_client(client_name=client_name).get("ticconnection", {})

    def get_cfg_client(self, client_name: str) -> dict:
        """Return configuration for specific client name"""
        return self.get_cfg().get("site", {}).get("client", {}).get(client_name, {})
