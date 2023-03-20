# import logging
# import time
# from typing import Dict
#
# from ob.data_colection.address import AddressError
# from ob.data_colection.base_components.tree_base_provider import TreeBaseProvider
# from ob.data_colection.base_components.tree_component import ProvidesResponseProtocol
# from ob.data_colection.coded_error import TreeStructureError, TreeOtherError
# from ob.data_colection.specialistic_components.tree_base_request_blocker import TreeBaseRequestBlocker, ReservationError
# from ob.data_colection.tree_user import BaseTreeUser
# from ob.data_colection.value import Value
# from ob.data_colection.value_call import ValueRequest
#
# logger = logging.getLogger(__name__.rsplit('.')[-1])
#
#
# class TreeAlpacaRequestBlocker(TreeBaseProvider, TreeBaseRequestBlocker):
#     """
#     This is a module for filtering and blocking some type incoming requests. In order to unlock access, access must
#     be reserved by the user for a certain period of time. Reservation is done using a different module.
#     """
#
#     COMPONENT_DEFAULT_NAME: str = 'TreeAlpacaRequestBlocker'
#
#     def __init__(self, component_name: str, subcontractor: ProvidesResponseProtocol = None, **kwargs):
#         super().__init__(component_name=component_name, subcontractor=subcontractor, **kwargs)
#         self._current_user: BaseTreeUser or None = None
#         self._timeout_reservation: float = 0
#         self._black_lists: Dict[str, list] = {'GET': [],
#                                               'PUT': []}
#         self._white_lists: Dict[str, list] = {'GET': [],
#                                               'PUT': []}
#         self._init_lists_of_special_requests()
