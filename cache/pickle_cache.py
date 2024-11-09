from __future__ import annotations

import os
import pickle
from collections.abc import Hashable
from pathlib import Path
from typing import Any, Optional, TypeVar

from cache.cache import Cache
from cache.hash import get_hash

T = TypeVar("T")


class PickleCache(Cache[T]):
    def __init__(self, basedir: str = "~/.cache"):
        self.basedir = os.path.expanduser(basedir)
        self._cached_object_paths = set()

    def init(self):
        os.makedirs(self.basedir, exist_ok=True)

    def get(self, key: Hashable) -> Optional[T]:
        unique_hash: str = get_hash(key).hex()
        cache_file: str = os.path.join(self.basedir, f"{unique_hash}.pickle")
        if os.path.exists(cache_file):
            return self._pickle_load(cache_file)
        return None

    def set(self, key: Hashable, value: Any) -> str:
        unique_hash: str = get_hash(key).hex()
        cache_file_path: str = os.path.join(self.basedir, f"{unique_hash}.pickle")
        self._pickle_dump(cache_file_path, value)
        return cache_file_path

    def clear(self) -> int:
        """
        1. Clear all cached objects
        2. Recursively remove empty directories, up until (and including) the base directory
        """
        # print(f'clear({self._cached_object_paths = !r})')
        cached_object_count = len(self._cached_object_paths)
        for cache_file in self._cached_object_paths:
            Path(cache_file).unlink()
        self._cached_object_paths.clear()
        for root, dirs, _ in os.walk(self.basedir, topdown=False):
            # print(f'clear({root = !r}, {dirs = !r}, {_ = !r})')
            if not dirs:
                os.rmdir(root)
        return cached_object_count

    def _pickle_load(self, cache_file: str) -> T:
        with open(cache_file, "rb") as f:
            data = pickle.load(f)
        self._cached_object_paths.add(cache_file)
        return data

    def _pickle_dump(self, cache_file: str, data: Any):
        with open(cache_file, "wb") as f:
            pickle.dump(data, f)
        self._cached_object_paths.add(cache_file)
