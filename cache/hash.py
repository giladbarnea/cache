from __future__ import annotations

import hashlib
from collections.abc import Hashable

from cache.serialize import json_dumps

_VERSION = 0


def get_hash(thing: Hashable) -> bytes:
    prefix = _VERSION.to_bytes(1, "big")
    digest = hashlib.md5(json_dumps(thing).encode("utf-8")).digest()
    return prefix + digest[:-1]
