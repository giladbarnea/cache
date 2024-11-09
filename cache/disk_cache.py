from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Union

from cache.cache import CachedFunction, cache
from cache.pickle_cache import PickleCache

# def disk_cache(dirpath: str = "~/.cache") -> Callable[[CachedFunction], CachedFunction]:
#     def decorator(func: CachedFunction) -> CachedFunction:
#         @wraps(func)
#         def wrapper(*args, **kwargs):
#             cache_dir = os.path.expanduser(dirpath)
#             os.makedirs(cache_dir, exist_ok=True)
#
#             unique_hash = get_hash((args, kwargs)).hex()
#             cache_file = os.path.join(cache_dir, f"{unique_hash}.pickle")
#
#             if os.path.exists(cache_file):
#                 get_console().print(f"💾✅ Loading cached value from {cache_file}")
#                 with open(cache_file, "rb") as f:
#                     return pickle.load(f)
#
#             get_console().print(f"💾🔍 Calculating value for {cache_file}")
#             value = func(*args, **kwargs)
#
#             with open(cache_file, "wb") as f:
#                 pickle.dump(value, f)
#
#             return value
#
#         return wrapper
#
#     return decorator


def disk_cache(
    pickle_cache: Union[PickleCache, Path, str],
) -> Callable[[CachedFunction], CachedFunction]:
    cache_cls = None if isinstance(pickle_cache, PickleCache) else PickleCache
    return cache(pickle_cache, cache_cls)
