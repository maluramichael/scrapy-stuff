from PIL import Image
from PIL.ExifTags import TAGS


def handle_image(absolute_file_path, doc):
    mime = doc['mime']

    if mime not in ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/tiff', 'image/webp', 'image/heic', 'image/jpg']:
        return {
            'skip': 'not an readable image'
        }

    try:
        with Image.open(absolute_file_path) as image:
            exif = image.getexif()
            exif_table = {}

            for k, v in exif.items():
                tag = TAGS.get(k)

                if isinstance(v, bytes):
                    continue

                if tag is None:
                    continue

                lower_tag = tag.lower()

                if lower_tag in ['software', 'make', 'model', 'datetimeoriginal', 'datetimedigitized', 'datetime', 'rating']:
                    if v is int:
                        exif_table[lower_tag] = v
                    elif v is str:
                        exif_table[lower_tag] = v.strip()

            return exif_table
    except Exception as e:
        return {
            'error': str(e)
        }
