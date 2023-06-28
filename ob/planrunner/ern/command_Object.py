import asyncio
import logging
from typing import Optional

from ob.data_colection.resource_manager.errors import ResourceCommandError
from ob.planrunner.ern.command import Command
from ob.planrunner.ern.errors import ResourceError, PlanBuildError
from ob.planrunner.ern.moves.custom_moves.mount_slew_alt_az import MountSlewAltAz
from ob.planrunner.ern.moves.custom_moves.mount_slew_ra_dec import MountSlewRaDec
from ob.planrunner.ern.moves.move import Move

logger = logging.getLogger(__name__.rsplit('.')[-1])


class CommandObject(Command):
    _NAME = "OBJECT"

    def __init__(self, command_dict: dict, plan_data, previous_command, id_: str = None,
                 loop: asyncio.AbstractEventLoop = None, **kwargs):
        super().__init__(command_dict=command_dict, plan_data=plan_data, id_=id_, previous_command=previous_command,
                         loop=loop, **kwargs)
        # --- --- --- --- --- --- --- --- --- --- ---
        self._mapped_args: dict = {"ra": None, "dec": None, "object_name": None, "filter": None, "repetitions": None}
        self._read_args(self.get_args())
        # todo dodać metodę build wywoływaną jak __init__ w którym się zbuduje wszystko np tak jak przy asynchronicznych metodach taki acync init
        # ------ subcommands ------
        self._move_mount: Optional[Move] = None

        # ------ build subcommands ------
        self._create_modules_from_args()

    def _read_args(self, args: list):
        if len(args) > 2:
            self._mapped_args['ra'] = args[1]
            self._mapped_args['dec'] = args[2]
        # todo uzupełnić

    def _create_modules_from_args(self):
        """

        :raise PlanBuildError:
        :return:
        """
        try:
            if self._arg("alt") and self._arg("az"):
                self._move_mount = MountSlewAltAz(api=4, resource_nr=0, alt_az=(self._arg("alt"), self._arg("az")),
                                                  plan_data=self._plan_data)
            else:
                self._move_mount = MountSlewRaDec(api=4, resource_nr=0, ra_dec=(self._arg("ra"), self._arg("dec")),
                                                  plan_data=self._plan_data)
        except PlanBuildError:
            raise

    def _arg(self, name):
        return self._mapped_args.get(name, None)

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
