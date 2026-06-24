"""Backend-agnostic thumbnail generation, shared by the sync and async paths."""

import logging
from io import BytesIO

try:
    from PIL import Image
    from PIL import ImageOps
except ImportError:  # pragma: no cover - Pillow is a hard dependency
    Image = None
    ImageOps = None

from .utils import parse_size

logger = logging.getLogger(__name__)


def generate_thumbnails(storage, name, sizes, source=None, max_pixels=None):
    """Write a thumbnail of ``name`` for every entry in ``sizes``.

    ``storage`` must expose the helpers added by :class:`ThumbnailMixin`
    (``get_thumbnail_name`` and ``store_thumbnail``).

    ``source`` is the original file's content. When ``None`` (the async case)
    the original is re-opened from ``storage`` — that is why a Celery worker
    only needs the file *name*, not its bytes.

    ``max_pixels`` caps the decoded image size (width * height). Images larger
    than this are skipped *before* they are decoded, which bounds memory use and
    blocks decompression-bomb uploads.

    Failures are logged and swallowed: a single bad image or one unwritable
    size never aborts the caller (an upload) or the other sizes.
    """
    if Image is None or not sizes:
        return

    close_source = False
    if source is None:
        source = storage.open(name)
        close_source = True

    try:
        try:
            source.seek(0)
            image = Image.open(source)
            # image.size comes from the header, so we can reject an oversized
            # image before paying to decode it into memory.
            width, height = image.size
            if max_pixels and width * height > max_pixels:
                logger.warning(
                    "Skipping thumbnails for %r: %dx%d exceeds max_pixels=%d.",
                    name,
                    width,
                    height,
                    max_pixels,
                )
                return
            image.load()
            # Respect EXIF orientation so portrait photos aren't sideways.
            image = ImageOps.exif_transpose(image)
        except Exception:
            logger.warning(
                "Could not read %r as an image; skipping thumbnails.",
                name,
                exc_info=True,
            )
            return

        image_format = image.format or "PNG"
        for key, size in sizes.items():
            try:
                thumb = image.copy()
                thumb.thumbnail(parse_size(size))
                if image_format == "JPEG" and thumb.mode in ("RGBA", "P"):
                    thumb = thumb.convert("RGB")

                buffer = BytesIO()
                thumb.save(buffer, format=image_format)

                thumb_name = storage.get_thumbnail_name(name, key)
                storage.store_thumbnail(thumb_name, buffer.getvalue())
            except Exception:
                logger.warning(
                    "Failed to generate %r thumbnail for %r; skipping it.",
                    key,
                    name,
                    exc_info=True,
                )
    finally:
        if close_source:
            source.close()
