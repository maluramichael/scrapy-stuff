from zipfile import ZipFile


def handle_zip(absolute_file_path, doc):
    with ZipFile(absolute_file_path) as myzip:
        files = myzip.namelist()

        return {
            'files': files
        }
