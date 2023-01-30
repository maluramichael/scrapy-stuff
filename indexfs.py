import hashlib
import os
import re
import sys

import magic
from opensearchpy import helpers as opensearch_helpers
from tqdm import tqdm

from handler.image import handle_image
from handler.iso9660 import handle_iso9660
from handler.text import handle_text
from handler.video import handle_video
from handler.windowsExecutable import handle_windows_executable
from handler.zip import handle_zip
from opensearch import opensearch

ignored_files = [r"\.DS_Store", r"\._.*", r"Thumbs\.db", r"aquota\.user", r"aquota\.group", r"lost\+found", r"desktop\.ini"]
ignored_dirs = [r".*\.git", r".*venv", r".*\.dtrash", r".*\.idea", r".*\.vscode", r".*/pr0gram"]
ignored_mime_types = ['application/octet-stream', 'application/x-bittorrent']
file_filter_pattern = "(" + ")|(".join(ignored_files) + ")"
dir_filter_pattern = "(" + ")|(".join(ignored_dirs) + ")"
start_dir = "/Volumes/tank/isos"

# parse --reindex parameter
reindex_existing_files = False

if '--reindex' in sys.argv:
    reindex_existing_files = True

# parse first argument as start directory
if len(sys.argv) > 1:
    start_dir = sys.argv[1]

if not opensearch.indices.exists('fs'):
    opensearch.indices.create('fs', body={
        'settings': {
            'index': {
                'number_of_shards': 1
            }
        }
    })


def bulk_insert(documents):
    opensearch_helpers.bulk(opensearch, documents, index='fs', refresh=True)


def get_existing_files_from_opensearch(directory_path):
    result = opensearch.search(index='fs', body={
        'query': {
            'match': {
                'path': directory_path
            }
        },
        'size': 10000
    })

    for hit in result['hits']['hits']:
        if 'filename' in hit['_source']:
            yield hit['_source']['filename']

        continue


def main():
    unknown_mime_types = set()

    for dirpath, dirnames, filenames in os.walk(start_dir):
        dirname = os.path.basename(dirpath)
        if re.match(dir_filter_pattern, dirpath):
            continue

        existing_files = []

        if not reindex_existing_files:
            existing_files = get_existing_files_from_opensearch(dirpath.replace('/Volumes', ''))

        filtered_files = [filename for filename in filenames if not re.match(file_filter_pattern, filename) and filename not in existing_files]
        docs = []

        if len(filtered_files) == 0:
            print(f"Skipping {dirpath} because there are no new files")
            continue

        print(f"Processing {len(filtered_files)} in {dirpath}")

        for filename in tqdm(filtered_files, desc=dirname, unit="files", position=0, leave=True):
            absolute_file_path = os.path.join(dirpath, filename)
            id = hashlib.sha256(absolute_file_path.encode('utf-8')).hexdigest()
            mime: str = magic.from_file(absolute_file_path, mime=True)
            stats = os.stat(absolute_file_path)

            doc = {
                'filename': filename,
                'path': dirpath.replace('/Volumes', ''),
                'mime': mime,
                'stat': {
                    'size': stats.st_size,
                    'mtime': stats.st_mtime,
                    'ctime': stats.st_ctime,
                    'atime': stats.st_atime,
                    'mode': stats.st_mode,
                },
            }

            meta_data = None

            if mime in ignored_mime_types:
                continue

            if mime.startswith('image/'):
                meta_data = handle_image(absolute_file_path, doc)
            elif mime.startswith('text/') or mime in ['application/x-wine-extension-ini']:
                meta_data = handle_text(absolute_file_path, doc)
            elif mime.startswith('video/'):
                meta_data = handle_video(absolute_file_path, doc)
            elif mime == 'application/x-iso9660-image':
                meta_data = handle_iso9660(absolute_file_path, doc)
            elif mime == 'application/zip':
                meta_data = handle_zip(absolute_file_path, doc)
            elif mime == 'application/vnd.microsoft.portable-executable':
                meta_data = handle_windows_executable(absolute_file_path, doc)
            elif mime == 'inode/x-empty':
                meta_data = {'skip': 'empty file'}
            else:
                unknown_mime_types.add(mime)
                continue

            if meta_data is None:
                continue

            if 'error' in meta_data:
                print(f"Error while processing {absolute_file_path}: {meta_data['error']}")
            elif 'skip' in meta_data:
                print(f"Skip further processing of the file. But still indexing it. {absolute_file_path}")


            doc['meta_data'] = meta_data
            docs.append({
                '_id': id,
                '_index': 'fs',
                **doc
            })

            if len(docs) >= 100:
                bulk_insert(docs)
                docs = []

        if len(docs) > 0:
            bulk_insert(docs)

    print(f"Unknown mime types: {unknown_mime_types}")


if __name__ == '__main__':
    main()
