import csv
import datetime
import decimal
import re
from logging import getLogger
from typing import IO, Any, Dict, Iterable

from bankreader.models import Transaction

from .base import BaseReader


logger = getLogger(__name__)


class CsvReader(BaseReader):
    label = "CSV"
    column_mapping: Dict[str, str] = {}
    date_format = "%Y-%m-%d"
    delimiter = ","
    quotechar = '"'
    encoding = "utf-8"
    decimal_separator = "."
    decimalregex = re.compile(r"[^0-9,-]")

    def __init__(self) -> None:
        self.decimal_cleaner = re.compile(r"[^0-9-%s]" % self.decimal_separator)

    def read_transactions(self, statemen_file: IO) -> Iterable[Transaction]:
        rows = statemen_file.read().decode(self.encoding).split("\n")
        column_mapping: Dict[str, int] = {}
        csv_reader = csv.reader(rows, delimiter=self.delimiter, quotechar=self.quotechar)
        for row in csv_reader:
            if not column_mapping:
                try:
                    column_mapping = {key: row.index(csv_key) for csv_key, key in self.column_mapping.items()}
                except ValueError:
                    pass
                continue
            try:
                data = {key: self.get_value(key, row[column_mapping[key]]) for key in column_mapping}
            except IndexError:
                logger.error("Error reading CSV file: %s", dict(row=row, column_mapping=column_mapping))
                continue
            yield Transaction(**data)

    def get_value(self, key: str, value: str) -> Any:
        if key in ("accounted_date", "entry_date"):
            return datetime.datetime.strptime(value, self.date_format).date()
        elif key == "amount":
            return decimal.Decimal(self.decimal_cleaner.sub("", value).replace(self.decimal_separator, "."))
        elif key.endswith("_symbol"):
            return int(value) if value.isdigit() else 0
        else:
            return value
