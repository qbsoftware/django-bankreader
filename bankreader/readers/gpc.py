from .base import BaseReader


class GpcReader(BaseReader):
    encoding = 'utf-8'
    label = 'GPC'

    def read(self, file_path):
        with open(file_path, encoding=self.encoding) as gpcfile:
            for row in gpcfile:
                yield {
                    'transaction_id': row[105:108],
                    'entry_date': row[108:114],
                    'accounted_date': row[108:114],
                    'remote_account_number': row[3:19],
                    'remote_account_name': row[19:39],
                    'amount': row[75:105],
                    # 'variable_symbol': row[],
                    # 'constant_symbol': row[],
                    # 'specific_symbol': row[],
                    # 'sender_description': row[],
                    # 'recipient_description': row[],
                }
