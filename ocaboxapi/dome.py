from __future__ import annotations
import logging
from typing import Callable

from ocaboxapi.telescopecomponent import TelescopeComponent, OcaBoxParam

logger = logging.getLogger(__name__.rsplit('.')[-1])


class Dome(TelescopeComponent):
    azimuth = OcaBoxParam(default=0.0, doc="Dome azimuth")
    shutterstatus = OcaBoxParam(default=0, doc="Dome shutter status")
    slaved = OcaBoxParam(default=False, doc="Dome slawed to telescope")
    slewing = OcaBoxParam(default=False, doc="Dome is moving")

    shutter_status_to_code = {
        'open': 0,
        'closed': 1,
        'opening': 2,
        'closing': 3,
        'error': 4,
    }
    shutter_code_to_status = {v: k for k, v in shutter_status_to_code.items()}

    async def aget_az(self) -> float:
        logger.debug(f'Getting dome AZ from {self.tel_addr}')
        ret = await self.aget_value('azimuth')
        return ret

    async def asubscribe_az(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing AZ from {self.tel_addr}')
        return await self.subscribe('azimuth', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_shutterstatus(self) -> int:
        logger.debug(f'Getting dome shutterstatus from {self.tel_addr}')
        ret = await self.aget_value('shutterstatus')
        return ret

    async def asubscribe_shutterstatus(self, callback: Callable | None = None,
                                       time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing shutterstatus from {self.tel_addr}')
        return await self.subscribe('shutterstatus', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aput_openshutter(self):
        logger.debug(f'Putting openshutter to {self.tel_addr}')
        return await self.aput_value('openshutter')

    async def aput_closeshutter(self):
        logger.debug(f'Putting closeshutter to {self.tel_addr}')
        return await self.aput_value('closeshutter')


    async def aget_slaved(self) -> bool:
        logger.debug(f'Getting dome slaved from {self.tel_addr}')
        ret = await self.aget_value('slaved')
        return ret

    async def asubscribe_slaved(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing slaved from {self.tel_addr}')
        return await self.subscribe('slaved', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aget_slewing(self) -> bool:
        logger.debug(f'Getting dome slewing from {self.tel_addr}')
        ret = await self.aget_value('slewing')
        return ret

    async def asubscribe_slewing(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing slewing from {self.tel_addr}')
        return await self.subscribe('slewing', callback=callback, time_of_data_tolerance=time_of_data_tolerance)

    async def aput_abortslew(self):
        logger.debug(f'Putting abortslew to {self.tel_addr}')
        await self.aput_value('abortslew')



# class DomeOld(TelescopeComponentOld):
#     async def aget_az(self) -> float:
#         log.debug(f'Getting dome AZ from {self.tel_addr}')
#         ret = await self.get_async('azimuth')
#         return ret
#
#
#     async def asubscribe_az(self, callback: Callable|None = None, time_of_data_tolerance: float|None = None):
#         log.debug(f'Subscribing AZ from {self.tel_addr}')
#         await self._asubscribe('azimuth', callback=callback)
#
#     async def _asubscribe_new(self, addr:str, callback:Callable, sexagesimal: bool, sex_formatter: Callable):
#         """New version, which is going to use `ClientAPI.subscribe_with_callback (not working yet)"""
#         # TODO: @Ernest może `subscribe_with_callback` powinno się przemianować na `run_subscription_callbacks`
#         # TODO: i niech ma pętlę taką jak w exmaplu Twoim lub w `_asubscribe` poniżej?
#         # TODO: W sumie o to chodzi żeby wywalać w Clienta kod niespecyficzny dla użytkownika zmiennych etc...
#         def fmt_callback(x: float, sex: bool, formatter: Callable, callback: Callable):
#             """Optionally formats sexagesimal before calling user callback"""
#             callback(formatter(x) if sex else x)
#
#         res = await self.telescope.observatory.client.subscribe_with_callback(
#             f'{self.tel_addr}.mount.{addr}',
#             callback_method=lambda x: fmt_callback(x, sex=sexagesimal, formatter=sex_formatter, callback=callback),
#             delay=0.2
#         )
#         self.subscriptions.append(res)
#
#     async def _asubscribe(self, addr:str, callback:Callable):
#         """Like in example version, using `ClientAPI.subscribe`"""
#         cq = await self.telescope.observatory.client.subscribe(f'{self.tel_addr}.dome.{addr}',
#                                                                delay=0.1,
#                                                                time_of_data_tolerance=0.1
#                                                                )
#         cq.start()
#         try:
#             while True:
#                 result = await cq.get_response()
#                 log.debug(f'Got dome.{addr} from {self.tel_addr}')
#                 if result and result[0].value:
#                     callback(result[0].value.v)
#         except CommunicationRuntimeError as e:
#             log.error('Communication error: %s', e)
#         finally:
#             log.info(f'Stopping {addr} subscription...')
#             cq.stop()
#
