from typing import Dict


class PlanStatus:

    def __init__(self, telescope: 'Telescope', info_callback) -> None:
        self.telescope = telescope
        self.info_callback = info_callback
        self.plan_static_dict: Dict = {}
        self.time_dict: Dict = {}
        self.status_dict: Dict = {}
        super().__init__()

    async def add_to_static_list(self, id: str, sequence_dict: Dict,
                                 started: bool, done: bool, skipped: bool) -> None:
        self.plan_static_dict[id] = sequence_dict
        self.plan_status[id] = {'started': started, 'done': done, 'skipped': skipped}
        self.plan_time[id] = {}

    async def reset(self):
        self.plan_static_dict = {}
        self.plan_time = {}
        self.plan_status = {}

    async def send_all_to_nats(self):
        pass

    async def send_to_nats(self):
        pass

    async def upd_status(self, id: str, field: str, value: bool):
        try:
            self.status_dict[id][field] = value
        except KeyError:
            pass
        self.info_callback['stream_1'](self.status_dict)
