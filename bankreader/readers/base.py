import io
from zipfile import BadZipFile, ZipFile


class BaseReader:
    encoding = 'utf-8'

    @property
    def label(self):
        raise NotImplementedError()

    def read_archive(self, statement_file):
        ''' Try to unpack ZIP archive and call read() for each file.
        '''
        try:
            zip_file = ZipFile(statement_file)
        except BadZipFile:
            try:
                statement_file.seek(0)
            except io.UnsupportedOperation:
                pass
            for transaction in self.read_transactions(self._decode(statement_file)):
                yield transaction
        else:
            for zip_info in zip_file.filelist:
                with zip_file.open(zip_info) as f:
                    for transaction in self.read_transactions(self._decode(f)):
                        yield transaction

    def _decode(self, rows):
        return (
            row.decode(self.encoding) if type(row) == bytes else row
            for row in rows
        )

    def read_transactions(self, rows):
        raise NotImplementedError()
