"""Formatting varius values for display"""
from __future__ import annotations

from pyaraucaria.coordinates import to_degminsec_sexagesimal, to_hourangle_sexagesimal, hourangle_to_decimal_deg, \
    deg_to_decimal_deg


def fmt_domeshutter(shutter: int | None):
    """Format shutter status for display"""
    if shutter is None:
        return 'n/a'
    return [
        'Open',
        'Closed',
        'Opening',
        'Closing',
        'Error',
    ][shutter]

def fmt_camerastate(state: int | None):
    """Format shutter status for display"""
    if state is None:
        return 'n/a'
    return [
        'Idle',
        'Waiting',
        'Exposing',
        'Reading',
        'Downloading',
        'Error'
    ][state]

def fmt_coverstate(state: int | None):
    """Format cover status for display"""
    if state is None:
        return 'n/a'
    return [
        'unknown',
        'Closed',
        'Moving',
        'Open'
    ][state]

def fmt_calibratorstate(state: int | None):
    """Format cover status for display"""
    if state is None:
        return 'n/a'
    return [
        'unknown',
        'Off',
        'Not Ready',
        'Ready'
    ][state]

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
