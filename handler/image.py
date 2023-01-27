from PIL import Image
from PIL.ExifTags import TAGS


def handle_image(absolute_file_path, doc):
    try:
        image = Image.open(absolute_file_path)
        exif = image.getexif()
        exif_table = {}

        for k, v in exif.items():
            tag = TAGS.get(k)

            if isinstance(v, bytes):
                continue

            if tag in ['Software', 'Make', 'Model', 'DateTimeOriginal', 'DateTimeDigitized', 'DateTime']:
                exif_table[tag] = v

        image.close()

        return exif_table
    except Exception as e:
        return {}
