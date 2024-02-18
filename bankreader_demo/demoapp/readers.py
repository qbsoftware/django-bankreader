from bankreader.readers import register_reader
from bankreader.readers.best import BestReader
from bankreader.readers.csv import CsvReader


@register_reader
class KbBestReader(BestReader):
    label = "Komerční banka Best"


@register_reader
class KbCsvReader(CsvReader):
    label = "Komerční banka CSV"
    encoding = "cp1250"
    delimiter = ";"
    column_mapping = {
        "accounted_date": "Datum splatnosti",
        "entry_date": "Datum odepsani JB",
        "remote_account_number": "Protiucet/Kod banky",
        "remote_account_name": "Nazev protiuctu",
        "amount": "Castka",
        "variable_symbol": "VS",
        "constant_symbol": "KS",
        "specific_symbol": "SS",
        "transaction_id": "Identifikace transakce",
        "sender_description": "Popis prikazce",
        "recipient_description": "Popis pro prijemce",
    }
    date_format = "%Y-%m-%d"
    decimal_separator = ","
