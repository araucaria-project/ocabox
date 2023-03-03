from ocaboxapi.observatory import Observatory



class AbstractTelescope:
    def __init__(self, id: str,  observatory: Observatory) -> None:
        self.id: str = id
        self.observatory: Observatory = observatory
        super().__init__()

    # @property
    # def settings(self):
    #     return settings[f'telescope.{self.id}']

    @property
    def tel_addr(self):
        return self.id
