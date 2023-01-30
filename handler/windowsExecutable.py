import subprocess
import pefile


def handle_windows_executable(absolute_file_path, doc):
    file = pefile.PE(absolute_file_path)

    return {
        'headers': file.dump_info(),
    }
