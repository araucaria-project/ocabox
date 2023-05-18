from __future__ import annotations

import logging
import time as time_module

from ob.data_colection.address import AddressError
from ob.data_colection.base_components.tree_provider import TreeProvider
from ob.data_colection.coded_error import TreeOtherError
from ob.data_colection.value import Value
from ob.data_colection.value_call import ValueRequest

logger = logging.getLogger(__name__.rsplit('.')[-1])


class TreeCCTV(TreeProvider):
    """
    This module steers the Ubiquity CCTV camera.
    """
    COMPONENT_DEFAULT_NAME = 'TreeCCTV'

    def __init__(self, camera_id: str, source_name: str, **kwargs):
        super().__init__(component_name=camera_id, source_name=source_name, subcontractor=None, **kwargs)
        logger.info(f'Created {self}')
        self.cam = None
        self.states = {False: None, True: None}

    async def get_value(self, request: ValueRequest, **kwargs) -> Value or None:
        user = request.user
        request_type = request.request_type

        try:
            command = request.address[request.index]
        except IndexError:
            raise AddressError(code=1001, message='The address does not contain a command.')

        if command == 'ir':
            if request_type == 'PUT':
                try:
                    on: bool = request.request_data['state']
                except KeyError:
                    raise TreeOtherError(code=4007,
                                         message=f'{self.get_name()}: Missing "state" parameter in {command} request.')
                ret = await self._set_ir(on)
            else:
                # @Ernest: Is it going to be cached in current structure?
                ret = 'unknown'
            return Value(v=ret, ts=time_module.time())
        elif command == 'snapshot' and request_type == 'GET':
            ret = await self._get_snapshot()
            if ret is None:
                # @Ernest: Jak to zwrocic blad? Przez raise? Jak wybrać odpowiedni kod? (i severity?)
                raise TreeOtherError(code=4002, message='Snapshot not returned')
            return Value(v=ret, ts=time_module.time())

        raise AddressError(code=1002,
                           message=f'Unrecognised method {request_type}:{command} for module {self.get_name()}')

    async def run(self):
        await self._init_api()
        return await super().run()

    async def stop(self):
        await self._close_api()
        return await super().stop()

    async def _init_api(self):
        # imports
        try:
            from pyunifiprotect import ProtectApiClient
            from pyunifiprotect.data import Camera, types
        except ImportError:
            logger.warning(f'{self} Ubiquity CCTV control disabled: Can not import `pyunifiprotect` package')
            return
        self.states = {False: types.IRLEDMode.AUTO, True: types.IRLEDMode.AUTO_NO_LED}

        cam_id = self._get_cfg("udm_camera_id", None)
        if cam_id is None or cam_id == '':
            logger.warning(f'{self} Ubiquity CCTV control disabled: '
                           f'TreeCCTV config misses: udm_camera_id, add it to your configuration')
            return

        # config
        cfg = {
            'host': self._get_cfg("udm_host", ''),
            'port': self._get_cfg("udm_port", 443),  # 7433
            'username': self._get_cfg("udm_user", ''),
            'password': self._get_cfg("udm_password", ''),
        }
        empties = [k for k, v in cfg.items() if v == '']
        if empties:
            logger.warning(f'{self} Ubiquity CCTV control disabled: '
                           f'TreeCCTV config misses: {",".join(empties)}, add it to your .secrets.yaml')
            return

        # init
        try:
            api = ProtectApiClient(cfg['host'], cfg['port'], cfg['username'], cfg['password'], verify_ssl=False)
            await api.update()
        except Exception as e:
            logger.warning(f'{self} Ubiquity CCTV control disabled: '
                           f"Api initialization for {cfg['username']}@{cfg['host']}:{cfg['port']} failed: {e}")
            return

        # camera
        cams = {cam.name: cam for cam in api.bootstrap.cameras.values()}
        try:
            self.cam: Camera = cams[cam_id]
        except LookupError:
            logger.warning(f'{self} Ubiquity CCTV control disabled: '
                           f"Camera {cam_id} not fund (available cameras: {cams.keys()})")
            return
        logger.info(f'{self} Ubiquity CCTV camera API initialized')

    async def _close_api(self):
        logger.info(f'{self} Ubiquity CCTV camera API closed')
        self.cam = None

    async def _get_snapshot(self):
        if self.cam is None:
            logger.info(f'{self} Unifi CCTV API not initialized, command get_snapshot() ignored')
            return None
        return await self.cam.get_snapshot()

    async def _set_ir(self, on: bool) -> None:
        if self.cam is None:
            logger.info(f'{self} Unifi CCTV API not initialized, command set_ir({on}) ignored')
            return
        try:
            await self.cam.set_ir_led_model(self.states[on])
        except Exception as e:
            logger.warning(f'{self} Unifi CCTV API error, reinitialize and retrying: {e}')
            await self._init_api()
            try:
                await self.cam.set_ir_led_model(self.states[on])
            except Exception as e:
                logger.warning(f'{self} Unifi CCTV API error, giving up: {e}')
                raise
