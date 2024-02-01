import asyncio

from ob.comunication.client import Client
from ocaboxapi.client_api import ClientAPI
from obcom.comunication.comunication_error import CommunicationRuntimeError


def main():
    client = Client(
        name="simple client")  # It is not necessary to create a client (the api will do it automatically) but recommended. Parameter 'name' is optional
    api = ClientAPI(client=client, user_email="abc@abc.com", user_name="John",
                    user_description="example description")  # create API object parameters 'user_email', 'user_name', 'user_description'  are optional and are used to distinguish different clients
    asyncio.run(make_subscribe(api, None))


async def make_subscribe(api, cq):
    address1 = "800.dome.azimuth"  # address to data. depends on how the server is structured
    cq = await api.subscribe(address1, delay=1, time_of_data_tolerance=0.5)
    cq.start()
    try:
        while True:
            result = await cq.get_response()
            if result and result[0].value:
                print(result[0].value.v)
    except CommunicationRuntimeError:
        print('error')
    finally:
        print('stopping...')
        await cq.stop_and_wait()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('program was stopped')