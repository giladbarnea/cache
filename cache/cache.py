from __future__ import annotations

import abc
from collections.abc import Hashable
from functools import wraps
from typing import Any, Callable, Generic, Optional, TypeVar, Union

T = TypeVar("T")


class Cache(Generic[T]):
    @abc.abstractmethod
    def init(self) -> None:
        pass

    @abc.abstractmethod
    def get(self, key: Hashable) -> Optional[T]:
        pass

    @abc.abstractmethod
    def set(self, key: Hashable, value: T) -> None:
        pass

    @abc.abstractmethod
    def clear(self) -> int:
        pass


CachedFunction = TypeVar("CachedFunction", bound=Callable[..., Any])


def cache(
    cache_or_cache_init_param: Union[Cache[T], Any], cache_cls: type[Cache[T]] = None
) -> Callable[[CachedFunction], CachedFunction]:
    def decorator(func: CachedFunction) -> CachedFunction:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if cache_cls:
                cache_object = cache_cls(cache_or_cache_init_param)
            else:
                cache_object = cache_or_cache_init_param
            cache_object.init()
            wrapper._cache_object = cache_object
            for method in ("get", "set", "clear"):
                setattr(wrapper, method, getattr(cache_object, method))

            cached_value = cache_object.get((args, kwargs))
            if cached_value is not None:
                return cached_value
            result = func(*args, **kwargs)
            cache_object.set((args, kwargs), result)
            return result

        return wrapper

    return decorator
