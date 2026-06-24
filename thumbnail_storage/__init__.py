from .mixins import AsyncThumbnailMixin
from .mixins import ThumbnailFileSystemStorage
from .mixins import ThumbnailMixin
from .utils import IMAGE_EXTENSIONS
from .utils import THUMBNAIL_SETTING
from .utils import parse_size

__all__ = [
    "ThumbnailMixin",
    "AsyncThumbnailMixin",
    "ThumbnailFileSystemStorage",
    "parse_size",
    "THUMBNAIL_SETTING",
    "IMAGE_EXTENSIONS",
]

try:  # Optional: only available when django-storages[s3] is installed.
    from .mixins import AsyncThumbnailS3Storage
    from .mixins import ThumbnailS3Storage
except ImportError:  # pragma: no cover
    pass
else:
    __all__ += ["ThumbnailS3Storage", "AsyncThumbnailS3Storage"]

__version__ = "0.1.0"
