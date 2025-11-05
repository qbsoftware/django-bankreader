from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseReader

readers: dict[str, "BaseReader"] = {}


def get_reader_choices() -> list[tuple[str, str]]:
    return sorted([(key, reader.label) for key, reader in readers.items()], key=lambda x: x[1])


def register_reader(reader: type["BaseReader"]) -> type["BaseReader"]:
    readers[getattr(reader, "key", f"{reader.__module__}.{reader.__name__}")] = reader()
    return reader
