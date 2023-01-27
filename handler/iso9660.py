import pycdlib


def handle_iso9660(absolute_file_path, doc):
    iso = pycdlib.PyCdlib()
    iso.open(absolute_file_path)
    files = []
    iso_path = '/'

    try:
        for dirname, dirlist, filelist in iso.walk(iso_path=iso_path):
            files.append(dirname)
            for file in filelist:
                files.append(iso_path + file)
    except Exception as e:
        pass

    iso.close()

    return {
        'files': files
    }
