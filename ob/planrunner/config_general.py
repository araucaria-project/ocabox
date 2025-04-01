import logging
from typing import Dict, Any, List


log = logging.getLogger(__name__.rsplit('.')[-1])


class ConfigGeneral:

    def __init__(self, telescope: 'Telescope', client_config_dict: Dict or None = None) -> None:
        self.telescope = telescope
        self.config_body_nats = self.get_config_body_nats(client_config_dict=client_config_dict)
        super().__init__()

    def get_config_body_nats(self, client_config_dict: Dict or None) -> Dict or None:
        if client_config_dict is not None and isinstance(client_config_dict, Dict):
            return client_config_dict
        else:
            return self.telescope.observatory.get_client_configuration()

    def get_value(self, seq: List, source: str = 'nats') -> Any:
        ret = self.config_body_nats
        for n in seq:
            try:
                ret = ret[n]
            except (LookupError, TypeError, IndexError):
                log.error(f'No value name {n} in config or wrong seq')
                return None
        if isinstance(ret, str) and '{telescope}' in ret:
            ret = ret.format(telescope=self.telescope.id)
        return ret
