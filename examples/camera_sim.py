import asyncio
import os
import sys
import numpy as np

image_size = 10

async def sky_flat_sim():
    arg = sys.argv
    if len(arg) < 3:
        arg = ['', 'evening', '100']
    if arg[1] == 'morning':
        arr = np.random.randint(low=14800, high=15200, size=(image_size, image_size))
    else:
        arr = np.random.randint(low=29800, high=30200, size=(image_size, image_size))
    while True:
        await asyncio.sleep(2)
        if arg[1] == 'morning':
            arr = arr + int(arg[2])
        else:
            arr = arr - int(arg[2])
        with open(os.path.expanduser('~/.oca/camera_sim.txt'), 'w') as f:
            f.write(f'{arr.tolist()}')



async def main():

    await asyncio.create_task(sky_flat_sim())



if __name__ == '__main__':
    try:
        asyncio.run(main())
    except:
        pass
    finally:
        pass