import logging
import time

from ob.data_colection.address import AddressError
from ob.data_colection.base_components.tree_component import AddressedResponderProtocol
from ob.data_colection.coded_error import TreeStructureError, TreeOtherError
from ob.data_colection.specialistic_components.tree_provider_frontend import TreeProviderFrontend
from ob.data_colection.tree_user import BaseTreeUser
from ob.data_colection.value import Value
from ob.data_colection.value_call import ValueRequest

logger = logging.getLogger(__name__)


class TreeRequestAlpacaBlocker(TreeProviderFrontend):

    def __init__(self, component_name: str, subcontractor: AddressedResponderProtocol = None, **kwargs):
        super().__init__(component_name=component_name, subcontractor=subcontractor, **kwargs)
        self._current_user: BaseTreeUser or None = None
        self._timeout_reservation: float = 0

    async def get_value(self, request: ValueRequest, **kwargs) -> Value or None:
        # docstring is importing from parent

        # GET always can go ahead
        if request.request_type == 'GET':
            raise TreeStructureError

        if request.request_type != 'PUT':
            raise TreeOtherError(code=4001, message='Unrecognized request type')

        current_user = self._get_current_reservation()
        if current_user and request.user == current_user:
            raise TreeStructureError

        raise AddressError(code=1004)

    def make_reservation(self, user: BaseTreeUser, timeout_reservation: float = None):
        """
        This method make reservation for given user.

        :param user: user object witch one want to reserve time on this block
        :param timeout_reservation: reservation timeout
        :raise ReservationError: if can not now reserve time this block
        :return:
        """
        current_user = self._get_current_reservation()
        if current_user is not None and current_user != user:
            raise ReservationError
        else:
            self._current_user = user
            timeout_reservation = time.time() + self._get_cfg('reservation_length',
                                                              0) if timeout_reservation is None else timeout_reservation
            self._timeout_reservation = timeout_reservation

    def _get_current_reservation(self) -> None or BaseTreeUser:
        """
        This method return current user witch one now use this block or None if No one use.

        :return: Current user or None
        """
        if self._current_user:
            if self._timeout_reservation != 0 and self._timeout_reservation <= time.time():
                self.cancel_reservation()
        return self._current_user

    def cancel_reservation(self):
        """Remove current reservation"""
        self._current_user = None
        self._timeout_reservation = 0

    def get_current_user(self) -> None or BaseTreeUser:
        """
        Return Current user witch one was reserved or None if block is free.

        :return: None or current user
        """
        return self._get_current_reservation()


class ReservationError(Exception):
    pass
