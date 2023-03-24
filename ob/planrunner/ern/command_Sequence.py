import ob.planrunner.ern.command


class CommandSequence(ob.planrunner.ern.command.Command):
    _NAME = "SEQUENCE"

    def __int__(self, kw_args: dict, ln: str, commands: list = None, label: str = "", message: str = "", **kwargs):
        super().__int__(kw_args=kw_args, ln=ln, label=label, message=message)

    def read_kwargs(self):
        pass
