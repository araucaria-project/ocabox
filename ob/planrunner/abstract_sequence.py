from typing import Dict, List, Any
import logging
import asyncio

logger = logging.getLogger(__name__.rsplit('.')[-1])


class AbstractSequence:

    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def build_args(sequence_dict: Dict[Any, Any]) -> List[Any]:
        if 'args' in sequence_dict.keys():
            return sequence_dict['args']
        else:
            return []

    @staticmethod
    def build_kwargs(sequence_dict: Dict[Any, Any]) -> Dict[Any, Any]:
        if 'kwargs' in sequence_dict.keys():
            return sequence_dict['kwargs']
        else:
            return {}

    @staticmethod
    def numb(number: int) -> str:
        if number > 9:
            return f'{number}'
        else:
            return f'0{number}'

    @staticmethod
    async def _arun(subcomponents: Any, step_id: str or None = None):
        for n in subcomponents.keys():
            if step_id is None:
                await subcomponents[n].arun(step_id=step_id)
            elif step_id is not None:
                match = step_id[: len(subcomponents[n].id)]
                if match <= subcomponents[n].id:
                    await subcomponents[n].arun(step_id=step_id)