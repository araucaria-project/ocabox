from planrunner.command import Command


class CommandZero(Command):
    _NAME = "ZERO"

    def __int__(self, kw_args: dict, ln: str, commands: list = None, label: str = "", message: str = "", **kwargs):
        super().__int__(kw_args=kw_args, ln=ln, label=label, message=message)
