from typing import IO, TYPE_CHECKING, Iterable
from zipfile import BadZipFile, ZipFile

if TYPE_CHECKING:
    from ..models import Transaction


class BaseReader:
    encoding = "utf-8"

    @property
    def label(self) -> str:
        raise NotImplementedError()

    def read_file(self, statement_file: IO) -> Iterable["Transaction"]:
        """Try to unpack ZIP archive and call read() for each file."""
        try:
            zip_file = ZipFile(statement_file)
        except BadZipFile:
            statement_file.seek(0)
            yield from self.read_transactions(statement_file)
        else:
            for zip_info in zip_file.filelist:
                with zip_file.open(zip_info) as f:
                    yield from self.read_file(f)

    def read_transactions(self, statement_file: IO) -> Iterable["Transaction"]:
        raise NotImplementedError()
