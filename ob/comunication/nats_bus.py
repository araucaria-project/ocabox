from __future__ import annotations

import asyncio
import logging
from typing import Callable, Optional, Dict, Tuple
from serverish.messenger import request
from serverish.base.exceptions import MessengerRequestNoResponders, MessengerRequestTimeout, MessengerRequestCanceled
from serverish.messenger.msg_journal_pub import MsgJournalPublisher
from serverish.base.task_manager import create_task


logger = logging.getLogger(__name__.rsplit('.')[-1])


async def rpc_request(
        subject: str, data: Dict, journal: Optional[MsgJournalPublisher] = None, timeout: float = 120
) -> Tuple[Optional[Dict], Optional[Dict]]:

    try:
        dat, met = await request(
            subject=subject,
            data=data,
            timeout=timeout
        )
        return dat, met
    except MessengerRequestNoResponders:
        inf = f'Rpc get MessengerRequestNoResponders error.'
        logger.error(inf)
        if journal:
            await journal.error(inf)
        return None, None
    except MessengerRequestCanceled:
        inf = f'Rpc get MessengerRequestCanceled error.'
        logger.error(inf)
        if journal:
            await journal.error(inf)
        return None, None
    except MessengerRequestTimeout:
        inf = f'Rpc get MessengerRequestTimeout error.'
        logger.error(inf)
        if journal:
            await journal.error(inf)
        return None, None


async def _rpc_subscribe(
        callback: Callable, subject: str, data: Dict, interval: float = 1,
        journal: Optional[MsgJournalPublisher] = None, timeout: float = 120
) -> Tuple[Optional[Dict], Optional[Dict]]:

    while True:
        dat, met = await rpc_request(
            subject=subject,
            data=data,
            journal=journal,
            timeout=timeout
        )
        await callback(dat, met)
        await asyncio.sleep(interval)


async def rpc_subscribe(
        callback: Callable, subject: str, data: Dict, interval: float = 1,
        journal: Optional[MsgJournalPublisher] = None, timeout: float = 120
) -> None:

    logger.info(f"Starting rpc subscription to {subject}")
    await create_task(
        _rpc_subscribe(
            callback=callback,
            subject=subject,
            data=data,
            interval=interval,
            journal=journal,
            timeout=timeout
        ),
        name=f'rpc_subscribe_{subject}'
    )
