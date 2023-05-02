"""Formatting varius values for display"""
from __future__ import annotations
from datetime import datetime
from pyaraucaria.coordinates import to_degminsec_sexagesimal, to_hourangle_sexagesimal, hourangle_to_decimal_deg, \
    deg_to_decimal_deg


def fmt_domeshutter(shutter: int | None):
    """Format shutter status for display"""
    if shutter is None:
        return 'n/a'
    try:
        return [
            'Open',
            'Closed',
            'Opening',
            'Closing',
            'Error',
        ][shutter]
    except IndexError:
        return f'status: {shutter}'

def fmt_time(t: datetime|None, decimals: int = 0) -> str:
    """Format time for display"""
    if t is None:
        return 'n/a'
    format_str = "%H:%M:%S"
    if decimals > 0:
        fractional_seconds = t.strftime(".%f")[:decimals + 1]
        format_str += fractional_seconds
    return t.strftime(format_str)

def fmt_camerastate(state: int | None):
    """Format shutter status for display"""
    if state is None:
        return 'n/a'
    try:
        return [
            'Idle',
            'Waiting',
            'Exposing',
            'Reading',
            'Downloading',
            'Error'
        ][state]
    except IndexError:
        return f'status: {state}'

def fmt_coverstate(state: int | None):
    """Format cover status for display"""
    if state is None:
        return 'n/a'
    try:
        return [
            'unknown',
            'Closed',
            'Moving',
            'Open'
        ][state]
    except IndexError:
        return f'status: {state}'

def fmt_calibratorstate(state: int | None):
    """Format cover status for display"""
    if state is None:
        return 'n/a'
    try:
        return [
            'unknown',
            'Off',
            'Not Ready',
            'Ready'
        ][state]
    except IndexError:
        return f'status: {state}'

def fmt_temperature(temp: float | None, celsius: bool = True):
    """Format temperature for display"""
    if temp is None:
        return 'n/a'
    return f'{temp:.1f} °C' if celsius else f'{temp + 273.15:.1f} K'

def fmt_az(az, sexagesimal=True):
    """Format azimuth for display"""
    if az is None:
        return 'n/a'
    if sexagesimal:
        return fmt_deg_min_sec(az, sign=False, precision=3)
    return '{:9.5f}'.format(az)

def fmt_alt(alt, sexagesimal=True, sign=True):
    """Format altitude for display"""
    if alt is None:
        return 'n/a'
    if sexagesimal:
        return fmt_deg_min_sec(alt, sign=sign, precision=3)
    fmt_str = '{:+10.5f}' if sign else '{:9.5f}'
    return fmt_str.format(alt)

def fmt_ra(ra, sexagesimal=True):
    """Format right ascension for display"""
    if ra is None:
        return 'n/a'
    if sexagesimal:
        return fmt_hourangle_min_sec(ra, precision=3)
    return '{:9.5f}'.format(ra)

def fmt_dec(dec, sexagesimal=True):
    """Format declination for display"""
    if dec is None:
        return 'n/a'
    if sexagesimal:
        return fmt_deg_min_sec(dec, precision=1)
    return '{:+10.5f}'.format(dec)

def parse_deg_or_hms(deg_or_hms: str) -> float:
    """Parse a string as either a decimal degree or a sexagesimal string representing hourangle (RA).
    Returns float value in decimal degrees.

    Raises:
        ValueError: if the string is not a valid sexagesimal string or a float.

    Examples:
        >>> parse_deg_or_hms('12:34:56.1')
        188.73375
        >>> parse_deg_or_hms('12h34m56.1s')
        188.73375
        >>> parse_deg_or_hms('-12 34 56.1')
        -188.73375
        >>> parse_deg_or_hms('188.73375')
        188.73375
        """
    return hourangle_to_decimal_deg(deg_or_hms)

def parse_deg_or_dms(deg_or_dms: str) -> float:
    """Parse a string as either a decimal degree or a sexagesimal degrees (DEC).
    Returns float value in decimal degrees.

    Raises:
        ValueError: if the string is not a valid sexagesimal string or a float.

    Examples:
        >>> parse_deg_or_dms('12:34:56.1')
        12.58225
        >>> parse_deg_or_dms('12°34′56.1″')
        12.58225
        >>> parse_deg_or_dms('-12 34 56.1')
        -12.58225
        >>> parse_deg_or_dms('12.58225')
        12.58225
        """
    return deg_to_decimal_deg(deg_or_dms)

def fmt_binning(binning: tuple[int, int]) -> str:
    """Format a binning value for display"""
    x, y = binning
    return f'{x}x{y}'

def parse_binning(binning: str) -> tuple[int, int]:
    """Parse a string as a binning value.
    Returns a tuple of two integers.

    Raises:
        ValueError: if the string is not a valid binning string.

    Examples:
        >>> parse_binning('1x1')
        (1, 1)
        >>> parse_binning('2x2')
        (2, 2)
        >>> parse_binning('2x1')
        (2, 1)
        >>> parse_binning('2')
        (2, 2)
        """
    try:
        xy = int(binning)
        return xy, xy
    except ValueError:
        pass
    try:
        x, y = binning.split('x')
        return int(x), int(y)
    except ValueError:
        raise ValueError(f'Invalid binning value: {binning}')

def fmt_subframe(subframe: tuple[int, int, int, int]) -> str:
    """Format a subframe value for display"""
    x1, x2, y1, y2 = subframe
    if x1 is None:
        x = '*'
    else:
        x = f'{x1}:{x2}'
    if y1 is None:
        y = '*'
    else:
        y = f'{y1}:{y2}'
    return f'[{x},{y}]'

def parse_subframe(subframe: str) -> tuple[int, int, int, int]:
    """Parse a string as a subframe value.
    Returns a tuple of four integers.

    Raises:
        ValueError: if the string is not a valid subframe string.

    Examples:
        >>> parse_subframe('[0:0,100:200]')
        (0, 0, 100, 200)
        >>> parse_subframe('[*, 0 : 100:200]')
        (None, None, 100, 200)
        """
    try:
        xx, yy = subframe.strip('[]').split(',')
        # print(subframe, ' => ', xx, yy)
        x1, x2 = (None, None) if '*' in xx else map(int, xx.split(':'))
        # print(x1, x2)
        y1, y2 = (None, None) if '*' in yy else map(int, yy.split(':'))
        # print(y1, y2)
        # print (x1, x2, y1, y2)
        return x1, x2, y1, y2

    except ValueError:
        raise ValueError(f'Invalid subframe value: {subframe}')

def is_decimal(deg_or_dms_or_hms: str) -> bool:
    """Check if a string is a decimal number"""
    try:
        float(deg_or_dms_or_hms)
        return True
    except ValueError:
        return False


def fmt_deg_min_sec(deg: float, sign=True, sep=':', precision=1) -> str:
    """Format degree arcminutes arcseconds for display"""
    return to_degminsec_sexagesimal(deg, sep=sep, sign=sign, precision=precision)


def fmt_hourangle_min_sec(ha: float, sep=':', precision = 1) -> str:
    """Format hourangle for display"""
    return to_hourangle_sexagesimal(ha, sep=sep, sign=False, precision=precision)


# def fmt_bool_to_led(b: bool|None, on='green', off='red'):
#     """Format shutter status for display"""
#     if b is None:
#         return '❌'
#     leds = {
#         'green': '🟢',
#         'red': '🔴',
#         'black': '⚫',
#         'grey': '⚪',
#         'orange': '🟠',
#     }
#     return leds[on] if b else leds[off]
