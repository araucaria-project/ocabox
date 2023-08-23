import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, Tuple, List

from ob.data_colection.resource_manager.errors import ResourceCommandError
from ob.planrunner.ern.command import Command
from ob.planrunner.ern.commands.commands_args_map import CommandArgsMap
from ob.planrunner.ern.errors import ResourceError, PlanBuildError
from ob.planrunner.ern.commands.commands_names import CommandsNames
from ob.planrunner.ern.moves.custom_moves.camera_exposure import CameraExposure
from ob.planrunner.ern.moves.custom_moves.dome_slew import DomeSlew
from ob.planrunner.ern.moves.custom_moves.dome_slew_ra_dec import DomeSlewRaDec
from ob.planrunner.ern.moves.custom_moves.filter_wheel import FilterWheel
from ob.planrunner.ern.moves.custom_moves.focuser_focus import FocuserFocus
from ob.planrunner.ern.moves.custom_moves.mirror_cover_cls_opn import MirrorCoverClsOpn
from ob.planrunner.ern.moves.custom_moves.mount_slew_alt_az import MountSlewAltAz
from ob.planrunner.ern.moves.custom_moves.mount_slew_ra_dec import MountSlewRaDec
from ob.planrunner.ern.moves.move import Move

logger = logging.getLogger(__name__.rsplit('.')[-1])


