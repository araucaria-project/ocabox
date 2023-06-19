import asyncio
import logging
from typing import List, Tuple

from ob.data_colection.resource_manager.resource import ResourceCommandError
from ob.planrunner.ern.command import Command

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
        self._create_modules_from_args()
        self._needed_modules: List[Tuple[str, int]] = []

    def _read_args(self, args: list):
        if len(args) > 2:
            self._mapped_args['ra'] = args[1]
            self._mapped_args['dec'] = args[2]
        # todo uzupełnić

    def _create_modules_from_args(self):
        # todo uzupełnić, utworzyć obiekty, coś w stylu _write_object() z dawnego runera
        nr = 0
        some_module = (self.res_mngr.MOUNT, 0)
        self._needed_modules.append(some_module)

        some_module = (self.res_mngr.DOME, 0)
        self._needed_modules.append(some_module)

        some_module = (self.res_mngr.CAMERA, 0)
        self._needed_modules.append(some_module)

    def _get_res(self, name: str, nr: int):
        m = self.res_mngr.get_resource(name=name, nr=nr)
        # TODO W przyszłości mogą być inne sterowniki teleskopów które będą mieć inne zasoby dlatego dorobić kiedyś
        #  trzeba kontrolę typu zasobu, np czy jest alpaca czy inny
        if m:
            return m
        raise RuntimeError  # todo zrobić customowy bład

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
