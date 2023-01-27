from zipfile import ZipFile


def handle_zip(absolute_file_path, doc):
    files = []

    with ZipFile(absolute_file_path) as myzip:
        files = myzip.namelist()

    return {
        'files': files
    }
