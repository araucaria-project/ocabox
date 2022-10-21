from typing import Protocol, runtime_checkable

from ob.data_colection.base_components.tree_component import ProvidesResponseProtocol
from ob.data_colection.value import Value
from ob.data_colection.value_call import ValueRequest


@runtime_checkable
class KnownValueProtocol(Protocol):
    # TODO może ten protokol powinien być w sierodku TreeCacheProtocol MIKOŁAJ
    def get_change_time(self) -> float:
        pass

    def get_timestamp(self) -> float or None:
        pass

    def get_value(self) -> Value:
        pass


@runtime_checkable
class TreeCacheProtocol(ProvidesResponseProtocol, Protocol):

    def set_conditional_freezer(self):
        pass

    def remove_conditional_freezer(self):
        pass

    def get_k_val(self, address) -> KnownValueProtocol or None:
        pass

    def is_cachable_request(self, request: ValueRequest) -> bool:
        pass
