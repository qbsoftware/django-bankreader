import csv
import datetime
import decimal
import re

from .base import BaseReader


class CsvReader(BaseReader):
    column_mapping = {}
    date_format = '%Y-%m-%d'
    delimiter = ','
    quotechar = '"'
    encoding = 'utf-8'
    decimal_separator = '.'
    decimalregex = re.compile(r'[^0-9,-]')

    def __init__(self):
        self.decimal_cleaner = re.compile(r'[^0-9-%s]' % self.decimal_separator)

    def read(self, file_path):
        with open(file_path, encoding=self.encoding) as csvfile:
            column_mapping = {}
            for row in csv.reader(csvfile, delimiter=self.delimiter, quotechar=self.quotechar):
                if not column_mapping:
                    try:
                        column_mapping = {key: row.index(csv_key) for csv_key, key in self.column_mapping.items()}
                    except ValueError:
                        pass
                    continue
                yield {
                    key: self.get_value(key, row[column_mapping[key]])
                    for key in column_mapping
                }

    def get_value(self, key, value):
        if key in ('accounted_date', 'entry_date'):
            return datetime.datetime.strptime(value, self.date_format).date()
        elif key == 'amount':
            return decimal.Decimal(self.decimal_cleaner.sub('', value).replace(self.decimal_separator, '.'))
        elif key.endswith('_symbol'):
            return int(value) if value.isdigit() else 0
        else:
            return value
