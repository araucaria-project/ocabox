import logging

from ob.comunication.base_client import BaseClient

logger = logging.getLogger(__name__.rsplit('.')[-1])


class ClientInternal(BaseClient):
    DEFAULT_NAME = 'InternalClient'
    pass
