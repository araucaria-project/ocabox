"""Read the M1 mirror cell (active collimation) and watch it move — READ-ONLY.

Demonstrates the high-level ``MirrorCell`` client component (ocabox ≥ 2.6.3,
server ≥ 2.4.0): one-shot fresh reads of positions and per-motor scalars, and
a subscription to ``moving``. Requires NATS (client config) and a running TIC.

Positions come back in metres (µm-scale in practice) — scale in the consumer.
"""
import asyncio

from serverish.messenger import Messenger

from ocaboxapi import Observatory

TELESCOPE = 'zb08'
NATS_HOST, NATS_PORT = 'nats.oca.lan', 4222


async def main():
    messenger = Messenger()
    await messenger.open(host=NATS_HOST, port=NATS_PORT, wait=4)
    observatory = Observatory(client_name='CliClient', software_id='mirrorcell-example',
                              config_stream='tic.config.observatory')
    await observatory.load_client_cfg()
    observatory.connect()
    try:
        cell = observatory.get_telescope(TELESCOPE).get_mirrorcell()

        if not await cell.aget_available(time_of_data_tolerance=1.0):
            print(f'{TELESCOPE} has no mirror cell (e.g. wk06) — nothing to read')
            return

        # one-shot fresh reads (TIC's cache default is 60 s; nothing subscribes
        # to the mirror cell, so demand recent data explicitly)
        positions = await cell.aget_positions(time_of_data_tolerance=1.0)
        print('positions [µm]:', [f'{p * 1e6:+.1f}' for p in positions])
        for index in range(cell.MOTOR_COUNT):
            text = await cell.aget_motor_statustext(index, time_of_data_tolerance=1.0)
            print(f'motor {index}: {text}')

        # subscription: prints every change of `moving` for half a minute
        def on_moving(responses):
            for response in responses:
                if response.value is not None:
                    print('moving:', response.value.v)

        cq = await cell.asubscribe_moving(callback=on_moving, time_of_data_tolerance=1.0)
        await asyncio.sleep(30)
        cell.unsubscribe(cq)
    finally:
        await observatory.aunsubscribe_all()
        await messenger.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('stopped')
