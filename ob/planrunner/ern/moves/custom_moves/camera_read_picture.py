import logging
import time
from datetime import datetime
from typing import List

from pyaraucaria.fits import fits_header, fits_stat, save_fits_from_array

from ob.comunication.comunication_error import CommunicationTimeoutError, CommunicationRuntimeError
from ob.data_colection.resource_manager.errors import ResourceCommandError
from ob.data_colection.resource_manager.resource_manager import ResourceManager
from ob.planrunner.ern.errors import PlanBuildError
from ob.planrunner.ern.moves.move import Move
from ob.planrunner.ern.moves.position import Position
from pyaraucaria.date import datetime_to_julian

logger = logging.getLogger(__name__.rsplit('.')[-1])


class CameraReadPicture(Move):
    _USED_RESOURCE = ResourceManager.CAMERA

    def __init__(self, exposure_time: float, plan_data, resource_nr=0, mount_resource_nr=None, req_ra=None):
        super().__init__(plan_data=plan_data)
        self._resource_nr = resource_nr
        self._mount_resource_nr = mount_resource_nr if mount_resource_nr is not None else self._resource_nr
        self._resource_content = self.res_mngr.get_resource(self._USED_RESOURCE, nr=self._resource_nr)
        self._mount_resource_content = self.res_mngr.get_resource(ResourceManager.MOUNT, nr=self._mount_resource_nr)
        if self._mount_resource_content is None:
            raise PlanBuildError(f"Can not find mount resource content for camera")
        self._exposure_time: float = exposure_time

        self.exp_time_start = None
        self.readout_time_start = None

        self._build()

    def _build(self):
        # here position has random value in target, it will be updated in a_init() method
        self.add_position(
            Position(f"{self._resource_content.adr}.imageready", t=True))

    async def _action(self):

        await self.watch()

    @staticmethod
    def get_oca_date(jd: float) -> float:
        return jd - 2460000

    async def _save_fits(self, sub: int, sub_time: float) -> None:

        jd = datetime_to_julian(self.exp_time_start)
        jd_oca = f"{self.get_oca_date(jd):010.5f}"

        array = await self._camera_aget_imagearray()
        gains = await self.camera.aget_gains()
        readoutmodes = await self.camera.aget_readoutmodes()
        gain = await self.camera.aget_gain()
        readoutmode = await self.camera.aget_readoutmode()



        gain = self.indexing_value(gain, gains)
        readoutmode = self.indexing_value(readoutmode, readoutmodes)



        header = fits_header(
            obs_lat=self._mount_resource_content.latitude,
            parsed_obs_lat=self._mount_resource_content.latitude,
            obs_lon=self._mount_resource_content.longitude,
            parsed_obs_lon=self._mount_resource_content.longitude,
            obs_elev=self._mount_resource_content.elevation,
            tel_id=str(self._resource_content.telescope_id),  # observatory name like zb08
            utc_now=str(self.exp_time_start.isoformat(sep='T', timespec='auto')),
            jd=jd,
            req_ra=self.kwargs["req_ra"],
            req_dec=self.kwargs["req_dec"],
            epoch=self.kwargs["epoch"],
            tel_ra=self.mount.rightascension,
            tel_dec=self.mount.declination,
            tel_alt=self.mount.altitude,
            tel_az=self.mount.azimuth,
            focus=self.focuser.position,
            rotator_pos=self.rotator.position,
            obs_type=str(self.kwargs['type']),
            object=str(self.kwargs["obj_name"]),
            filter=str(self.kwargs["filter"]),
            observer=str(self.kwargs['observer']),
            req_exp=sub_time,
            cam_exp=sub_time,
            ccd_name=str(self.camera.sensorname),
            ccd_temp=self.camera.ccdtemperature,
            ccd_binx=self.camera.binx,
            ccd_biny=self.camera.biny,
            read_mod=str(readoutmode),
            gain=str(gain)
        )
        if self.kwargs['type'] == 'snap':
            file_name = f'snap'
        else:
            file_name = f'{self._resource_content.telescope_id}c_{jd_oca.split(".")[0]}_{jd_oca.split(".")[1]}'
        stat = fits_stat(array, size=100, median=False, std=False, min=False, max=False)

        save_fits_from_array(array,
                             self.target_folder,
                             file_name,
                             header,
                             overwrite=True,
                             dtyp='sideint16')

    @staticmethod
    def indexing_value(value: int, values: List[str]) -> int or str:
        if isinstance(value, int) and isinstance(values, list):
            data = values[value]
        else:
            data = str(value)
        return data
