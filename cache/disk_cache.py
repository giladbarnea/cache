import os
import pickle
from functools import wraps


def _positive_hash(s) -> int:
    return hash(s) + 2**63


def disk_cache(dirpath: str = "~/.cache"):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_dir = os.path.expanduser(dirpath)
            os.makedirs(cache_dir, exist_ok=True)

            unique_filename = str(_positive_hash(str(args) + str(kwargs)))
            cache_file = os.path.join(cache_dir, f"{unique_filename}.pickle")

            if os.path.exists(cache_file):
                get_console().print(f"💾✅ Loading cached result from {cache_file}")
                with open(cache_file, "rb") as f:
                    return pickle.load(f)

            get_console().print(f"💾🔍 Calculating result for {cache_file}")
            result = func(*args, **kwargs)

            with open(cache_file, "wb") as f:
                pickle.dump(result, f)

            return result

        return wrapper

    return decorator
