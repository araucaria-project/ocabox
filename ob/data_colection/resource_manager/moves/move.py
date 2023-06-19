from ob.data_colection.resource_manager.errors import ResourceCommandError


class Move:
    def __init__(self, api):
        self.error = False
        self.error_content = None
        self.positions = []
        self._api = api
        self._actn = None

    async def watch(self):
        for p in self.positions:
            await p.run(api=self._api)

    @property
    def progress(self):
        """
        Property representing summ progress of all positions

        :raise ValueError
        :return:
        """
        suma = 0
        for p in self.positions:
            suma += p.progress  # can raise ValueError
        return suma / len(self.positions)

    def done(self):
        for p in self.positions:
            if not p.done():
                return False
        return True

    async def wait(self):
        for p in self.positions:
            await p.wait()

    def add_position(self, position):
        # this should be before add given position to list
        self._set_in_level(position=position)
        self.positions.append(position)

    def _set_in_level(self, position):
        """This should be before add given position to list"""
        for p in self.positions:
            if p.level < position.level:
                position.add_more_important_position(p)
            elif p.level > position.level:
                p.add_more_important_position(position)

    def set_action(self, action):
        self._actn = action

    async def make(self):
        try:
            if self._actn is not None:
                await self._actn
            else:
                await self._action()
        except NotImplementedError:
            raise ResourceCommandError(f"Method action is not implemented")
        except ResourceCommandError:
            raise

    async def _action(self):
        raise NotImplementedError
