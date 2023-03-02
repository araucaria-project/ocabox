from __future__ import annotations
import logging
from typing import Union, Callable
from ocaboxapi.telescopecomponent import TelescopeComponent, OcaBoxParam


logger = logging.getLogger(__name__.rsplit('.')[-1])


class Mount(TelescopeComponent):
    rightascension = OcaBoxParam(default=0.0, doc="Mount rightascension")
    declination = OcaBoxParam(default=0.0, doc="Mount declination")
    azimuth = OcaBoxParam(default=0.0, doc="Mount azimuth")
    altitude = OcaBoxParam(default=0.0, doc="Mount altitude")
    athome = OcaBoxParam(default=False, doc="Mount is athome")
    atpark = OcaBoxParam(default=False, doc="Mount is atpark")
    slewing = OcaBoxParam(default=False, doc="Mount is slewing")
    tracking = OcaBoxParam(default=False, doc="Mount is tracking")

    async def aget_ra(self) -> float:
        logger.debug(f'Getting mount RA from {self.tel_addr}')
        ret = await self.aget_value('rightascension')
        return ret

    async def asubscribe_ra(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing mount RA from {self.tel_addr}')
        return await self.subscribe('rightascension', callback=callback, time_of_data_tolerance=time_of_data_tolerance)


    """async def aput_slewtora(self, ra: float):
        logger.debug(f'Putting slew to {self.tel_addr}')
        await self.aput_value('slewtora', Rightascension=ra)"""



    async def aget_dec(self) -> float:
        logger.debug(f'Getting mount DEC from {self.tel_addr}')
        ret = await self.aget_value('declination')
        return ret

    async def asubscribe_dec(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing mount DEC from {self.tel_addr}')
        return await self.subscribe('declination', callback=callback, time_of_data_tolerance=time_of_data_tolerance)



    async def aget_az(self) -> float:
        logger.debug(f'Getting mount AZ from {self.tel_addr}')
        ret = await self.aget_value('azimuth')
        return ret

    async def asubscribe_az(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing mount AZ from {self.tel_addr}')
        return await self.subscribe('azimuth', callback=callback, time_of_data_tolerance=time_of_data_tolerance)




    async def aget_alt(self) -> float:
        logger.debug(f'Getting mount ALT from {self.tel_addr}')
        ret = await self.aget_value('altitude')
        return ret

    async def asubscribe_alt(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing mount ALT from {self.tel_addr}')
        return await self.subscribe('altitude', callback=callback, time_of_data_tolerance=time_of_data_tolerance)



    async def aget_athome(self) -> float:
        logger.debug(f'Getting mount is athome from {self.tel_addr}')
        ret = await self.aget_value('athome')
        return ret

    async def asubscribe_athome(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing mount is athome from {self.tel_addr}')
        return await self.subscribe('athome', callback=callback, time_of_data_tolerance=time_of_data_tolerance)



    async def aget_atpark(self) -> float:
        logger.debug(f'Getting mount is atpark from {self.tel_addr}')
        ret = await self.aget_value('atpark')
        return ret

    async def asubscribe_atpark(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing mount is atpark from {self.tel_addr}')
        return await self.subscribe('atpark', callback=callback, time_of_data_tolerance=time_of_data_tolerance)



    async def aget_slewing(self) -> float:
        logger.debug(f'Getting mount is slewing from {self.tel_addr}')
        ret = await self.aget_value('slewing')
        return ret

    async def asubscribe_slewing(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing mount is slewing from {self.tel_addr}')
        return await self.subscribe('slewing', callback=callback, time_of_data_tolerance=time_of_data_tolerance)



    async def aget_tracking(self) -> float:
        logger.debug(f'Getting mount is tracking from {self.tel_addr}')
        ret = await self.aget_value('tracking')
        return ret

    async def asubscribe_tracking(self, callback: Callable | None = None, time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing mount is tracking from {self.tel_addr}')
        return await self.subscribe('tracking', callback=callback, time_of_data_tolerance=time_of_data_tolerance)







    """    def slew(self):
        pass

    async def aget_ra(self, sexagesimal: bool = False) -> Union[float, str]:
        log.debug(f'Getting RA from {self.tel_addr}')
        ret = await self.get_async('rightascension')
        return fmt_ra(ret, sexagesimal=sexagesimal)

    async def aget_dec(self, sexagesimal: bool = False) -> Union[float, str]:
        log.debug(f'Getting DEC from {self.tel_addr}')
        ret = await self.get_async('declination')
        return fmt_dec(ret, sexagesimal=sexagesimal)

    async def aget_az(self, sexagesimal: bool = False) -> Union[float, str]:
        log.debug(f'Getting AZ from {self.tel_addr}')
        ret = await self.get_async('azimuth')
        return fmt_az(ret, sexagesimal=sexagesimal)

    async def aget_alt(self, sexagesimal: bool = False) -> Union[float, str]:
        log.debug(f'Getting ALT from {self.tel_addr}')
        ret = await self.get_async('altitude')
        return fmt_alt(ret, sexagesimal=sexagesimal)

    async def asubscribe_ra(self, callback:Callable, sexagesimal: bool = False):
        log.debug(f'Subscribing RA from {self.tel_addr}')
        await self._asubscribe_coo_formatted('rightascension', callback=callback,
                                             sexagesimal=sexagesimal, sex_formatter=fmt_ra)

    async def asubscribe_dec(self, callback:Callable, sexagesimal: bool = False):
        log.debug(f'Subscribing DEC from {self.tel_addr}')
        await self._asubscribe_coo_formatted('declination', callback=callback,
                                             sexagesimal=sexagesimal, sex_formatter=fmt_dec)

    async def asubscribe_az(self, callback:Callable, sexagesimal: bool = False):
        log.debug(f'Subscribing AZ from {self.tel_addr}')
        await self._asubscribe_coo_formatted('azimuth', callback=callback,
                                             sexagesimal=sexagesimal, sex_formatter=fmt_az)

    async def asubscribe_alt(self, callback:Callable, sexagesimal: bool = False):
        log.debug(f'Subscribing ALT from {self.tel_addr}')
        await self._asubscribe_coo_formatted('altitude', callback=callback,
                                             sexagesimal=sexagesimal, sex_formatter=fmt_alt)

    # TODO: Remove sexadecimal and formatting at all from here
    async def _asubscribe_new(self, addr:str, callback:Callable, sexagesimal: bool, sex_formatter: Callable):
        New version, which is going to use `ClientAPI.subscribe_with_callback (not working yet)
        # TODO: @Ernest może `subscribe_with_callback` powinno się przemianować na `run_subscription_callbacks`
        # TODO: i niech ma pętlę taką jak w exmaplu Twoim lub w `_asubscribe` poniżej?
        # TODO: W sumie o to chodzi żeby wywalać w Clienta kod niespecyficzny dla użytkownika zmiennych etc...
        def fmt_callback(x: float, sex: bool, formatter: Callable, callback: Callable):
            Optionally formats sexagesimal before calling user callback
            callback(formatter(x) if sex else x)

        res = await self.telescope.observatory.client.subscribe_with_callback(
            f'{self.tel_addr}.mount.{addr}',
            callback_method=lambda x: fmt_callback(x, sex=sexagesimal, formatter=sex_formatter, callback=callback),
            delay=0.2
        )
        self.subscriptions.append(res)

    async def _asubscribe_coo_formatted(self, addr:str, callback:Callable, sexagesimal: bool, sex_formatter: Callable):
        Lik in example version, using `ClientAPI.subscribe`
        def fmt_callback(x: float, sex: bool, formatter: Callable, callback: Callable):
            Optionally formats sexagesimal before calling user callback
            callback(formatter(x, sex))

        cq = await self.telescope.observatory.client.subscribe(f'{self.tel_addr}.mount.{addr}',
                                                               delay=0.3,
                                                               time_of_data_tolerance=0.2
                                                               )
        cq.start()
        try:
            while True:
                result = await cq.get_response()
                log.debug(f'Got {addr} from {self.tel_addr}')
                if result and result[0].value:
                    fmt_callback(result[0].value.v, sex=sexagesimal, formatter=sex_formatter, callback=callback)
        except CommunicationRuntimeError as e:
            log.error('Communication error: %s', e)
        finally:
            log.info(f'Stopping {addr} subscription...')
            cq.stop()
        """

