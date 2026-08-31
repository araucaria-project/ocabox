from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional

from ocaboxapi.telescopecomponent import TelescopeComponent, OcaBoxParam

logger = logging.getLogger(__name__.rsplit('.')[-1])


class MirrorCell(TelescopeComponent):
    """M1 mirror cell (active collimation) — three support motors.

    Read-back is served by the server-side ``mirrorcell`` interface
    (ocabox-server ≥ 2.4.0; which hardware implementation serves it is the
    server's concern): aggregate reads plus per-motor scalars
    ``motor<N>{position,status,statustext}``. Positions are **metres** at the
    API level (µm-scale in practice, e.g. ``-9.63e-05`` = −96.3 µm); µm
    formatting belongs to the consumer (CLI/FITS/Grafana).

    Error model (server contract): a motor fault raises ``OcaboxDeviceError``
    (server code 4009, carrying the device status code in ``device_errno``) on
    every *value* read — ``positions``, ``atsetpoint``, ``moving``,
    ``motor<N>position`` (each only for its own motor) — while *status* reads
    (``mirrorcellstatus``, ``motorstatuses``, ``motorstatustexts``,
    ``motor<N>status``, ``motor<N>statustext``) stay readable: the status enum
    is the fault channel. A telescope without the subsystem (e.g. wk06)
    raises server code 2002 CRITICAL — permanent, a SERVICE-policy subscriber
    stops instead of retrying; ``available`` stays a never-raising capability
    probe.

    ⚠️ The movement/stop commands are unit-tested end to end but have never
    been commanded on real hardware (supervised test pending, see the M1
    collimation project board). Until it passes, no script or service may
    move the mirror cell.
    """

    #: Motors per cell; per-motor indices are 0…MOTOR_COUNT-1 (part of the interface contract).
    MOTOR_COUNT = 3

    available = OcaBoxParam(default=False, doc="Mirror cell present on this telescope (capability probe)")
    mirrorcellstatus = OcaBoxParam(default={}, doc="Raw device status dict — the diagnostic view")
    positions = OcaBoxParam(default=[], doc="[m] Motor positions ordered by motor index")
    motorstatuses = OcaBoxParam(default=[], doc="Motor status codes ordered by motor index")
    motorstatustexts = OcaBoxParam(default=[], doc="Motor status names ordered by motor index")
    atsetpoint = OcaBoxParam(default=False, doc="True when every motor holds its commanded position")
    moving = OcaBoxParam(default=False, doc="True while any motor is in motion")
    motor0position = OcaBoxParam(default=0.0, doc="[m] Motor 0 position")
    motor1position = OcaBoxParam(default=0.0, doc="[m] Motor 1 position")
    motor2position = OcaBoxParam(default=0.0, doc="[m] Motor 2 position")
    motor0status = OcaBoxParam(default=0, doc="Motor 0 status code")
    motor1status = OcaBoxParam(default=0, doc="Motor 1 status code")
    motor2status = OcaBoxParam(default=0, doc="Motor 2 status code")
    motor0statustext = OcaBoxParam(default='', doc="Motor 0 status name")
    motor1statustext = OcaBoxParam(default='', doc="Motor 1 status name")
    motor2statustext = OcaBoxParam(default='', doc="Motor 2 status name")

    # --- aggregate reads -----------------------------------------------------

    async def aget_available(self, time_of_data_tolerance: float | None = None) -> bool:
        logger.debug(f'Getting mirrorcell available from {self.tel_addr}')
        return await self.aget_value('available', time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_available(self, callback: Optional[Callable] = None,
                                   time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing mirrorcell available from {self.tel_addr}')
        return await self.subscribe('available', callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_mirrorcellstatus(self, time_of_data_tolerance: float | None = None) -> Dict:
        logger.debug(f'Getting mirrorcellstatus from {self.tel_addr}')
        return await self.aget_value('mirrorcellstatus', time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_mirrorcellstatus(self, callback: Optional[Callable] = None,
                                          time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing mirrorcellstatus from {self.tel_addr}')
        return await self.subscribe('mirrorcellstatus', callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_positions(self, time_of_data_tolerance: float | None = None) -> List[float]:
        logger.debug(f'Getting mirrorcell positions from {self.tel_addr}')
        return await self.aget_value('positions', time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_positions(self, callback: Optional[Callable] = None,
                                   time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing mirrorcell positions from {self.tel_addr}')
        return await self.subscribe('positions', callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_motorstatuses(self, time_of_data_tolerance: float | None = None) -> List[int]:
        logger.debug(f'Getting mirrorcell motorstatuses from {self.tel_addr}')
        return await self.aget_value('motorstatuses', time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_motorstatuses(self, callback: Optional[Callable] = None,
                                       time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing mirrorcell motorstatuses from {self.tel_addr}')
        return await self.subscribe('motorstatuses', callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_motorstatustexts(self, time_of_data_tolerance: float | None = None) -> List[str]:
        logger.debug(f'Getting mirrorcell motorstatustexts from {self.tel_addr}')
        return await self.aget_value('motorstatustexts', time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_motorstatustexts(self, callback: Optional[Callable] = None,
                                          time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing mirrorcell motorstatustexts from {self.tel_addr}')
        return await self.subscribe('motorstatustexts', callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_atsetpoint(self, time_of_data_tolerance: float | None = None) -> bool:
        logger.debug(f'Getting mirrorcell atsetpoint from {self.tel_addr}')
        return await self.aget_value('atsetpoint', time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_atsetpoint(self, callback: Optional[Callable] = None,
                                    time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing mirrorcell atsetpoint from {self.tel_addr}')
        return await self.subscribe('atsetpoint', callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_moving(self, time_of_data_tolerance: float | None = None) -> bool:
        logger.debug(f'Getting mirrorcell moving from {self.tel_addr}')
        return await self.aget_value('moving', time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_moving(self, callback: Optional[Callable] = None,
                                time_of_data_tolerance: float | None = None):
        logger.debug(f'Subscribing mirrorcell moving from {self.tel_addr}')
        return await self.subscribe('moving', callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    # --- per-motor reads (one value per telemetry subject) -------------------

    async def aget_motor_position(self, index: int,
                                  time_of_data_tolerance: float | None = None) -> float:
        """[m] Position of one motor; faults (4009) only on its own motor."""
        param = self._motor_param(index, 'position')
        logger.debug(f'Getting mirrorcell {param} from {self.tel_addr}')
        return await self.aget_value(param, time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_motor_position(self, index: int, callback: Optional[Callable] = None,
                                        time_of_data_tolerance: float | None = None):
        param = self._motor_param(index, 'position')
        logger.debug(f'Subscribing mirrorcell {param} from {self.tel_addr}')
        return await self.subscribe(param, callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_motor_status(self, index: int,
                                time_of_data_tolerance: float | None = None) -> int:
        """Status code of one motor; stays readable while the motor is faulted."""
        param = self._motor_param(index, 'status')
        logger.debug(f'Getting mirrorcell {param} from {self.tel_addr}')
        return await self.aget_value(param, time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_motor_status(self, index: int, callback: Optional[Callable] = None,
                                      time_of_data_tolerance: float | None = None):
        param = self._motor_param(index, 'status')
        logger.debug(f'Subscribing mirrorcell {param} from {self.tel_addr}')
        return await self.subscribe(param, callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    async def aget_motor_statustext(self, index: int,
                                    time_of_data_tolerance: float | None = None) -> str:
        """Status name of one motor; stays readable while the motor is faulted."""
        param = self._motor_param(index, 'statustext')
        logger.debug(f'Getting mirrorcell {param} from {self.tel_addr}')
        return await self.aget_value(param, time_of_data_tolerance=time_of_data_tolerance)

    async def asubscribe_motor_statustext(self, index: int, callback: Optional[Callable] = None,
                                          time_of_data_tolerance: float | None = None):
        param = self._motor_param(index, 'statustext')
        logger.debug(f'Subscribing mirrorcell {param} from {self.tel_addr}')
        return await self.subscribe(param, callback=callback,
                                    time_of_data_tolerance=time_of_data_tolerance)

    def _motor_param(self, index: int, field: str) -> str:
        # The server address space has exactly motor0..motor<MOTOR_COUNT-1>;
        # anything else is a client-side programming error, not a device state.
        if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < self.MOTOR_COUNT:
            raise ValueError(f'Mirror-cell motor index must be 0..{self.MOTOR_COUNT - 1}, got {index!r}')
        return f'motor{index}{field}'

    # --- commands -------------------------------------------------------------
    # ⚠️ Never commanded on real hardware yet — see the class docstring.

    async def amove_all_motors_to(self, positions: List[float]) -> None:
        """Move all motors to absolute ``positions`` (list of MOTOR_COUNT floats, metres)."""
        logger.debug(f'Putting mirrorcell moveallmotorsto {positions} in {self.tel_addr}')
        await self.aput_value('moveallmotorsto', Positions=positions)

    async def amove_all_motors_offset(self, offsets: List[float]) -> None:
        """Move all motors by relative ``offsets`` (list of MOTOR_COUNT floats, metres)."""
        logger.debug(f'Putting mirrorcell moveallmotorsoffset {offsets} in {self.tel_addr}')
        await self.aput_value('moveallmotorsoffset', Offsets=offsets)

    async def amove_one_motor_offset(self, index: int, offset: float) -> None:
        """Move motor ``index`` (0…MOTOR_COUNT-1) by a relative ``offset`` (metres)."""
        logger.debug(f'Putting mirrorcell moveonemotoroffset motor {index} by {offset} in {self.tel_addr}')
        await self.aput_value('moveonemotoroffset', Index=index, Offset=offset)

    async def astop_one_motor(self, index: int) -> None:
        """Stop motor ``index`` (0…MOTOR_COUNT-1)."""
        logger.debug(f'Putting mirrorcell stoponemotor motor {index} in {self.tel_addr}')
        await self.aput_value('stoponemotor', Index=index)

    async def astop_all_motors(self) -> None:
        """Stop all motors."""
        logger.debug(f'Putting mirrorcell stopallmotors in {self.tel_addr}')
        await self.aput_value('stopallmotors')
