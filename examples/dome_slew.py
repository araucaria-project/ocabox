import argparse
import random

from ocaboxapi import Observatory

async def amian():
    parser = argparse.ArgumentParser(description='Dome slew example')
    parser.add_argument('--config', type=str, required=False, default=None,
                        help='Path to configuration file')
    # desired azimuth
    parser.add_argument('azimuth', type=float, default=None, nargs='?',
                        help='Desired dome azimuth in degrees')
    args = parser.parse_args()
    az = args.azimuth
    if az is None:
        # random azimuth
        az = random.uniform(0.0, 360.0)
        print(f'No azimuth given, slewing to random azimuth: {az:.2f} deg')
    if az < 0.0 or az >= 360.0:
        print('Azimuth must be in range [0, 360) degrees')
        return


    ob = Observatory()
    ob.connect()

    tel = ob.get_telescope('dev')
    dome = tel.get_dome(id='dome')
    dome.request_special_permission = True
    await dome.aput_slewtoazimuth(az)

if __name__ == '__main__':
    import asyncio

    asyncio.run(amian())