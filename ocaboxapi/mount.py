import logging
from typing import Union, Callable

from ob.comunication.comunication_error import CommunicationRuntimeError

from ocaboxapi.formatter import fmt_hourangle, fmt_ra, fmt_dec, fmt_az, fmt_alt
from ocaboxapi.telescopecomponent import TelescopeComponentOld

log = logging.getLogger(__name__.rsplit('.')[-1])

class Mount(TelescopeComponentOld):
    def slew(self):
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
        """New version, which is going to use `ClientAPI.subscribe_with_callback (not working yet)"""
        # TODO: @Ernest może `subscribe_with_callback` powinno się przemianować na `run_subscription_callbacks`
        # TODO: i niech ma pętlę taką jak w exmaplu Twoim lub w `_asubscribe` poniżej?
        # TODO: W sumie o to chodzi żeby wywalać w Clienta kod niespecyficzny dla użytkownika zmiennych etc...
        def fmt_callback(x: float, sex: bool, formatter: Callable, callback: Callable):
            """Optionally formats sexagesimal before calling user callback"""
            callback(formatter(x) if sex else x)

        res = await self.telescope.observatory.client.subscribe_with_callback(
            f'{self.tel_addr}.mount.{addr}',
            callback_method=lambda x: fmt_callback(x, sex=sexagesimal, formatter=sex_formatter, callback=callback),
            delay=0.2
        )
        self.subscriptions.append(res)

    async def _asubscribe_coo_formatted(self, addr:str, callback:Callable, sexagesimal: bool, sex_formatter: Callable):
        """Lik in example version, using `ClientAPI.subscribe`"""
        def fmt_callback(x: float, sex: bool, formatter: Callable, callback: Callable):
            """Optionally formats sexagesimal before calling user callback"""
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

