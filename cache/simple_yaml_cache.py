# Better take this from to/to.py
def yaml_str_representer(dumper, data):
    if len(data.splitlines()) > 1:  # check for multiline string
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml = YAML(typ="safe", pure=True)
yaml.default_flow_style = False
yaml.indent = 4
yaml.preserve_quotes = True
yaml.representer.add_representer(str, yaml_str_representer)
yaml.sequence_dash_offset = 2
yaml.sort_base_mapping_type_on_output = True
yaml.sort_keys = True
yaml.width = 999


YAML_LOADS_CACHE = {}


def yaml_loads(data: str, *, cache=False) -> dict:
    if not cache:
        return yaml.load(data)
    data_hash = get_hash(data).hex()
    if data_hash in YAML_LOADS_CACHE:
        return YAML_LOADS_CACHE[data_hash]
    YAML_LOADS_CACHE[data_hash] = yaml.load(data)
    return YAML_LOADS_CACHE[data_hash]


def yaml_load(file_path: Path, *, cache=False) -> dict:
    with file_path.open("r") as file:
        return yaml_loads(file.read(), cache=cache)


def yaml_dump(data: dict, file_path: Path):
    with file_path.open("w") as file:
        yaml.dump(data, file)


def yaml_dumps(data: dict) -> str:
    import io

    output = io.StringIO()
    yaml.dump(data, output)
    return output.getvalue()


def init_yaml_cache_file(path) -> Path:
    cache_path = Path(path)
    cache_path.touch(exist_ok=True)
    if not cache_path.read_text():
        yaml_dump({}, cache_path)
    return cache_path


T = TypeVar("T")
class SimpleYamlCache(Generic[T]):
    def __init__(
            self, path: Path, parse_func: Callable[[dict], T], to_dict_func: Callable[[T], dict] = jsonable_encoder
    ):
        self.path = init_yaml_cache_file(path)
        self.parse_func = parse_func
        self.to_dict_func = to_dict_func
        self._nickname = path.stem.upper().replace("_", " ").replace("-", " ")

    def get(self, key: str) -> Union[T, None]:
        cache = yaml_loads(self.path.read_text())
        if key in cache:
            console.rule(
                f"Found cached {self._nickname} for {key!r} out of {len(cache)} cached entries",
                style="bold bright green",
            )
            return self.parse_func(cache[key])
        console.rule(f"No cached {self._nickname} for {key!r}. Cache count: {len(cache)}", style="bold bright cyan")
        return None

    def set(self, key: str, value: T):
        cache = yaml_loads(self.path.read_text())
        count_before = len(cache)
        data = self.to_dict_func(value)
        cache[key] = data
        console.rule(
            f"Cached {self._nickname} for {key!r}. Cache count: {count_before}->{len(cache)}", style="bold bright blue"
        )
        yaml_dump(cache, self.path)
