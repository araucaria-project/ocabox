import logging
from typing import Dict, Any, List

log = logging.getLogger(__name__.rsplit('.')[-1])


class ConfigGeneral:

    def __init__(self, telescope_id: str = None) -> None:
        self.telescope_id = telescope_id
        super().__init__()

    def get_value(self, seq: List) -> Any:
        ret = self.config_body
        for n in seq:
            try:
                ret = ret[n]
            except (IndexError, KeyError):
                log.error(f'No value name {n} in config or wrong seq')
                return None
        return ret

    @property
    def config_body(self) -> Dict:
        ret = {
            'take_control_time': 84000,
            'wind_pointing_restr': 11,
            'wind_max': 14,
            'moon_separation': 30,
            'observatory_location': {'latitude': -24.598056, 'longitude': -70.196389, 'elevation': 2817},
            'zb08': {
                'camera': {
                    'DW936_BV': {
                        'gains': ['x1', 'x2', 'x4'],
                        'readoutmodes': ["5Mhz", "3Mhz", "1Mhz", "0.05Mhz"],
                        'temp_range': [-70, 10],
                        'autoflats_evening_factor': 1.11,
                        'zero_mean': 290.0,
                        'pixel_scale': 0.5
                    }
                },
                'mount': {
                    'type': 'az'
                },
                'focuser': {
                    'focusing_range': [14000, 17000],
                }
            },
            'jk15': {
                'camera': {
                    'IMX411': {
                        'gains': ["gain_range"],
                        'readoutmodes': ['16-bit'],
                        'temp_range': {'min': -25, 'max': 10},
                        'pixel_scale': 0.14 # on 2x2 binning
                    },
                    'XL230A_84,BV': {
                        'gains': ["Gain 1", "Gain 2", "Gain 3"],
                        'readoutmodes': ['4MHz 16-bit', '2MHz 16-bit', '1MHz 16-bit',
                                         '1MHz 18-bit', '0,1MHz 16-bit', '0,1MHz 18-bit'],
                        'temp_range': {'min': -70, 'max': 10},
                        'pixel_scale': 0.29
                    }},
                'mount': {
                    'type': 'az'
                },
                'focuser': {
                    'focusing_range': [23000, 27000]
                }
            },
            'wk06': {
                'camera': {
                    'DW936_BV': {
                        'gains': ['x1', 'x2', 'x4'],
                        'readoutmodes': ["5Mhz", "3Mhz", "1Mhz", "0.05Mhz"],
                        'temp_range': {'min': -70, 'max': 10},
                        'pixel_scale': 0.66
                    }
                },
                'mount': {
                    'type': 'eq'
                },
                'focuser': {
                    'focusing_range': [21000, 23000]
                }
            },
            'dev': {
                'camera': {
                    'simul': {
                        'gains': ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13'],
                        'readoutmodes': ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13'],
                        'temp_range': {'min': -30, 'max': 10},
                        'pixel_scale': 0.5
                    }
                },
                'mount': {
                    'type': 'az'
                },
                'focuser': {
                    'focusing_range': [5000, 10000]
                }
            },
        }
        return ret





