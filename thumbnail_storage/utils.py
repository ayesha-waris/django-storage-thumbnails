"""Small helpers shared across the package (no Django/Pillow import needed)."""

import os

#: Name of the Django setting holding the thumbnail size config.
THUMBNAIL_SETTING = "THUMBNAIL_SIZES"

#: File extensions we attempt to thumbnail. Anything else is saved untouched.
IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "gif",
    "bmp",
    "tiff",
    "tif",
    "webp",
}


def parse_size(value):
    """Normalise a thumbnail size into a ``(width, height)`` tuple of ints.

    Accepts either a ``(w, h)`` tuple/list or a ``"WxH"`` string (case and
    space insensitive), so all of these are equivalent::

        (10, 10)   ["10", "10"]   "10x10"   "10 X 10"
    """
    if isinstance(value, str):
        width, height = value.lower().replace(" ", "").split("x")
        return int(width), int(height)
    width, height = value
    return int(width), int(height)


#: Default storage prefix under which all generated thumbnails live. Keeping
#: derivatives in their own namespace avoids ever colliding with — or
#: overwriting — a source file the user uploaded.
DEFAULT_THUMBNAIL_PREFIX = "thumbnails"


def get_thumbnail_name(name, key, prefix=DEFAULT_THUMBNAIL_PREFIX):
    """Return the deterministic storage name of the ``key`` thumbnail.

    With the default prefix, ``photos/cat.jpg`` + ``small`` becomes
    ``thumbnails/small/photos/cat.jpg`` — a dedicated namespace that can never
    clash with a user file. With an empty ``prefix`` it falls back to the
    in-place ``photos/cat_small.jpg`` scheme.
    """
    if prefix:
        return f"{prefix.rstrip('/')}/{key}/{name.lstrip('/')}"
    root, ext = os.path.splitext(name)
    return f"{root}_{key}{ext}"


def is_image(name):
    ext = os.path.splitext(name)[1].lower().lstrip(".")
    return ext in IMAGE_EXTENSIONS
