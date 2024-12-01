from __future__ import annotations

from hashlib import blake2b
from importlib import import_module
from io import BytesIO
from string import Template
from sys import byteorder
from typing import TYPE_CHECKING, Any, Mapping, Type, Union

from .lock.base import BaseAsyncSadLock, BaseSadLock

if TYPE_CHECKING:  # pragma: no cover
    from _typeshed import ReadableBuffer


def to_int64_key(k: Union[int, str, ReadableBuffer]) -> int:
    if isinstance(k, int):
        return ensure_int64(k)
    if isinstance(k, str):
        k = k.encode()
    return int.from_bytes(blake2b(k, digest_size=8).digest(), byteorder, signed=True)


def to_str_key(key: Union[str, int, float, ReadableBuffer]) -> str:
    if isinstance(key, str):
        return key
    if isinstance(key, (int, float)):
        return str(key)
    if isinstance(key, (bytes, bytearray)):
        return key.decode()
    if key is None:
        raise TypeError(type(None).__name__)
    return BytesIO(key).read().decode()


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


def find_lock_class(engine_name: str, is_asyncio: bool = False) -> Union[Type[BaseSadLock], Type[BaseAsyncSadLock]]:
    conf: Mapping[str, Any] = getattr(
        import_module(".registry", __package__), "ASYNCIO_REGISTRY" if is_asyncio else "REGISTRY"
    )[engine_name]
    package: Union[str, None] = conf.get("package")
    if package:
        package = Template(package).safe_substitute(package=__package__)
    module = import_module(conf["module"], package)
    class_ = getattr(module, conf["class"])
    return class_
