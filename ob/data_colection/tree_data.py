from dataclasses import dataclass
from serverish.messenger import Messenger


@dataclass
class TreeData:
    """
    this is an object containing the global data of the entire octabox tree.
    """
    nats_messenger: Messenger = None

    def __post_init__(self):
        if self.nats_messenger is None:
            self.nats_messenger = Messenger()
