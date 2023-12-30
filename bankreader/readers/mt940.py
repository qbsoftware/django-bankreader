import re
from typing import IO, Iterable

from mt940.parser import parse as mt940_parse

from ..models import Transaction
from .base import BaseReader


class MT940Reader(BaseReader):
    label = "MT940 (MultiCash)"

    def read_transactions(self, statement_file: IO) -> Iterable[Transaction]:
        for transaction in mt940_parse(statement_file):
            purpose = transaction.data.get("purpose")
            symbols = dict(re.findall(r"([KVS]S) ([0-9]{10})", purpose))
            account_match = re.search(r"([0-9]+-)?([0-9]{10})/([0-9]{4})", purpose)
            description = re.split("([KVS]S [0-9]{10}){3}", purpose)[-1]
            yield Transaction(
                transaction_id=transaction.data.get("customer_reference"),
                entry_date=transaction.data.get("entry_date"),
                accounted_date=transaction.data.get("date"),
                remote_account_number=account_match.group() if account_match else "",
                remote_account_name=transaction.data.get("applicant_name"),
                amount=transaction.data.get("amount").amount,
                variable_symbol=symbols.get("VS"),
                constant_symbol=symbols.get("KS"),
                specific_symbol=symbols.get("SS"),
                sender_description=description,
                recipient_description=description,
            )
