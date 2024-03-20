import re
from hashlib import blake2b
from sys import byteorder


def safe_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", s).strip().lower()


def to_int64_key(k) -> int:
    if isinstance(k, str):
        k = k.encode()
    if isinstance(k, (bytearray, bytes, memoryview)):
        return int.from_bytes(blake2b(k, digest_size=8).digest(), byteorder, signed=True)
    if isinstance(k, int):
        return ensure_int64(k)
    raise TypeError(f"{type(k)}")


def ensure_int64(i: int) -> int:
    """ensure the integer in PostgreSQL advisory lock's range (Signed INT64)

    * max of signed int64: ``2**63-1`` (``+0x7FFF_FFFF_FFFF_FFFF``)
    * min of signed int64: ``-2**63`` (``-0x8000_0000_0000_0000``)

    Returns:
        Signed int64 key
    """
    ## no force convert UINT greater than 2**63-1 to SINT
    # if i > 0x7FFF_FFFF_FFFF_FFFF:
    #     return int.from_bytes(i.to_bytes(8, byteorder, signed=False), byteorder, signed=True)
    if not isinstance(i, int):
        raise TypeError(f"int type expected, but actual type is {type(i)}")
    if i > 0x7FFF_FFFF_FFFF_FFFF:
        raise OverflowError("int too big")
    if i < -0x8000_0000_0000_0000:
        raise OverflowError("int too small")
    return i


def camel_case(s: str) -> str:
    """Convert string into camel case.

    Args:
        s: String to convert

    Returns:
        Camel case string.
    """
    s = re.sub(r"\w[\s\W]+\w", "", str(s))
    if not s:
        return s
    return lower_case(s[0]) + re.sub(r"[\-_\.\s]([a-z])", lambda matched: upper_case(matched.group(1)), s[1:])


def lower_case(s: str) -> str:
    """Convert string into lower case.

    Args:
        s: String to convert

    Returns:
        Lowercase case string.
    """
    return str(s).lower()


def upper_case(s: str) -> str:
    """Convert string into upper case.

    Args:
        s: String to convert

    Returns:
        Uppercase case string.
    """
    return str(s).upper()


def capital_case(s: str) -> str:
    """Convert string into capital case.
    First letters will be uppercase.

    Args:
        s: String to convert

    Returns:
        Capital case string.
    """
    s = str(s)
    if not s:
        return s
    return upper_case(s[0]) + s[1:]


def pascal_case(s: str) -> str:
    """Convert string into pascal case.

    Args:
        s: String to convert

    Returns:
        Pascal case string.
    """
    return capital_case(camel_case(s))
