import boto3
from django.core.files.base import ContentFile
from django.test import SimpleTestCase
from django.test import override_settings
from moto import mock_aws
from PIL import Image

from thumbnail_storage import ThumbnailS3Storage

from .utils import make_image

BUCKET = "test-thumbnails-bucket"


@mock_aws
@override_settings(THUMBNAIL_SIZES={"small": (10, 10), "med": (20, 20)})
class ThumbnailS3StorageTests(SimpleTestCase):
    def setUp(self):
        conn = boto3.resource("s3", region_name="us-east-1")
        conn.create_bucket(Bucket=BUCKET)
        self.storage = ThumbnailS3Storage(
            bucket_name=BUCKET, region_name="us-east-1"
        )

    def test_thumbnails_created_on_save(self):
        name = self.storage.save(
            "photos/cat.jpg", ContentFile(make_image().read())
        )
        self.assertEqual(name, "photos/cat.jpg")

        for key, (max_w, max_h) in {"small": (10, 10), "med": (20, 20)}.items():
            thumb_name = f"thumbnails/{key}/photos/cat.jpg"
            self.assertTrue(
                self.storage.exists(thumb_name), f"{thumb_name} missing on S3"
            )
            with self.storage.open(thumb_name) as fh:
                img = Image.open(fh)
                img.load()
            self.assertLessEqual(img.width, max_w)
            self.assertLessEqual(img.height, max_h)

    def test_thumbnail_url_points_at_thumbnail_key(self):
        self.storage.save("photos/cat.jpg", ContentFile(make_image().read()))
        url = self.storage.thumbnail_url("photos/cat.jpg", "small")
        self.assertIn("thumbnails/small/photos/cat.jpg", url)

    def test_delete_cleans_up_thumbnails(self):
        self.storage.save("photos/cat.jpg", ContentFile(make_image().read()))
        self.assertTrue(
            self.storage.exists("thumbnails/small/photos/cat.jpg")
        )

        self.storage.delete("photos/cat.jpg")

        self.assertFalse(self.storage.exists("photos/cat.jpg"))
        self.assertFalse(
            self.storage.exists("thumbnails/small/photos/cat.jpg")
        )
