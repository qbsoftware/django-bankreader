import datetime
import decimal
from zipfile import BadZipFile, ZipFile

from .base import BaseReader


class BestReader(BaseReader):
    label = 'Best'
    encoding = 'cp1250'

    def read(self, statement_file):
        try:
            zip_file = ZipFile(statement_file)
        except BadZipFile:
            statement_file.seek(0)
            return self._read(statement_file)
        else:
            for zip_info in zip_file.filelist:
                with zip_file.open(zip_info) as okmfile:
                    for transaction in self._read(okmfile):
                        yield transaction

    def _read(self, okmfile):
        for row in okmfile:
            if type(row) == bytes:
                row = row.decode(self.encoding)
            prefix = row[:2]
            if prefix == '52':
                # process transaction
                yield {
                    'transaction_id': row[86:117].strip(),
                    'entry_date': datetime.datetime.strptime(row[167:175], '%Y%m%d').date(),
                    'accounted_date': datetime.datetime.strptime(row[175:183], '%Y%m%d').date(),
                    'remote_account_number': '%s-%s/%s' % (
                        row[23:29],
                        row[29:39],
                        row[42:46] if row[39:42] == '000' else row[39:46],
                    ),
                    # 'remote_account_name': row[],
                    'amount': decimal.Decimal('%s%s.%s' % ('-' if row[46] == '0' else '', row[50:63], row[63:65])),
                    'variable_symbol': int(row[127:137]),
                    'constant_symbol': int(row[137:147]),
                    'specific_symbol': int(row[147:157]),
                    'sender_description': row[269:409].strip(),
                    'recipient_description': row[209:239].strip(),
                }
