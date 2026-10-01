from __future__ import annotations
import logging
from typing import Callable, Optional, Dict, Tuple

from serverish.base import Task
from serverish.messenger.msg_journal_pub import MsgJournalPublisher

from ob.comunication.nats_bus import rpc_request, rpc_subscribe
from ocaboxapi.telescopecomponent import TelescopeComponent, OcaBoxParam

logger = logging.getLogger(__name__.rsplit('.')[-1])


class Dome(TelescopeComponent):
    # INFO default values in param is only for class getting value e.g. Dome.slewing return default, but instance
    # return None

    azimuth = OcaBoxParam(default=0.0, doc="Dome azimuth")
    shutterstatus = OcaBoxParam(default=0, doc="Dome shutter status")
    slaved = OcaBoxParam(default=False, doc="Dome slawed to telescope")
    slewing = OcaBoxParam(default=False, doc="Dome is moving")
    slave_on = OcaBoxParam(default=False, doc="Slave to telescope on")
    atpark = OcaBoxParam(default=False, doc="Dome at park position")
    domefansrunning = OcaBoxParam(default=False, doc="Dome fans running")


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
        return await self.subscribe('azimuth', callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_shutterstatus(self) -> int:
        logger.debug(f'Getting dome shutterstatus from {self.tel_addr}')
        ret = await self.aget_value('shutterstatus')
        return ret

    async def asubscribe_shutterstatus(self, callback: Callable | None = None,
                                       time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing shutterstatus from {self.tel_addr}')
        return await self.subscribe('shutterstatus', callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

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
        return await self.subscribe('slaved', callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_slewing(self) -> bool:
        logger.debug(f'Getting dome slewing from {self.tel_addr}')
        ret = await self.aget_value('slewing')
        return ret

    async def asubscribe_slewing(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing slewing from {self.tel_addr}')
        return await self.subscribe('slewing', callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_atpark(self) -> bool:
        logger.debug(f'Getting dome atpark from {self.tel_addr}')
        ret = await self.aget_value('atpark')
        return ret

    async def asubscribe_atpark(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing dome atpark from {self.tel_addr}')
        return await self.subscribe('atpark', callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aput_slewtoazimuth(self, az: float) -> None:
        logger.debug(f'Putting slew to {self.tel_addr}')
        await self.aput_value('slewtoazimuth', Azimuth=az)

    async def aput_abortslew(self) -> None:
        logger.debug(f'Putting abortslew dome to {self.tel_addr}')
        await self.aput_value('abortslew')

    async def slave_to_telescope(self, tel_az: float, tolerance: float = 0.1) -> None:
        if self.azimuth:
            diff = tel_az - self.azimuth
            if self.slave_on:
                if (360 - tolerance) > abs(diff) > tolerance:
                    await self.aput_slewtoazimuth(tel_az)

    async def aput_park(self) -> None:
        logger.debug(f'Putting park dome to {self.tel_addr}')
        await self.aput_value('park')

    async def aput_dome_fans_turn_on(self) -> None:
        logger.debug(f'Putting dome ventilators on to {self.tel_addr}')
        await self.aput_value('domefansturnon')

    async def aput_fans_turn_off(self) -> None:
        logger.debug(f'Putting dome ventilators off to {self.tel_addr}')
        await self.aput_value('domefansturnoff')

    async def aget_dome_fans_running(self) -> bool:
        logger.debug(f'Getting dome ventilators are running from {self.tel_addr}')
        ret = await self.aget_value('domefansrunning')
        return ret

    async def asubscribe_dome_fans_running(self, callback: Optional[Callable] = None,
                                           time_of_data_tolerance: Optional[float] = None):
        logger.debug(f'Subscribing dome ventilators are running from {self.tel_addr}')
        return await self.subscribe('domefansrunning',
                                    callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aput_dome_follower_on(
            self, journal: Optional[MsgJournalPublisher] = None, timeout: float = 30
    ) -> bool:
        logger.debug(f'Putting dome follower on')
        dat, met = await rpc_request(
            subject=f'tic.rpc.{self.telescope.id}.dome.follower.on',
            data={},
            journal=journal,
            timeout=timeout
        )
        try:
            if dat is not None and dat['status'] == 'ok':
                return True
            else:
                return False
        except (LookupError, TypeError, ValueError):
            return False

    async def aput_dome_follower_off(
            self, journal: Optional[MsgJournalPublisher] = None, timeout: float = 30
    ) -> bool:
        logger.debug(f'Putting dome follower off')
        dat, met = await rpc_request(
            subject=f'tic.rpc.{self.telescope.id}.dome.follower.off',
            data={},
            journal=journal,
            timeout=timeout
        )
        try:
            if dat is not None and dat['status'] == 'ok':
                return True
            else:
                return False
        except (LookupError, TypeError, ValueError):
            return False

    async def aget_dome_follower_status(
            self, journal: Optional[MsgJournalPublisher] = None, timeout: float = 30
    ) -> Optional[Dict]:
        logger.debug(f'Getting dome follower state')
        dat, met = await rpc_request(
            subject=f'tic.rpc.{self.telescope.id}.dome.follower.state',
            data={},
            journal=journal,
            timeout=timeout
        )
        return dat

    async def asubscribe_dome_follower_status(
            self, callback: Callable, interval: float = 1,
            journal: Optional[MsgJournalPublisher] = None, timeout: float = 30
    ) -> Task:
        logger.debug(f'Subscribing dome follower state')
        return await rpc_subscribe(
            callback=callback,
            subject=f'tic.rpc.{self.telescope.id}.dome.follower.state',
            data={},
            interval=interval,
            journal=journal,
            timeout=timeout
        )
