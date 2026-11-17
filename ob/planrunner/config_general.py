import logging
from typing import Dict, Any, List, Optional

log = logging.getLogger(__name__.rsplit('.')[-1])


class ConfigGeneral:

    def __init__(self, telescope: 'Telescope', client_config_dict: Optional[Dict] = None) -> None:
        self.telescope = telescope
        self.config_body_nats = self.get_config_body_nats(client_config_dict=client_config_dict)
        super().__init__()

    def get_config_body_nats(self, client_config_dict: Optional[Dict]) -> Optional[Dict]:
        if client_config_dict is not None and isinstance(client_config_dict, Dict):
            return client_config_dict
        else:
            return self.telescope.observatory.get_client_configuration()

    def get_value(self, seq: List, source: str = 'nats', instr_id: Optional[str] = None) -> Any:
        ret = self.config_body_nats
        for n in seq:
            try:
                ret = ret[n]
            except (LookupError, TypeError, IndexError):
                log.error(f'No value name {n} in config or wrong seq')
                return None
        if isinstance(ret, str) and '{telescope}' in ret and instr_id is None and not '{instrument}' in ret:
            ret = ret.format(telescope=self.telescope.id)
        elif isinstance(ret, str) and '{telescope}' in ret and instr_id is not None and '{instrument}' in ret:
            ret = ret.format(telescope=self.telescope.id, instrument=instr_id)
        elif isinstance(ret, str) and '{telescope}' in ret and instr_id is None and '{instrument}' in ret:
            raise RuntimeError
        elif isinstance(ret, str) and '{telescope}' in ret and instr_id is not None and '{instrument}' not in ret:
            raise RuntimeError
        return ret
