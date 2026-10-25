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

    def get_config(self) -> dict:
        """Method return configuration for telescope"""
        return self.observatory.get_telescopes_configuration().get(self.tel_addr, {})

    def component_config(self, name: str) -> dict:
        """The configuration of component ``name`` as TIC publishes it (``observatory.components``);
        empty when the telescope has no such component. Read live: TIC republishes on restart."""
        return ((self.get_config().get('observatory') or {}).get('components') or {}).get(name) or {}
