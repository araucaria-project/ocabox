import asyncio
import logging

import zmq
from zmq.asyncio import Context, Poller

logger = logging.getLogger(__name__)


class ValueRouter:
    __name__ = 'ValueRouter'

    def __init__(self, name: str = None, port: int = 5559):
        self.name = name if name else ValueRouter.__name__
        # OMQ
        self.context = Context()  # TODO Context.instance() ? jeden czy wiele kontekstów?
        self.frontend = self.context.socket(zmq.ROUTER)
        self.frontend.bind(f"tcp://*:{port}")
        # Tasks
        self._main_task_name = f'{self.name}_main_task'
        self._main_task = None
        self._ping_task_name = f'{self.name}_ping_task'
        self._ping_task = None
        self._message_task_name = f'{self.name}_message_task'
        self._message_tasks = []
        self._stop_task_name = f'{self.name}_stop_task'
        self._stop_task = None
        # async loop
        self._current_loop = None  # remember async loop with router working

    async def _ping(self):
        while True:
            await asyncio.sleep(1)
            logger.info(f'{self.name}: Listening...')

    # w przyszłości zmienić to na pobieranie warotości z teleskopu
    async def my_coroutine(self):
        await asyncio.sleep(2)
        print("My Coroutine 2s")

    async def _send_back(self, message):
        await self.my_coroutine()
        self.frontend.send_multipart([message.result()[0], b'', b"world"])
        try:
            task = asyncio.current_task()
            self._message_tasks.remove(task)
        except ValueError:
            logger.error('Unexpected ValueError. Can not remove task from task list.')

    async def _main(self):
        poller = Poller()
        poller.register(self.frontend, zmq.POLLIN)
        i = 0
        while True:
            i += 1
            events = await poller.poll()

            if self.frontend in dict(events):
                message = self.frontend.recv_multipart()
                print(f'get message {message.result()} ')

                # await self.frontend.send_multipart([message.result()[0], b'', b"world"])
                # await self.send_back(message)
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
        canceled as this may lead to incorrect niepoprawnego wyłączenia rutera..
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
                self._stop_task = loop.create_task(self._wait_for_stop(), name=self._stop_task_name)
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
        else:
            logger.info(f'Can not find async loop for this router. Probably this router was newer started.')
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
