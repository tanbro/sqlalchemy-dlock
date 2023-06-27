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


def ensure_int64(i: int) -> int:
    """ensure the integer in PostgreSQL advisory lock's range (Signed INT64)

    * max of signed int64: ``2**63-1`` (``+0x7FFF_FFFF_FFFF_FFFF``)
    * min of signed int64: ``-2**63`` (``-0x8000_0000_0000_0000``)
    """
    if i > 0x7FFFFFFFFFFFFFFF:
        i = int.from_bytes(i.to_bytes(8, byteorder, signed=False), byteorder, signed=True)
    elif i < -0x8000000000000000:
        raise OverflowError("int too small to convert")
    return i


def camel_case(s: str) -> str:
    """Convert string into camel case.

    Args:
        s: String to convert.

    Return:
        Camel case string.
    """
    s = re.sub(r"\w[\s\W]+\w", "", str(s))
    if not s:
        return s
    return lower_case(s[0]) + re.sub(r"[\-_\.\s]([a-z])", lambda matched: upper_case(matched.group(1)), s[1:])


def lower_case(s: str) -> str:
    """Convert string into lower case.

    Args:
        s: String to convert.

    Return:
        Lowercase case string.
    """
    return str(s).lower()


def upper_case(s: str) -> str:
    """Convert string into upper case.

    Args:
        s: s to convert.

    Return:
        Uppercase case string.
    """
    return str(s).upper()


def capital_case(s: str) -> str:
    """Convert string into capital case.
    First letters will be uppercase.

    Args:
        s: String to convert.

    Return:
        Capital case string.
    """
    s = str(s)
    if not s:
        return s
    return upper_case(s[0]) + s[1:]


def pascal_case(s: str) -> str:
    """Convert string into pascal case.

    Args:
        s: String to convert.

    Return:
        Pascal case string.
    """
    return capital_case(camel_case(s))
