import shutil
import tempfile

from django.core.files.base import ContentFile
from django.test import SimpleTestCase
from django.test import override_settings
from PIL import Image

from thumbnail_storage import ThumbnailFileSystemStorage
from thumbnail_storage import parse_size

from .utils import make_image


class ParseSizeTests(SimpleTestCase):
    def test_tuple(self):
        self.assertEqual(parse_size((10, 20)), (10, 20))

    def test_list_of_strings(self):
        self.assertEqual(parse_size(["10", "20"]), (10, 20))

    def test_string(self):
        self.assertEqual(parse_size("10x20"), (10, 20))

    def test_string_with_spaces_and_caps(self):
        self.assertEqual(parse_size("10 X 20"), (10, 20))


@override_settings(THUMBNAIL_SIZES={"small": (10, 10), "med": (20, 20)})
class ThumbnailFileSystemStorageTests(SimpleTestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.storage = ThumbnailFileSystemStorage(
            location=self.tmp, base_url="/media/"
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_thumbnails_created_on_save(self):
        name = self.storage.save(
            "photos/cat.jpg", ContentFile(make_image().read())
        )
        self.assertEqual(name, "photos/cat.jpg")

        expected = {"small": (10, 10), "med": (20, 20)}
        for key, (max_w, max_h) in expected.items():
            # Thumbnails live under their own prefix, never beside the source.
            thumb_name = f"thumbnails/{key}/photos/cat.jpg"
            self.assertTrue(
                self.storage.exists(thumb_name), f"{thumb_name} missing"
            )
            with self.storage.open(thumb_name) as fh:
                img = Image.open(fh)
                img.load()
            # Thumbnails preserve aspect ratio and fit within the box.
            self.assertLessEqual(img.width, max_w)
            self.assertLessEqual(img.height, max_h)

    def test_thumbnail_url(self):
        self.storage.save("photos/cat.jpg", ContentFile(make_image().read()))
        self.assertEqual(
            self.storage.thumbnail_url("photos/cat.jpg", "small"),
            "/media/thumbnails/small/photos/cat.jpg",
        )

    def test_get_thumbnails_returns_all_urls(self):
        self.storage.save(
            "a/b.png", ContentFile(make_image(fmt="PNG").read())
        )
        urls = self.storage.get_thumbnails("a/b.png")
        self.assertEqual(set(urls), {"small", "med"})
        self.assertEqual(urls["small"], "/media/thumbnails/small/a/b.png")

    def test_png_with_alpha(self):
        self.storage.save(
            "a/logo.png", ContentFile(make_image(fmt="PNG").read())
        )
        self.assertTrue(self.storage.exists("thumbnails/small/a/logo.png"))

    def test_non_image_is_not_thumbnailed(self):
        self.storage.save("docs/readme.txt", ContentFile(b"hello world"))
        self.assertFalse(
            self.storage.exists("thumbnails/small/docs/readme.txt")
        )

    def test_no_sizes_configured_is_noop(self):
        with override_settings(THUMBNAIL_SIZES={}):
            self.storage.save("x/y.jpg", ContentFile(make_image().read()))
            self.assertFalse(
                self.storage.exists("thumbnails/small/x/y.jpg")
            )

    def test_corrupt_image_does_not_fail_upload(self):
        # An image extension but non-image bytes: the original must still save,
        # and no thumbnails are produced (failure is logged, not raised).
        name = self.storage.save(
            "broken/x.jpg", ContentFile(b"not really a jpeg")
        )
        self.assertEqual(name, "broken/x.jpg")
        self.assertTrue(self.storage.exists("broken/x.jpg"))
        self.assertFalse(self.storage.exists("thumbnails/small/broken/x.jpg"))

    def test_one_bad_size_does_not_block_others(self):
        with override_settings(
            THUMBNAIL_SIZES={"bad": "not-a-size", "small": (10, 10)}
        ):
            self.storage.save("mix/p.jpg", ContentFile(make_image().read()))
            # The malformed size is skipped; the valid one still gets written.
            self.assertFalse(self.storage.exists("thumbnails/bad/mix/p.jpg"))
            self.assertTrue(self.storage.exists("thumbnails/small/mix/p.jpg"))

    def test_thumbnail_does_not_collide_with_user_file(self):
        # A user file literally named like the old in-place scheme must NOT be
        # clobbered by, or confused with, a generated thumbnail.
        self.storage.save("cat.jpg", ContentFile(make_image().read()))
        user_file = self.storage.save(
            "cat_small.jpg", ContentFile(b"user owns this, not a thumbnail")
        )
        self.assertEqual(user_file, "cat_small.jpg")

        # The real thumbnail lives elsewhere...
        self.assertTrue(self.storage.exists("thumbnails/small/cat.jpg"))
        # ...and the user's file is untouched.
        with self.storage.open("cat_small.jpg") as fh:
            self.assertEqual(fh.read(), b"user owns this, not a thumbnail")

    def test_max_pixels_skips_oversized_image(self):
        # Off by default; when set, an image above the cap is skipped entirely.
        with override_settings(THUMBNAIL_MAX_PIXELS=100):  # 10x10 = 100 ok, more not
            self.storage.save(
                "big/wall.jpg", ContentFile(make_image(width=200, height=200).read())
            )
            self.assertTrue(self.storage.exists("big/wall.jpg"))
            self.assertFalse(
                self.storage.exists("thumbnails/small/big/wall.jpg")
            )

    def test_exif_orientation_is_applied(self):
        # A 40x20 image tagged orientation=6 (rotate 90°) should come out of the
        # thumbnailer as portrait (taller than wide), not landscape.
        from io import BytesIO

        from PIL import Image

        buf = BytesIO()
        img = Image.new("RGB", (40, 20), (0, 128, 255))
        exif = img.getexif()
        exif[274] = 6  # Orientation tag
        img.save(buf, format="JPEG", exif=exif)
        buf.seek(0)

        with override_settings(THUMBNAIL_SIZES={"small": (100, 100)}):
            self.storage.save("rot/x.jpg", ContentFile(buf.read()))
            with self.storage.open("thumbnails/small/rot/x.jpg") as fh:
                out = Image.open(fh)
                out.load()
            self.assertGreater(out.height, out.width)

    def test_delete_cleans_up_thumbnails(self):
        self.storage.save("photos/cat.jpg", ContentFile(make_image().read()))
        self.assertTrue(self.storage.exists("thumbnails/small/photos/cat.jpg"))
        self.assertTrue(self.storage.exists("thumbnails/med/photos/cat.jpg"))

        self.storage.delete("photos/cat.jpg")

        self.assertFalse(self.storage.exists("photos/cat.jpg"))
        self.assertFalse(self.storage.exists("thumbnails/small/photos/cat.jpg"))
        self.assertFalse(self.storage.exists("thumbnails/med/photos/cat.jpg"))
