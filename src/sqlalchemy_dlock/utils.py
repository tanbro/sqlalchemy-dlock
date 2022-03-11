import re
from hashlib import blake2b
from sys import byteorder
from typing import Union

SAFE_NAME_PATTERN = re.compile(r'[^A-Za-z0-9_]+')


def safe_name(s):
    return SAFE_NAME_PATTERN.sub('_', s).strip().lower()


def to_int64_key(k: Union[bytearray, bytes, memoryview, str, int]) -> int:
    if isinstance(k, str):
        k = k.encode()
    if isinstance(k, (bytearray, bytes, memoryview)):
        return int.from_bytes(blake2b(k, digest_size=8).digest(), byteorder, signed=True)
    elif isinstance(k, int):
        return ensure_int64(k)
    raise TypeError('{}'.format(type(k)))


INT64_MAX = 2**63-1  # max of signed int64: 2**63-1(+0x7fff_ffff_ffff_ffff)
INT64_MIN = -2**63  # min of signed int64: -2**63(-0x8000_0000_0000_0000)


def ensure_int64(i: int) -> int:
    if i > INT64_MAX:
        i = int.from_bytes(
            i.to_bytes(8, byteorder, signed=False),
            byteorder, signed=True
        )
    elif i < INT64_MIN:
        raise OverflowError('int too small to convert')
    return i
