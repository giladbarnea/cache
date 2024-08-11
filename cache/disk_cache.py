from __future__ import annotations

import abc
import dataclasses
from typing import Any, Callable, Generic, Type, TypeVar

_VERSION = 0

try:
    from fastapi.encoders import jsonable_encoder
except ImportError:
    import datetime
    import hashlib
    import json
    import os
    import pickle
    from collections import defaultdict, deque
    from decimal import Decimal
    from enum import Enum
    from functools import wraps
    from ipaddress import (
        IPv4Address,
        IPv4Interface,
        IPv4Network,
        IPv6Address,
        IPv6Interface,
        IPv6Network,
    )
    from pathlib import Path, PurePath
    from re import Pattern
    from types import GeneratorType
    from uuid import UUID

    def _pydantic_installed() -> bool:
        from importlib.util import find_spec

        return bool(find_spec("pydantic"))

    def _import_pydantic_BaseModel():
        try:
            from pydantic import BaseModel

            return BaseModel
        except ImportError:
            return None

    def _is_pydantic_2() -> bool:
        from pydantic.version import VERSION as PYDANTIC_VERSION

        return PYDANTIC_VERSION.startswith("2.")

    def _pydantic_model_dump(model):
        if _is_pydantic_2():
            return model.model_dump(mode="json")
        else:
            return model.dict()

    def decimal_encoder(dec_value: Decimal) -> int | float:
        if dec_value.as_tuple().exponent >= 0:
            return int(dec_value)
        else:
            return float(dec_value)

    ENCODERS_BY_TYPE: dict[Type[Any], Callable[[Any], Any]] = {
        bytes: lambda o: o.decode(),
        datetime.date: lambda o: o.isoformat(),
        datetime.datetime: lambda o: o.isoformat(),
        datetime.time: lambda o: o.isoformat(),
        datetime.timedelta: lambda td: td.total_seconds(),
        Decimal: decimal_encoder,
        Enum: lambda o: o.value,
        frozenset: list,
        deque: list,
        GeneratorType: list,
        IPv4Address: str,
        IPv4Interface: str,
        IPv4Network: str,
        IPv6Address: str,
        IPv6Interface: str,
        IPv6Network: str,
        Path: str,
        Pattern: lambda o: o.pattern,
        set: list,
        UUID: str,
    }
    if _pydantic_installed():
        from pydantic.color import Color
        from pydantic.networks import AnyUrl, NameEmail
        from pydantic.types import SecretBytes, SecretStr

        ENCODERS_BY_TYPE.update(
            {
                Color: str,
                NameEmail: str,
                SecretBytes: str,
                SecretStr: str,
                AnyUrl: str,
            }
        )
        if _is_pydantic_2():
            from pydantic_core import Url

            ENCODERS_BY_TYPE[Url] = str
        else:
            from pydantic import AnyUrl as Url

            ENCODERS_BY_TYPE[Url] = str

    def generate_encoders_by_class_tuples(
        type_encoder_map: dict[Any, Callable[[Any], Any]],
    ) -> dict[Callable[[Any], Any], tuple[Any, ...]]:
        encoders_by_class_tuples: dict[Callable[[Any], Any], tuple[Any, ...]] = defaultdict(tuple)
        for type_, encoder in type_encoder_map.items():
            encoders_by_class_tuples[encoder] += (type_,)
        return encoders_by_class_tuples

    encoders_by_class_tuples = generate_encoders_by_class_tuples(ENCODERS_BY_TYPE)

    def jsonable_encoder(
        obj: Any,
    ) -> Any:
        if (BaseModel := _import_pydantic_BaseModel()) and isinstance(obj, BaseModel):
            obj_dict = _pydantic_model_dump(obj)
            if "__root__" in obj_dict:
                obj_dict = obj_dict["__root__"]
            return jsonable_encoder(
                obj_dict,
            )
        if dataclasses.is_dataclass(obj):
            obj_dict = dataclasses.asdict(obj)
            return jsonable_encoder(
                obj_dict,
            )
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, PurePath):
            return str(obj)
        if isinstance(obj, (str, int, float, type(None))):
            return obj
        if isinstance(obj, dict):
            encoded_dict = {}
            allowed_keys = set(obj.keys())
            for key, value in obj.items():
                if (not isinstance(key, str)) or (not key.startswith("_sa")) and key in allowed_keys:
                    encoded_key = jsonable_encoder(
                        key,
                    )
                    encoded_value = jsonable_encoder(
                        value,
                    )
                    encoded_dict[encoded_key] = encoded_value
            return encoded_dict
        if isinstance(obj, (list, set, frozenset, GeneratorType, tuple, deque)):
            encoded_list = []
            for item in obj:
                encoded_list.append(
                    jsonable_encoder(
                        item,
                    )
                )
            return encoded_list

        if type(obj) in ENCODERS_BY_TYPE:
            return ENCODERS_BY_TYPE[type(obj)](obj)
        for encoder, classes_tuple in encoders_by_class_tuples.items():
            if isinstance(obj, classes_tuple):
                return encoder(obj)

        try:
            data = dict(obj)
        except Exception as e:
            errors: list[Exception] = []
            errors.append(e)
            try:
                data = vars(obj)
            except Exception as e:
                errors.append(e)
                raise ValueError(errors) from e
        return jsonable_encoder(
            data,
        )