class CommandObject(Command):
    _NAME = CommandsNames.OBJECT

    @dataclass
    class _ExecuteSeqObject:
        filter: FilterWheel
        exp_list: List[Tuple[FocuserFocus, CameraExposure]]

    def __init__(self, command_dict: dict, plan_data, previous_command, id_: str = None,
                 loop: asyncio.AbstractEventLoop = None, **kwargs):
        super().__init__(command_dict=command_dict, plan_data=plan_data, id_=id_, previous_command=previous_command,
                         loop=loop, **kwargs)
        # ------ subcommands ------
        self._move_mount: Optional[Move] = None
        self._move_dome: Optional[Move] = None
        self._camera_exposure: Optional[Move] = None
        self._camera_read_pic: Optional[Move] = None
        self._filter: Optional[Move] = None
        self._focuser: Optional[Move] = None
        self.filter_wheel: Optional[Move] = None
        self._mirror_close: Optional[Move] = None
        self._mirror_open: Optional[Move] = None
        self._execute_seq_subcomands: List[CommandObject._ExecuteSeqObject] = []

        # ------ build subcommands ------
        self._create_modules_from_args()

    def _create_modules_from_args(self):
        """

        :raise PlanBuildError:
        :return:
        """
        try:
            # ----------- mount ----------
            if self.plan_alt is not None and self.plan_az is not None:
                self._move_mount = MountSlewAltAz(resource_nr=0, alt_az=(self.plan_alt,
                                                                         self.plan_az),
                                                  plan_data=self._plan_data)
            else:
                self._move_mount = MountSlewRaDec(resource_nr=0, ra_dec=(self.plan_ra,
                                                                         self.plan_dec),
                                                  plan_data=self._plan_data)

            # ----------- dome ----------
            if self.plan_alt is not None and self.plan_az is not None:
                self._move_dome = DomeSlew(resource_nr=0, az=self.plan_az,
                                           plan_data=self._plan_data)
            else:
                self._move_dome = DomeSlewRaDec(resource_nr=0, ra_dec=(self.plan_ra,
                                                                       self.plan_dec),
                                                plan_data=self._plan_data)

            # ----------- mirror cover ----------
            if self.mirror_cover_mode in (CommandArgsMap.MIRROR_COVER.OPEN, CommandArgsMap.MIRROR_COVER.AUTO):
                self._mirror_open = MirrorCoverClsOpn(action=True, resource_nr=0, plan_data=self._plan_data)
            if self.mirror_cover_mode in (CommandArgsMap.MIRROR_COVER.CLOSE, CommandArgsMap.MIRROR_COVER.AUTO):
                self._mirror_close = MirrorCoverClsOpn(action=False, resource_nr=0, plan_data=self._plan_data)
            # if None don't do anything with mirror

            # =============== EXPOSITION SEQUENCE ==============
            for s, f in self.plan_seq_focus_combination:
                # ----------- change filter ------------
                _filter = FilterWheel(filter_=s.filter, plan_data=self._plan_data)
                exp_list = []
                for i in range(0, s.exp_quantity):
                    # ----------- set focus ----------------
                    _focuser = FocuserFocus(focus=f.focus_position(exp_no=i), plan_data=self._plan_data)
                    # ----------- camera exposure ----------
                    _camera_exposure = CameraExposure(exposure_time=s.exp_time, light=True,
                                                      plan_data=self._plan_data)
                    exp_list.append((_focuser, _camera_exposure))
                self._execute_seq_subcomands.append(CommandObject._ExecuteSeqObject(filter=_filter, exp_list=exp_list))
            # -----------

        except PlanBuildError:
            raise

    def _get_res(self, name: str, nr: int):
        m = self.res_mngr.get_resource(name=name, nr=nr)
        # TODO W przyszłości mogą być inne sterowniki teleskopów które będą mieć inne zasoby dlatego dorobić kiedyś
        #  trzeba kontrolę typu zasobu, np czy jest alpaca czy inny
        if m:
            return m
        raise ResourceError(f"Can't find resource")

    async def _is_loaded(self, resource_name: str, nr: int = 0):
        m = self.res_mngr.get_resource(name=resource_name, nr=nr)
        return m is not None

    async def _run_body(self):
        await self._wait_for_permission_to_locking()  # jeśli zabrało wszystko co potrzebne to można zaczynać zbierać u siebie i lokować
        try:
            #  --------- prepare step - check all needed resources is available ----------
            if self.res_mngr.get_resource(self.res_mngr.MOUNT) is None or \
                    self.res_mngr.get_resource(self.res_mngr.DOME) is None or \
                    self.res_mngr.get_resource(self.res_mngr.CAMERA) is None or \
                    self.res_mngr.get_resource(self.res_mngr.COVERCALIBRATOR) is None or \
                    self.res_mngr.get_resource(self.res_mngr.FOCUSER) is None or \
                    self.res_mngr.get_resource(self.res_mngr.FILTERWHEEL):
                self.log("Some of the required resource is not available")
                return

            #  ---------  first step ----------
            async with self.res_mngr.get_resource(self.res_mngr.MOUNT), \
                    self.res_mngr.get_resource(self.res_mngr.DOME), \
                    self.res_mngr.get_resource(self.res_mngr.COVERCALIBRATOR):

                await self._move_mount.run()
                await self._move_dome.run()
                if self._mirror_open:
                    await self._mirror_open.run()

                await self._move_mount.wait()
                await self._move_dome.wait()
                if self._mirror_open:
                    await self._mirror_open.wait()
            # TODO  tą logikę można jeszcze skomplikować takżeby filtr się zmieniał podczas ruchu kopuły ale njpierw
            #  pokazać to mikołajowi - MIKOŁAJ

            #  ---------  second step ----------
            async with self.res_mngr.get_resource(self.res_mngr.CAMERA), \
                    self.res_mngr.get_resource(self.res_mngr.FOCUSER), \
                    self.res_mngr.get_resource(self.res_mngr.FILTERWHEEL):

                for ess in self._execute_seq_subcomands:
                    await ess.filter.run()

                    for foc, cam in ess.exp_list:
                        await foc.run()
                        await ess.filter.wait()  # attention ! in first loop step here will be wait but all the
                        # next steps always finish immediately because Move will be already finished. In first time
                        # we will save time
                        await foc.wait()
                        await cam.run()
                        await cam.wait()

                # get again for close mirror
                async with self.res_mngr.get_resource(self.res_mngr.COVERCALIBRATOR):
                    self._unlock_next_command()  # unlock next command faster, before this command do last thing
                    if self._mirror_close:
                        await self._mirror_close.run()
                        await self._mirror_close.wait()

        except ResourceCommandError:
            self.log("Command have error")

    async def a_init(self):
        await super().a_init()
        if self._move_mount is not None:
            await self._move_mount.a_init()
