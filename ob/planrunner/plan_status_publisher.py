import time

from serverish.messenger import get_publisher

from ob.comunication.nats_streams import NatsStreams


class PlanStatusPublisher:

    def __init__(self):
        self._plan_current_state = {}  # this is a dictionary witch command's status only witch one was finished

    def update_status(self, cmd_id: str, data):
        self._plan_current_state[cmd_id] = data

    @staticmethod
    async def send_program_state(plan_id: str, dic: dict, telescope_id: str):
        """
        Method send observation plan state to NATS stream.

        :param plan_id: observation plan id
        :param dic: dictionary witch observation plan initial state
        :param telescope_id: telescope id like "zb08"
        :return: None
        """
        publisher = get_publisher(NatsStreams.PLAN_MANAGER_PLAN.format(telescope_id))
        await publisher.publish(data={'id': plan_id,
                                      'published': [*time.gmtime()],
                                      'state': dic},
                                meta={
                                    "message_type": "program_state",  # IMPORTANT one of pre declared types
                                    "tags": ["plan_state"],
                                    'sender': 'Ocabox server',
                                })
