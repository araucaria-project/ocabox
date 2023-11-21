import asyncio
import os
import sys
import numpy as np
import json
import datetime

image_size = 120
morning_sat = 666 # 12500 + 290 = 13790 to bright
eveningh_sat = 666 # 665 + 290 = 955 too dark

async def sky_flat_sim():
    arg = sys.argv
    if len(arg) < 3:
        arg = ['', '', '10']
    if datetime.datetime.utcnow().hour > 14:
        evening = True
    else:
        evening = False
    # evening = True
    if not evening:
        arr = np.random.randint(low=morning_sat-10, high=morning_sat+10, size=(image_size, image_size))
    else:
        arr = np.random.randint(low=eveningh_sat-10, high=eveningh_sat+10, size=(image_size, image_size))
    while True:
        await asyncio.sleep(0.5)
        if not evening:
            arr = arr + int(arg[2])
        else:
            arr = arr - int(arg[2])
        with open(os.path.expanduser('~/.oca/camera_sim.txt'), 'w') as f:
            f.write(f'{arr.tolist()}')
            f.close()
        with open(os.path.expanduser('~/.oca/camera_sim.txt'), 'r') as f:
            w = json.load(f)
            a = np.array(w)
            print(a.mean(axis=0).mean())
            f.close()



async def main():

    await asyncio.create_task(sky_flat_sim())



if __name__ == '__main__':
    try:
        asyncio.run(main())
    except:
        pass
    finally:
        pass