from typing import TYPE_CHECKING, Dict, Type

if TYPE_CHECKING:
    from .base import BaseReader

readers: Dict[str, "BaseReader"] = {}


def get_reader_choices() -> list[tuple[str, str]]:
    return sorted([(key, reader.label) for key, reader in readers.items()], key=lambda x: x[1])


def register_reader(reader: Type["BaseReader"]) -> Type["BaseReader"]:
    readers[getattr(reader, "key", "%s.%s" % (reader.__module__, reader.__name__))] = reader()
    return reader
