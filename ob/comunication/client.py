import asyncio
import logging

import zmq
from zmq.asyncio import Context, Poller

from ob.comunication.base_communication_object import BaseCommunicationObject
from ob.comunication.base_request_solver import BaseRequestSolver
from ob.ob_config import SingletonConfig

logger = logging.getLogger(__name__)


class Client(BaseCommunicationObject):
    DEFAULT_NAME = 'DefaultClient'

    def __init__(self, request_solver: BaseRequestSolver or None, name: str = None, port: int = SingletonConfig.
                 get_config()['router'][DEFAULT_NAME]['port'].get(), **kwargs):
        super().__init__(name=name, **kwargs)

        # request solver
        self.request_solver: BaseRequestSolver or None = request_solver
        # OMQ
        self.context = Context()  # TODO One for all router (Context.instance()) or one for everyone router (Context())?
        self.frontend = self.context.socket(zmq.DEALER)
        self.frontend.bind(f"{self._get_cfg('protocol', 'tcp')}://{self._get_cfg('url', 'localhost')}:{port}")

    async def _main(self):
        poller = Poller()
        poller.register(self.frontend, zmq.POLLIN)
        i = 0
        while True:
            i += 1
            events = await poller.poll()
            if self.frontend in dict(events):
                message = await self.frontend.recv_multipart()
                # task = asyncio.create_task(self._send_back(message), name=self._message_task_name)
                # self._message_tasks.append(task)
