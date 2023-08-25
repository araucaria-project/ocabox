from abc import ABC, abstractmethod
from typing import Optional, List, Tuple

from pyaraucaria.coordinates import ra_to_decimal, dec_to_decimal

from ob.planrunner.ern.commands.commands_args_map import CommandArgsMap
from ob.planrunner.ern.commands.commands_names import CommandsNames
from ob.planrunner.ern.commands.commands_types import CommandsTypes
from ob.planrunner.ern.errors import PlanBuildError
from ob.planrunner.ern.focusing_data import FocusingData
from ob.planrunner.ern.sequence_data import SequenceData


class CommandArgsReader(ABC):
    _NAME: str = "DEFAULT"
    DEFAULT_TRACKING_ON = CommandArgsMap.TRACKING.OFF.val()

    def __init__(self, arg, kwarg, **kwargs):
        super().__init__(**kwargs)
        self._args = arg
        self._kwargs = kwarg
        self._seq: List[Tuple[SequenceData, FocusingData]] = self._create_seq_list()  # can raise PlanBuildError
        self._mapped_args: dict = {CommandArgsMap.RA: CommandArgsMap.RA.val(),
                                   CommandArgsMap.DEC: CommandArgsMap.DEC.val(),
                                   CommandArgsMap.OBJ_NAME: CommandArgsMap.OBJ_NAME.val()}
        self.validate()
        # ==== object name ====
        if len(self._args) >= 1:
            self._mapped_args[CommandArgsMap.OBJ_NAME] = self._args[0]
        # ==== ra dec ====
        if len(self._args) >= 3:
            self._mapped_args[CommandArgsMap.RA] = ra_to_decimal(self._args[1])
            self._mapped_args[CommandArgsMap.DEC] = dec_to_decimal(self._args[2])

    @abstractmethod
    def validate(self):
        """
        Method validate command arguments

        :raise PlanBuildError
        :return:
        """
        raise NotImplementedError

    def _create_seq_list(self) -> List[Tuple[SequenceData, FocusingData]]:
        """

        :raise PlanBuildError
        :return:
        """
        lis = []
        for s in self._plan_seq_rare_list:
            sd = SequenceData(seq=s)
            sd.validate()
            fd = FocusingData(seq_foc=self.focus_list_rare, expositions_quantity=sd.exp_quantity,
                              defocus=self.defocus)
            fd.validate()
            lis.append((sd, fd))
        return lis

    @property
    def defocus(self) -> int:
        return int(self._kwargs.get(CommandArgsMap.FOCUSING_OFFSET, CommandArgsMap.FOCUSING_OFFSET.val()))

    @property
    def uobi(self) -> int:
        v = self._kwargs.get(CommandArgsMap.UOBI, None)
        if v is not None:
            return self._kwargs[CommandArgsMap.UOBI]
        else:
            return CommandArgsMap.UOBI.val()

    @property
    def _dome_follow(self) -> bool:
        v = self._kwargs.get(CommandArgsMap.DOME_FOLLOW, None)
        if v is not None:
            if CommandArgsMap.DOME_FOLLOW.has_item(v):
                return CommandArgsMap.DOME_FOLLOW.get_item_by_name(v).val()
        return CommandArgsMap.DOME_FOLLOW.ON.val()

    @property
    def epoch(self) -> str:
        return str(self._kwargs.get(CommandArgsMap.EPOCH, CommandArgsMap.EPOCH.val()))

    # @property
    # def dither_on(self) -> bool:
    #     """
    #     Do dithering or not.
    #     :return: bool
    #     """
    #     if self.command_name == 'SKYFLAT':
    #         if 'dither' not in self.kwargs.keys():
    #             return True
    #         elif 'dither' in self.kwargs.keys() and self.kwargs['dither'] != 'none':
    #             return True
    #         elif 'dither' in self.kwargs.keys() and self.kwargs['dither'] == 'none':
    #             return False
    #         else:
    #             return False
    #
    #     elif self.command_name in self.possible_dither:
    #         if 'dither' not in self.kwargs.keys():
    #             return False
    #         elif 'dither' in self.kwargs.keys() and self.kwargs['dither'] != 'none':
    #             return True
    #         elif 'dither' in self.kwargs.keys() and self.kwargs['dither'] == 'none':
    #             return False
    #         else:
    #             return False
    #     else:
    #         return False

    @property
    def mirror_cover_mode(self):
        v = self._kwargs.get(CommandArgsMap.MIRROR_COVER, None)
        if v is not None:
            if CommandArgsMap.MIRROR_COVER.has_item(v):
                return v
        return None

    @property
    def observer(self) -> str:
        return self._kwargs.get(CommandArgsMap.OBSERVER, CommandArgsMap.OBSERVER.val())

    @property
    def screen_light_mode(self):
        v = self._kwargs.get(CommandArgsMap.SCREEN_LIGHT, None)
        if v is not None:
            if CommandArgsMap.SCREEN_LIGHT.has_item(v):
                return v
        return None

    # def _op_id(self, id_next: int) -> str:
    #     return f'{self.id}_{self.numb(id_next)}'

    # def _add_comp(self, sub: SubCommand, id_next: int) -> int:
    #     self.subcomponents[f'{self.id}_{self.numb(id_next)}'] = sub
    #     return id_next + 1

    @property
    def plan_object_name(self) -> Optional[str]:
        return self._mapped_args.get(CommandArgsMap.OBJ_NAME, CommandArgsMap.OBJ_NAME.val())

    @property
    def plan_ra(self) -> Optional[float]:
        return self._mapped_args.get(CommandArgsMap.RA, CommandArgsMap.RA.val())

    @property
    def plan_dec(self) -> Optional[float]:
        return self._mapped_args.get(CommandArgsMap.DEC, CommandArgsMap.DEC.val())

    @property
    def plan_az(self) -> Optional[float]:
        return self._kwargs.get(CommandArgsMap.AZ, CommandArgsMap.AZ.val())

    @property
    def plan_alt(self) -> Optional[float]:
        return self._kwargs.get(CommandArgsMap.ALT, CommandArgsMap.ALT.val())

    @property
    def plan_seq_rare(self) -> str:
        return str(self._kwargs.get(CommandArgsMap.SEQ, CommandArgsMap.SEQ.val()))

    @property
    def _plan_seq_rare_list(self) -> List[str]:
        return [i for i in self.plan_seq_rare.split(",") if i]

    @property
    def plan_seq(self) -> List[SequenceData]:
        return [a for a, b in self._seq]

    @property
    def plan_seq_focus_combination(self) -> List[Tuple[SequenceData, FocusingData]]:
        return self._seq

    @property
    def focus_seq(self) -> List[FocusingData]:
        return [b for a, b in self._seq]

    @property
    def domeflat_dome_az(self) -> float or None:
        # TODO take this value from settings
        if CommandsNames.get_item_by_name(self._NAME).val() == CommandsTypes.FLAT:
            return 0.0
        else:
            return None

    @property
    def domeflat_mount_az(self) -> float or None:
        # TODO take this value from settings
        if CommandsNames.get_item_by_name(self._NAME).val() == CommandsTypes.FLAT:
            return self.domeflat_dome_az + 180.0
        else:
            return None

    @property
    def domeflat_mount_alt(self) -> float or None:
        # TODO take this value from settings
        if CommandsNames.get_item_by_name(self._NAME).val() == CommandsTypes.FLAT:
            return 15.0
        else:
            return None

    @property
    def possible_dither(self) -> List[str]:
        """
        List of commands with possibility of dither
        :return: List of commands name
        """
        # todo może wywalić to jak nie potrzebne
        return [CommandsNames.OBJECT, CommandsNames.SNAP, CommandsNames.SKYFLAT]

    @property
    def tracking(self) -> bool:
        v = self._kwargs.get(CommandArgsMap.TRACKING, None)
        if v is not None:
            if CommandArgsMap.SCREEN_LIGHT.has_item(v):
                return CommandArgsMap.TRACKING.get_item_by_name(v).val()
        return self.DEFAULT_TRACKING_ON

    @property
    def object_name(self) -> str:
        name = ""
        if self.plan_object_name:
            name = self.plan_object_name
        else:
            if self._NAME in [CommandsNames.SKYFLAT, CommandsNames.FOCUS, CommandsNames.DOMEFLAT, CommandsNames.DARK,
                              CommandsNames.ZERO, CommandsNames.SNAP]:
                name = self._NAME.lower()
        return name

    @property
    def focus_list_rare(self) -> str:
        """
        Input format focus_target/focus_step
        :return: [focus_target, focus_step]
        """
        return self._kwargs.get(CommandArgsMap.FOCUSING, CommandArgsMap.FOCUSING.val())
