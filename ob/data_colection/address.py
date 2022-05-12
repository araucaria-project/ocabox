class Address:

    def __init__(self, s: str):
        self.components = s.split('.') if s else []

    @classmethod
    def as_address(cls, a):
        if isinstance(a, Address):
            return a
        if isinstance(a, str):
            return Address(a)

        # TODO jakie są inne możliwości?
        raise ValueError(a)

    def __eq__(self, other):
        return self.components == other.components

    def __hash__(self):
        return hash(self.components)

    def __str__(self):
        return '.'.join(self.components)

    def __iter__(self):
        return iter(self.components)
