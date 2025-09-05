import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Callable, Any


async def run_in_thread_executor(*args, func: Callable):
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(
            pool, func, *args
        )
    return result


async def run_in_process_executor(*args, func: Callable, max_workers: int = 4):
    loop = asyncio.get_running_loop()
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        result = await loop.run_in_executor(
            pool, func, *args
        )
    return result