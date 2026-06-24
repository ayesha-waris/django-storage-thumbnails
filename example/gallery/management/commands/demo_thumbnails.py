"""End-to-end demo: upload an image to S3 and generate thumbnails (synchronously).

    python manage.py demo_thumbnails
    python manage.py demo_thumbnails --image /path/to/real.jpg --name cat.jpg

Thumbnails are created during save(), so they're ready as soon as the upload
returns. No Celery/broker needed.
"""

from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image

from gallery.models import Photo


def _sample_image():
    buffer = BytesIO()
    Image.new("RGB", (800, 600), (30, 144, 255)).save(buffer, format="JPEG")
    return buffer.getvalue()


class Command(BaseCommand):
    help = "Upload an image and show the generated thumbnail URLs."

    def add_arguments(self, parser):
        parser.add_argument("--image", help="Path to an image file to upload.")
        parser.add_argument("--name", default="demo.jpg", help="Object name.")

    def handle(self, *args, **opts):
        if opts["image"]:
            with open(opts["image"], "rb") as fh:
                data = fh.read()
        else:
            data = _sample_image()

        photo = Photo()
        photo.image.save(opts["name"], ContentFile(data))  # uploads + thumbnails
        storage = photo.image.storage

        self.stdout.write(self.style.SUCCESS(f"Uploaded original: {photo.image.url}"))
        self.stdout.write("Thumbnails:")
        for key, url in photo.thumbnails.items():
            exists = storage.exists(
                storage.get_thumbnail_name(photo.image.name, key)
            )
            mark = (
                self.style.SUCCESS("ready")
                if exists
                else self.style.WARNING("missing")
            )
            self.stdout.write(f"  [{mark}] {key}: {url}")
