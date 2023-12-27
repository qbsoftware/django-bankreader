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
        "Datum splatnosti": "accounted_date",
        "Datum odepsani JB": "entry_date",
        "Protiucet/Kod banky": "remote_account_number",
        "Nazev protiuctu": "remote_account_name",
        "Castka": "amount",
        "VS": "variable_symbol",
        "KS": "constant_symbol",
        "SS": "specific_symbol",
        "Identifikace transakce": "transaction_id",
        "Popis prikazce": "sender_description",
        "Popis pro prijemce": "recipient_description",
    }
    date_format = "%Y-%m-%d"
    decimal_separator = ","
