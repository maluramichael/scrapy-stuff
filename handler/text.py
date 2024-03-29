import magic


def handle_text(absolute_file_path, doc):
    with open(absolute_file_path, 'r') as f:
        size = doc['stat']['size']

        try:
            m = magic.Magic(mime_encoding=True)
            encoding = m.from_buffer(f.read(1024))
        except Exception as e:
            return {
                'error': str(e)
            }

        result = {
            'encoding': encoding,
            'content': ''
        }

        if encoding == 'binary':
            return {
                'skip': 'binary'
            }

        f.seek(0)

        try:
            if size > 1024 * 1024:
                result['big_file'] = True
                result['content'] = f.read(1024 * 1024)
            else:
                result['big_file'] = False
                result['content'] = f.read()

            return result
        except Exception as e:
            return {
                'error': str(e)
            }
