import re
from hashlib import blake2b
from sys import byteorder
from typing import Union


def safe_name(s):
    return re.sub(r"[^A-Za-z0-9_]+", "_", s).strip().lower()


def to_int64_key(k: Union[bytearray, bytes, memoryview, str, int]) -> int:
    if isinstance(k, str):
        k = k.encode()
    if isinstance(k, (bytearray, bytes, memoryview)):
        return int.from_bytes(blake2b(k, digest_size=8).digest(), byteorder, signed=True)
    elif isinstance(k, int):
        return ensure_int64(k)
    raise TypeError(f"{type(k)}")


INT64_MAX = 2**63 - 1  # max of signed int64: 2**63-1(+0x7fff_ffff_ffff_ffff)
INT64_MIN = -(2**63)  # min of signed int64: -2**63(-0x8000_0000_0000_0000)


def ensure_int64(i: int) -> int:
    if i > INT64_MAX:
        i = int.from_bytes(i.to_bytes(8, byteorder, signed=False), byteorder, signed=True)
    elif i < INT64_MIN:
        raise OverflowError("int too small to convert")
    return i


def camel_case(string: str) -> str:
    """Convert string into camel case.

    Args:
        string: String to convert.

    Returns:
        string: Camel case string.
    """
    string = re.sub(r"\w[\s\W]+\w", "", str(string))
    if not string:
        return string
    return lower_case(string[0]) + re.sub(r"[\-_\.\s]([a-z])", lambda matched: upper_case(matched.group(1)), string[1:])


def lower_case(string: str) -> str:
    """Convert string into lower case.

    Args:
        string: String to convert.

    Returns:
        string: Lowercase case string.
    """
    return str(string).lower()


def upper_case(string: str) -> str:
    """Convert string into upper case.

    Args:
        string: String to convert.

    Returns:
        string: Uppercase case string.
    """
    return str(string).upper()


def capital_case(string: str) -> str:
    """Convert string into capital case.
    First letters will be uppercase.

    Args:
        string: String to convert.

    Returns:
        string: Capital case string.
    """
    string = str(string)
    if not string:
        return string
    return upper_case(string[0]) + string[1:]


def pascal_case(string: str) -> str:
    """Convert string into pascal case.

    Args:
        string: String to convert.

    Returns:
        string: Pascal case string.
    """
    return capital_case(camel_case(string))
