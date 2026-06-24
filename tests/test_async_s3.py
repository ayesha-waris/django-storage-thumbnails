"""Async S3 path.

Celery is not installed in the test env, so ``enqueue_thumbnails`` falls back
to running the job inline — which still exercises the full async code path:
save original only -> enqueue -> worker re-reads original from S3 -> writes
thumbnails. (With a broker, ``.delay()`` would run the same ``run_thumbnail_job``
in a worker instead.)
"""

import boto3
from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.test import SimpleTestCase
from django.test import override_settings
from moto import mock_aws
from PIL import Image

from .utils import make_image

BUCKET = "test-thumbnails-bucket"


@mock_aws
@override_settings(THUMBNAIL_SIZES={"small": (10, 10), "med": (20, 20)})
class AsyncThumbnailS3StorageTests(SimpleTestCase):
    def setUp(self):
        conn = boto3.resource("s3", region_name="us-east-1")
        conn.create_bucket(Bucket=BUCKET)
        # Drop cached storage instances so this test's instance is bound to the
        # current moto mock (and matches what run_thumbnail_job resolves).
        storages._storages = {}
        # Same instance the worker would resolve via the STORAGES alias.
        self.storage = storages["thumbnails"]

    def test_original_saved_and_thumbnails_generated(self):
        name = self.storage.save(
            "photos/cat.jpg", ContentFile(make_image().read())
        )
        self.assertEqual(name, "photos/cat.jpg")
        self.assertTrue(self.storage.exists("photos/cat.jpg"))

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

    def test_thumbnail_url_is_deterministic(self):
        self.storage.save("photos/cat.jpg", ContentFile(make_image().read()))
        url = self.storage.thumbnail_url("photos/cat.jpg", "small")
        self.assertIn("thumbnails/small/photos/cat.jpg", url)

    def test_worker_only_needs_name_not_bytes(self):
        # Simulate the worker: the original already exists, call the job with
        # just the alias + name (no image bytes passed).
        from thumbnail_storage.tasks import run_thumbnail_job

        self.storage.save("a/dog.jpg", ContentFile(make_image().read()))
        thumb = self.storage.get_thumbnail_name("a/dog.jpg", "small")
        # Remove a thumbnail, then regenerate purely from name.
        self.storage.delete(thumb)
        self.assertFalse(self.storage.exists(thumb))

        run_thumbnail_job("thumbnails", "a/dog.jpg")
        self.assertTrue(self.storage.exists(thumb))
