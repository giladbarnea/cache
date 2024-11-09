from __future__ import annotations

import dataclasses
from typing import Any, Callable, Type

try:
    from fastapi.encoders import jsonable_encoder
except ImportError:
    import datetime
    import json
    from collections import defaultdict, deque
    from decimal import Decimal
    from enum import Enum
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
        encoders_by_class_tuples: dict[Callable[[Any], Any], tuple[Any, ...]] = (
            defaultdict(tuple)
        )
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
        if callable(getattr(obj, "asdict", None)):
            return jsonable_encoder(
                obj.asdict(),
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
                if (
                    (not isinstance(key, str))
                    or (not key.startswith("_sa"))
                    and key in allowed_keys
                ):
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
            errors: list[Exception] = [e]
            try:
                data = vars(obj)
            except Exception as e:
                errors.append(e)
                raise ValueError(errors) from e
        return jsonable_encoder(
            data,
        )


def json_dumps(thing: object) -> str:
    return json.dumps(
        jsonable_encoder(thing),
        ensure_ascii=False,
        sort_keys=True,
        indent=None,
        separators=(",", ":"),
    )
