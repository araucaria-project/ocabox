from enum import Enum
from typing import Dict, Any
from serverish.messenger.msg_publisher import MsgPublisher
import logging

try:
    from enum import StrEnum
except ImportError:
    class StrEnum(str, Enum):
        pass

logger = logging.getLogger(__name__.rsplit('.')[-1])

class PlanStatusEnum(StrEnum):
    """
     Plan status enum
    Statuses:

    """
    loaded = '...'
    running = 'running'
    done = 'done'
    skipped = 'skipped'
    stop = 'stop'
    error = 'error'


class PlanStatus:

    def __init__(self, telescope: 'Telescope') -> None:
        self.telescope = telescope
        self.static_dict: Dict = {}
        self.time_dict: Dict = {}
        self.status_dict: Dict = {}
        self.plan_static_publisher: MsgPublisher or None = None
        self.plan_status_publisher: MsgPublisher or None = None
        self.plan_time_publisher: MsgPublisher or None = None
        super().__init__()

    def build(self, id: str, name: str, ctype: str) -> None:
        self.static_dict[id] = {'name': name, 'ctype':  ctype, 'kwargs': {}, 'args': []}
        self.status_dict[id] = {'status': PlanStatusEnum.loaded}
        self.time_dict[id] = {'ctc_time': 0.0, 'real_time': 0.0, 'dynamic': False}

    async def reset(self)-> None:
        self.static_dict = {}
        self.plan_time = {}
        self.plan_status = {}

    async def send_all_to_nats(self)-> None:
        await self.send_to_nats(publisher=self.plan_static_publisher, data=self.static_dict)
        await self.send_to_nats(publisher=self.plan_status_publisher, data=self.status_dict)
        await self.send_to_nats(publisher=self.plan_time_publisher, data=self.time_dict)

    async def send_to_nats(self, publisher: MsgPublisher, data: Dict)-> None:
        try:
            await publisher.publish(data=data, timeout=10)
        except TimeoutError:
            logger.error(f'Nats publish get timeout error')

    async def upd_status(self, id: str, value: PlanStatusEnum, field: str = 'status') -> None:
        self.status_dict[id][field] = value
        await self.send_to_nats(self.plan_status_publisher, self.status_dict)

    def upd_ctc_time(self, id: str, value: float) -> None:
        self.time_dict[id]['ctc_time'] = value

    def upd_dynamic_time(self, id: str, value: bool) -> None:
        self.time_dict[id]['dynamic'] = value

    async def upd_real_time(self, id: str, value: float) -> None:
        self.time_dict[id]['real_time'] = value
        await self.send_to_nats(self.plan_time_publisher, self.time_dict)

    def upd_static_kwargs(self, id: str, value: Any, field: str or None = None) -> None:
        if isinstance(value, dict):
            self.static_dict[id]['kwargs'] = self.static_dict[id]['kwargs'] | value
        else:
            self.static_dict[id]['kwargs'][field] = value

    def upd_static_args(self, id: str, args_list: list) -> None:
        for n in args_list:
            self.static_dict[id]['args'].append(n)

    def upd_static_name(self, id: str, value: str)-> None:
        self.static_dict[id]['name'] = value

    def upd_static_ctype(self, id: str, value: str)-> None:
        self.static_dict[id]['ctype'] = value
