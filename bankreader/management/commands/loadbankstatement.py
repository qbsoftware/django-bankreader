import os
import traceback
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser
from django.db.models import Q

from ...models import Account, AccountStatement


class Command(BaseCommand):
    help = "Load Bank Statement"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--account", dest="account", type=str)
        parser.add_argument("input_file", nargs="+", type=str)

    def handle(self, **options: Any) -> None:
        # get account
        try:
            q = Q(pk=int(options["account"]))
        except ValueError:
            q = Q(name=options["account"]) | Q(iban=options["account"])

        try:
            account = Account.objects.filter(reader__isnull=False).get(q)
        except Account.DoesNotExist:
            self.stderr.write(self.style.ERROR('Account "%s" does not exist' % options["account"]))
            return
        except Account.MultipleObjectsReturned:
            self.stderr.write(self.style.ERROR('Account "%s" is ambiguous' % options["account"]))
            return

        reader = account.get_reader()
        assert reader is not None

        for input_file in options["input_file"]:
            self.stdout.write(
                self.style.HTTP_INFO('Loading bank statement "%s" for account "%s"' % (input_file, account))
            )
            try:
                with open(input_file, "rb") as f:
                    transactions = tuple(reader.read_file(f))
            except Exception as e:
                if settings.DEBUG:
                    traceback.print_exc()
                self.stderr.write(self.style.ERROR('Error loading bank statement "%s": %s' % (input_file, e)))
                continue
            if not transactions:
                self.stderr.write(
                    self.style.ERROR('The account statement "%s" doesn\'t contain any transaction data.' % input_file)
                )
                continue
            statement = AccountStatement(account=account, statement=os.path.basename(input_file))
            messages = statement.save_with_transactions(transactions)
            for message in messages:
                self.stderr.write(self.style.WARNING(message))
            self.stdout.write(
                self.style.HTTP_INFO(
                    "Successfully loaded %d transactions (%d new) from %s."
                    % (len(transactions), len(transactions) - len(messages), input_file)
                )
            )
