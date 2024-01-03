import datetime
from typing import IO, Iterable

from bankreader.models import Transaction

from .base import BaseReader


class GpcReader(BaseReader):
    label = "GPC"

    def read_transactions(self, statemen_file: IO) -> Iterable[Transaction]:
        rows = statemen_file.read().decode(self.encoding).split("\n")
        transaction = None
        for row in rows:
            # first row of transaction data
            if row[:3] == "075":
                if transaction:
                    # send previous transaction data
                    if "entry_date" not in transaction:
                        transaction["entry_date"] = transaction["accounted_date"]
                    yield Transaction(**transaction)
                    transaction = None
                if row[60] in "12":
                    # create new transaction data
                    amount = int(row[48:60]) / 100.0
                    transaction = {
                        "transaction_id": row[35:48],
                        "accounted_date": datetime.datetime.strptime(row[122:128], "%d%m%y").date(),
                        "remote_account_number": "%s-%s/%s"
                        % (
                            row[19:25],
                            row[25:35],
                            row[73:77],
                        ),
                        "remote_account_name": row[97:117].strip(),
                        "amount": amount if row[60] == "2" else -amount,
                        "variable_symbol": int(row[61:71]),
                        "constant_symbol": int(row[77:81]),
                        "specific_symbol": int(row[81:91]),
                    }
            # second row of transaction data
            elif transaction and row[:3] == "076":
                try:
                    transaction["entry_date"] = datetime.datetime.strptime(row[29:35], "%d%m%y").date()
                except ValueError:
                    transaction["entry_date"] = transaction["accounted_date"]
                transaction["sender_description"] = row[35:127].strip()
            # third row of transaction data
            elif transaction and row[:3] == "078":
                transaction["recipient_description"] = row[3:127].strip()
            # 4th row of transaction data
            elif transaction and row[:3] == "079":
                transaction["recipient_description"] += row[3:73].strip()
        if transaction:
            if "entry_date" not in transaction:
                transaction["entry_date"] = transaction["accounted_date"]
            yield Transaction(**transaction)
