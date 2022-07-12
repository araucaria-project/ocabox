import asyncio
import logging
from typing import List

import zmq
from zmq.asyncio import Context, Poller

from ob.comunication.base_communication_object import BaseCommunicationObject
from ob.ob_config import SingletonConfig
from ob.comunication.message_serializer import MessageSerializer
from ob.comunication.base_request_solver import BaseRequestSolver

logger = logging.getLogger(__name__)


class Router(BaseCommunicationObject):
    DEFAULT_NAME = 'DefaultRouter'

    def __init__(self, request_solver: BaseRequestSolver or None, name: str = None, port: int = SingletonConfig.
                 get_config()['router'][DEFAULT_NAME]['port'].get(), **kwargs):
        super().__init__(name=name, **kwargs)
        # request solver
        self.request_solver: BaseRequestSolver or None = request_solver
        # OMQ
        self.context = Context()  # TODO One for all router (Context.instance()) or one for everyone router (Context())?
        self.frontend = self.context.socket(zmq.ROUTER)
        self.frontend.bind(f"{self._get_cfg('protocol', 'tcp')}://{self._get_cfg('url', '*')}:{port}")
        # Tasks
        self._main_task_name = f'{self.name}_main_task'
        self._main_task = None
        self._ping_task_name = f'{self.name}_ping_task'
        self._ping_task = None
        self._message_task_name = f'{self.name}_message_task'
        self._message_tasks = []
        # self._stop_task_name = f'{self.name}_stop_task'
        self._stop_task = None
        # async loop
        self._current_loop = None  # remember async loop with router working

    async def _ping(self):
        while True:
            await asyncio.sleep(1)
            logger.info(f'{self.name}: Listening...')

    async def _solve_request(self, data: List[dict]) -> List[dict] or None:
        answer = None
        if self.request_solver:
            answer = await self.request_solver.get_answer(data)
        else:
            logger.error(f"Can not find request solver. The router can't send response to client.")
        return answer

    @staticmethod
    def _open_envelope(multipart):
        if len(multipart) < 3:
            logger.error(f'Wrong multipart because is shorter than 3')
            raise ValueError
        target = multipart[0]
        empty = multipart[1]
        data = multipart[2:]
        if not target:
            logger.error(f'Wrong port address in multipart.')
            raise ValueError
        if empty:
            logger.error(f'Empty byte in multipart is not empty')
            raise ValueError
        if not data:
            logger.error(f'No data in multipart')
            raise ValueError
        messages = []
        for d in data:
            messages.append(MessageSerializer.unpack_b(d))
        return target, messages

    @staticmethod
    def _pack_to_envelope(target: bytes, data: list):
        if not target:
            logger.error(f'Wrong port address for multipart.')
            raise ValueError
        if not data:
            data = [{}]
            logger.error(f'No data to send. Task send empty bit to client. ')

        envelope = [target, b'']
        for d in data:
            if not isinstance(d, dict) or not MessageSerializer.is_correct(d):
                raise ValueError
            envelope.append(MessageSerializer.pack_b(d))
        return envelope

    async def _send_back(self, message):
        def remove_task_inner():
            try:
                task = asyncio.current_task()
                self._message_tasks.remove(task)
            except ValueError:
                logger.error('Unexpected ValueError. Can not remove task from task list.')

        try:
            target, data_list = self._open_envelope(message)
        except ValueError:
            # Don't answer for incorrect requests. Close task.
            remove_task_inner()
            return
        try:
            answer = await self._solve_request(data_list)
        except ValueError:
            # Obsolete and shouldn't have happened
            # Don't answer for incorrect requests. Close task.
            remove_task_inner()
            logger.error(f"Router encountered a ValueError when try to solve request. Solver handled the exception "
                         f"incorrectly")
            return
        except asyncio.CancelledError:
            # remove canceled task from list
            remove_task_inner()
            raise
        except Exception as e:
            # shouldn't have happened
            remove_task_inner()
            logger.error(f"Router encountered an unexpected error while generating response. Task was closed and "
                         f"don't send response. Error message: {str(e)}")
            return
        try:
            answer_envelope = Router._pack_to_envelope(target, answer)
        except ValueError:
            # Don't answer for incorrect requests. Close task.
            remove_task_inner()
            return
        self.frontend.send_multipart(answer_envelope)
        remove_task_inner()

    async def _main(self):
        # Poller() is only necessary for multiple sockets. Has been added here with thoughts about the future.
        poller = Poller()
        poller.register(self.frontend, zmq.POLLIN)
        i = 0
        while True:
            i += 1
            events = await poller.poll()
            if self.frontend in dict(events):
                message = await self.frontend.recv_multipart()
                task = asyncio.create_task(self._send_back(message), name=self._message_task_name)
                self._message_tasks.append(task)

    def _start_main_task(self):
        for task in asyncio.all_tasks(self._current_loop):
            if task.get_name().startswith(self.name):
                logger.error(f'Router name conflict. Could not start router {self.name} because a router with that '
                             f'name is already running in the async loop.')
                raise ValueError
        logger.info('start main task')
        self._main_task = self._current_loop.create_task(self._main(), name=self._main_task_name)
        logger.info('start ping task')
        self._ping_task = self._current_loop.create_task(self._ping(), name=self._ping_task_name)

    def start(self, loop=None):
        """
        This method starts the router's event loop on the asynchronous task and runs it in the current async loop.
        It is possible to pass a previously created loop as an argument of the method. Otherwise, the currently
        running loop is downloaded.
        :param loop: async loop
        :return:
        """
        if not loop:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:  # 'RuntimeError: There is no current event loop...'
                loop = None
        if loop and not loop.is_closed():
            if not self._current_loop:
                self._current_loop = loop  # remember async loop with router working
            if not self.is_stopped():
                logger.error('Can not start router because is already workng.')
                return
            self._current_loop = loop  # assign again after checking 'is_stopped()'
            self._start_main_task()
            logger.info('Router is running')
        else:
            logger.error('Can not start router because async loop not found.')

    async def main_coroutine(self):
        """
        This method is coroutine responsible for starting the server and waiting for it to finish running and then
        shutting down all tasks if they were not terminated earlier. Warning! this method catches error
        asyncio.CancelledError and shuts down the server securely. Canceling it turns off the entire server.
        :return:
        """
        if not self.is_stopped():
            logger.error('Can not start router because is already workng.')
            return
        self._current_loop = asyncio.get_running_loop()  # this is called from loop so it is not possible to loop was
        # closed and throw exception
        self._start_main_task()
        mt = self._main_task  # keep the instance when await because self param can be set to None during waiting
        pt = self._ping_task  # keep the instance when await because self param can be set to None during waiting
        try:
            await mt
        except asyncio.CancelledError:
            # catch canceled main task and cancel all server task safety
            pass
        finally:
            # Stop the router after finishing main tasks, tasks are endless loops so only in case of any errors you may
            # need this piece of code.
            self.stop()
            await self.wait_for_stop()
            logger.info(f'Main coroutine for router {self.name} was end')

    def _stop_router_tasks(self):
        logger.info('cancelling router tasks...')
        task_count = 0
        loop = self._current_loop
        for task in asyncio.all_tasks(loop):
            if task is self._main_task and not task.cancelled():
                logger.info('cancel main task')
                task.cancel()
                task_count += 1
            if task is self._ping_task and not task.cancelled():
                logger.info('cancel ping task')
                task.cancel()
                task_count += 1
            if task.get_name() is self._message_task_name:
                logger.info('cancel client answer task')
                task.cancel()
                task_count += 1
        if task_count > 0:
            logger.info(f'Cancel {task_count} tasks. They exiting in a minute...')
        else:
            logger.warning(f'Can not find any task for cancel. Tasks are already canceled or finished')

    def stop(self):
        """
        This method is responsible for canceling all router tasks and then creating a special task that is to wait
        for all canceled previously to close and the server to shut down properly. shutdown job should never be
        canceled as this may lead to incorrect shutdown of the router.

        :return:
        """
        if self.is_stopped():
            logger.info(f'The router {self.name} is already stop')
            return
        logger.info('Stopping router...')
        if self._current_loop and not self._current_loop.is_closed():
            loop = self._current_loop
        else:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:  # 'RuntimeError: There is no current event loop...'
                logger.warning('Can not stop router because the running loop not found.')
                loop = None
        if loop:
            if self._stop_task:
                logger.info(f'Router {self.name} is already stopping now, please wait a moment for stopped.')
            else:
                self._stop_router_tasks()
                self._stop_task = loop.create_task(self._wait_for_stop())
        else:
            # TODO It should never happened. However, if it does, need to think about restarting the loop and end tasks
            logger.error(f'Router {self.name} is not stopped and can not find running loop. Something go wrong')
            raise RuntimeError

    async def _wait_for_stop(self):
        # --------------------------------- stop main -----------------------------------------------------
        if self._main_task:
            try:
                await self._main_task
            except asyncio.CancelledError:
                # here is checking if stop task was canceled, in normal situation it don't and should waiting for rest
                # of router task
                if self._stop_task.cancelled():
                    logger.error(f'Stop task for router {self.name} was canceled before cancel all router tasks')
                    raise asyncio.CancelledError
            if self._main_task not in asyncio.all_tasks():
                self._main_task = None
                logger.info(f'Main task for router named {self.name} stopped.')

        # --------------------------------- stop ping ----------------------------------------------------
        if self._ping_task:
            try:
                await self._ping_task
            except asyncio.CancelledError:
                # here is checking if stop task was canceled, in normal situation it don't and should waiting for rest
                # of router task
                if self._stop_task.cancelled():
                    logger.error(f'Stop task for router {self.name} was canceled before cancel all router tasks')
                    raise asyncio.CancelledError
            if self._ping_task not in asyncio.all_tasks():
                self._ping_task = None
                logger.info(f'Ping task for router named {self.name} stopped.')
            else:
                logger.error(f'Stop task for router {self.name} was canceled before cancel all router tasks')

        # --------------------------------- stop message ---------------------------------------------------
        for task in self._message_tasks:
            try:
                await task
            except asyncio.CancelledError:
                # here is checking if stop task was canceled, in normal situation it don't and should waiting for rest
                # of router task
                if self._stop_task.cancelled():
                    logger.error(f'Stop task for router {self.name} was canceled before cancel message task')
                    raise asyncio.CancelledError
            if task in asyncio.all_tasks():
                logger.info(f'Task {task.get_name} for router named {self.name} stopped.')
        self._message_tasks = []

        self._stop_task = None
        logger.info(f'Router {self.name} was stopped.')

    async def wait_for_stop(self):
        """
        This method is a corutin that waits for the server to shutdown properly after calling the 'stop()' method.
        Additionally, it checks the server shutdown process. Instead, you can use the 'get_stop_task()' method which
        returns a job instance to shutdown the router and wait for it to complete but it is not recommended.
        :return:
        """
        if self.is_stopped():
            logger.info(f'The router {self.name} is already stopped')
            return
        stop_task = self.get_stop_task()
        if not stop_task:
            logger.warning(f'The router {self.name} is running and a stop has not been initiated try run first .stop() '
                           f'method')
            return
        try:
            await stop_task
        except asyncio.CancelledError:
            logger.error(f'the job waiting for shutting down the router {self.name} was not completed correctly. '
                         f'The router may be canceled but not terminated.')
        if not self.is_stopped():
            logger.error(f'An attempt to turn off the router has been unsuccessful')
            raise RuntimeError  # probably newer happen

    def is_stopped(self):
        """
        This method returns true if the router is stopped.
        :return: true if router is stopped or false if don't.
        """
        if self._current_loop:
            tasks = [self._main_task, self._ping_task, self._message_tasks, self._stop_task]
            for t in tasks:
                if t and t in asyncio.all_tasks(self._current_loop):
                    return False
        # else:
            # logger.info(f'Can not find async loop for this router. Probably this router was newer started.')
        return True

    def get_stop_task(self):
        """
        This method returns an instance of the task that waits for the router to shut down correctly, provided the
        'stop()' method has been run beforehand. If the stop () method has not been run before or the router has
        already been shut down properly, None will be returned. It is recommended to use the 'wait_for_stop()' instead
        this method.
        :return: asyncio task
        """
        return self._stop_task

    def __del__(self):
        if not self.is_stopped():
            self.stop()
        self.context.destroy()  # without this zmq not close socket when router is destroy