def get_hash(thing: object) -> bytes:
    prefix = _VERSION.to_bytes(1, "big")
    digest = hashlib.md5(_json_dumps(thing).encode("utf-8")).digest()
    return prefix + digest[:-1]


def _json_dumps(thing: object) -> str:
    return json.dumps(
        jsonable_encoder(thing),
        ensure_ascii=False,
        sort_keys=True,
        indent=None,
        separators=(",", ":"),
    )


T = TypeVar("T")


class Cache(Generic[T]):
    @abc.abstractmethod
    def init(self) -> None:
        pass

    @abc.abstractmethod
    def get(self, key) -> T:
        pass

    @abc.abstractmethod
    def set(self, key, result: T) -> None:
        pass


class PickleCache(Cache):
    def __init__(self, basedir: str = "~/.cache"):
        self.basedir = os.path.expanduser(basedir)

    def init(self):
        os.makedirs(self.basedir, exist_ok=True)

    def get(self, key):
        unique_hash = get_hash(key).hex()
        cache_file = os.path.join(self.basedir, f"{unique_hash}.pickle")
        if os.path.exists(cache_file):
            with open(cache_file, "rb") as f:
                return pickle.load(f)
        return None

    def set(self, key, data):
        unique_hash = get_hash(key).hex()
        cache_file = os.path.join(self.basedir, f"{unique_hash}.pickle")
        with open(cache_file, "wb") as f:
            pickle.dump(data, f)


TFunc = TypeVar("TFunc", bound=Callable[..., Any])


# def disk_cache(dirpath: str = "~/.cache") -> Callable[[TFunc], TFunc]:
#     def decorator(func: TFunc) -> TFunc:
#         @wraps(func)
#         def wrapper(*args, **kwargs):
#             cache_dir = os.path.expanduser(dirpath)
#             os.makedirs(cache_dir, exist_ok=True)
#
#             unique_hash = get_hash((args, kwargs)).hex()
#             cache_file = os.path.join(cache_dir, f"{unique_hash}.pickle")
#
#             if os.path.exists(cache_file):
#                 get_console().print(f"💾✅ Loading cached result from {cache_file}")
#                 with open(cache_file, "rb") as f:
#                     return pickle.load(f)
#
#             get_console().print(f"💾🔍 Calculating result for {cache_file}")
#             result = func(*args, **kwargs)
#
#             with open(cache_file, "wb") as f:
#                 pickle.dump(result, f)
#
#             return result
#
#         return wrapper
#
#     return decorator


def cache(cache_or_cache_init_param: Cache | Any, cache_cls: type[Cache] = None) -> Callable[[TFunc], TFunc]:
    def decorator(func: TFunc) -> TFunc:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if cache_cls:
                cache = cache_cls(cache_or_cache_init_param)
            else:
                cache = cache_or_cache_init_param
            cache.init()

            value = cache.get((args, kwargs))
            if value is not None:
                return value
            result = func(*args, **kwargs)
            cache.set((args, kwargs), result)
            return result

        return wrapper

    return decorator


def disk_cache(pickle_cache: PickleCache | Path | str) -> Callable[[TFunc], TFunc]:
    cache_cls = None if isinstance(pickle_cache, PickleCache) else PickleCache
    return cache(pickle_cache, cache_cls)
