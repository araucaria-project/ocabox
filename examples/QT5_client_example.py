import sys
import asyncio

from ob.comunication.client import Client
from ob.comunication.client_api import ClientAPI
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QGridLayout
from qasync import QEventLoop


async def listener(api_w: ClientAPI, address, target, name="name"):
    cq = await api_w.subscribe(address, delay=1, time_of_data_tolerance=0.5, name=name)  # this creates 'cycle query' object
    cq.start()  # start retrieving
    try:
        while True:
            await asyncio.sleep(0)
            result = await cq.get_response()  # response is a list because it is possible to subscribe to multiple
            # values in one query. IT IS RECOMMENDED TO ONLY SUBSCRIPTION FOR ONE VALUE AT A TIME

            if result and result[0].value:
                print(result[0].value.v)
                target.setText(f"{result[0].value.v}")  # update field in GUI
                # update_field(target, result[0].value.v)  # update field in GUI
    finally:
        await cq.stop_and_wait()  # it is recommended to use this method instead of the usual Stop() because it waits
        # for the query to finish and the stop method only puts it in a closing state which can take some time and
        # must be terminated before the end of the program


async def fun(lo):
    address1 = "800.dome.azimuth"  # address to data. depends on how the server is structured
    address2 = "800.dome.shutterstatus"  # address to data. depends on how the server is structured
    li1 = lo.create_task(listener(api, address1, display1, name="sub1"))  # 'fire and forget' don't await
    li2 = lo.create_task(listener(api, address2, display2, name="sub2"))  # 'fire and forget' don't await
    # await li1  # don't wait for tasks. They have to run in the background
    # await li2  # don't wait for tasks. They have to run in the background

if __name__ == '__main__':
    client = Client(name="client for QT")  # It is not necessary to create a client (the api will do it automatically) but recommended. Parameter 'name' is optional
    api = ClientAPI(client=client, user_email="abc@abc.com", user_name="John", user_description="example description")  # create API object parameters 'user_email', 'user_name', 'user_description'  are optional and are used to distinguish different clients

    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)  # NEW must set the event loop

    window = QWidget()
    window.setWindowTitle("Alpaca GUI Example")
    window.setFixedSize(300, 200)
    example_grid_layout = QGridLayout()
    window.setLayout(example_grid_layout)

    # first data field
    example_grid_layout.addWidget(QLabel("dome azimuth"), 0, 0)
    display1 = QLineEdit()
    display1.setFixedHeight(30)
    display1.setAlignment(Qt.AlignmentFlag.AlignRight)
    display1.setReadOnly(True)
    example_grid_layout.addWidget(display1, 0, 1)

    # second data field
    example_grid_layout.addWidget(QLabel("Shutter status"), 1, 0)
    display2 = QLineEdit()
    display2.setFixedHeight(30)
    display2.setAlignment(Qt.AlignmentFlag.AlignRight)
    display2.setReadOnly(True)
    example_grid_layout.addWidget(display2, 1, 1)

    window.show()  # start app

    with loop:
        loop.run_until_complete(fun(loop))
        sys.exit(loop.run_forever())
