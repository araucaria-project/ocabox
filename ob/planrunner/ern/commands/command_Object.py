import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, Tuple, List

from ob.data_colection.resource_manager.errors import ResourceCommandError
from ob.planrunner.ern.command import Command
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

    # def _read_arguments(self, args: list, kwargs: dict):
    #     #todo tu trzeba zwalidowaś ilość argsów  if len<1
    #     # ------- read args ----------
    #     # ==== object name ====
    #     if len(args) < 1:  # wrong number of args
    #         pass  # todo raise error
    #     else:  # object name have to be always
    #         if not isinstance(args[0], str):
    #             pass  # todo raise error
    #         self._mapped_args[CommandArgsMap.OBJ_NAME] = args[0]
    #     # ==== ra dec ====
    #     if len(args) >= 3:
    #         self._mapped_args[CommandArgsMap.RA] = args[1]
    #         self._mapped_args[CommandArgsMap.DEC] = args[2]
    #
    #     # ------- read kwargs --------
    #     # ==== tracking ====
    #     v = kwargs.get(CommandArgsMap.TRACKING, None)
    #     if v is not None:
    #         if CommandArgsMap.TRACKING.has_item(v):
    #             self._mapped_args[CommandArgsMap.TRACKING] = CommandArgsMap.TRACKING.get_item_by_name(v).val()
    #         else:
    #             self.log(f"unexpected state of {CommandArgsMap.TRACKING} = {v}")
    #     # ==== epoch ====
    #     v = kwargs.get(CommandArgsMap.EPOCH, None)
    #     if v is not None:
    #         self._mapped_args[CommandArgsMap.EPOCH] = str(v)

    def _create_modules_from_args(self):
        """

        :raise PlanBuildError:
        :return:
        """
        try:
            # ----------- mount ----------
            if self.plan_alt and self.plan_az:
                self._move_mount = MountSlewAltAz(resource_nr=0, alt_az=(self.plan_alt,
                                                                         self.plan_az),
                                                  plan_data=self._plan_data)
            else:
                self._move_mount = MountSlewRaDec(resource_nr=0, ra_dec=(self.plan_ra,
                                                                         self.plan_dec),
                                                  plan_data=self._plan_data)

            # ----------- dome ----------
            if self.plan_alt and self.plan_az:
                self._move_dome = DomeSlew(resource_nr=0, az=self.plan_az,
                                           plan_data=self._plan_data)
            else:
                self._move_dome = DomeSlewRaDec(resource_nr=0, ra_dec=(self.plan_ra,
                                                                       self.plan_dec),
                                                plan_data=self._plan_data)

            # ----------- mirror cover ----------
            self._mirror_open = MirrorCoverClsOpn(action=True, resource_nr=0, plan_data=self._plan_data)
            self._mirror_close = MirrorCoverClsOpn(action=False, resource_nr=0, plan_data=self._plan_data)

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
        print('start')
        try:
            #  --------- pierwsza część ----------
            if self.res_mngr.get_resource(self.res_mngr.MOUNT) is None or \
                    self.res_mngr.get_resource(self.res_mngr.DOME) is None or \
                    self.res_mngr.get_resource(self.res_mngr.CAMERA) is None:
                self.log("Some of the required resource is not available")
                return

            async with self.res_mngr.get_resource(self.res_mngr.MOUNT), \
                    self.res_mngr.get_resource(self.res_mngr.DOME):
                print('start2')
                await self._get_res(self.res_mngr.MOUNT, nr=0).go_to_position()
                await self._get_res(self.res_mngr.DOME, nr=0).go_to_position()

                await self._move_mount.run()

                await self._move_mount.wait()

                await self._get_res(self.res_mngr.DOME, nr=0).wait_to_slew()
                await self._get_res(self.res_mngr.MOUNT, nr=0).wait_to_slew()
                print('a')

            #  ---------  druga część ----------
            async with self.res_mngr.get_resource(self.res_mngr.CAMERA):
                print('b')
                self._get_res(self.res_mngr.CAMERA, nr=0).take_photo()

                self._unlock_next_command()  # unlock faster - elemęty z pierwszej części
                print('c--')
                # po zrobienu zdjęcia można ruszać kopułą więc zgłaszamy _unlock_next_command() i następna komęda
                # OBJECT wie że jeśli loki są wolne to może zaczynać a jadyny zajęty Lock w tym miejscy to Camera więc
                # Dome i Mount będą się ruszać

                # jeśli nieda się stwożyć takiej metody jak poniżej to cały ten algorytm będzie bezużyteczny tutaj
                # ale może mieć zastosowanie np przy Darkach albo innych komędach
                self._get_res(self.res_mngr.CAMERA, nr=0).take_photo()  # nie wiem czy jest taka metoda
                print('d')
        except ResourceCommandError:
            self.log("Command have error")
        finally:
            # good practices to have this here, but it is not necessary
            self._unlock_next_command()  # unlock in the end. This is set again in run() method
            self._set_self_finish()  # command finished - this should be last code line. This is set again in run()
            print('e')

    async def a_init(self):
        await super().a_init()
        if self._move_mount is not None:
            await self._move_mount.a_init()
