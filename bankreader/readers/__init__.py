readers = {}


def get_reader_choices():
    return sorted([(key, reader.label) for key, reader in readers.items()], key=lambda x: x[1])


def register_reader(reader):
    readers[getattr(reader, 'key', '%s.%s' % (reader.__module__, reader.__name__))] = reader()
    return reader
