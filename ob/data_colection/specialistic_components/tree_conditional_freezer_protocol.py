from typing import Protocol, runtime_checkable


@runtime_checkable
class TreeConditionalFreezerProtocol(Protocol):

    def set_change_event(self):
        pass

    def clear_change_event(self):
        pass
