import logging

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage

from . import utils
from .core import generate_thumbnails
from .utils import DEFAULT_THUMBNAIL_PREFIX
from .utils import IMAGE_EXTENSIONS  # noqa: F401  (re-exported for convenience)
from .utils import THUMBNAIL_SETTING

logger = logging.getLogger(__name__)


class ThumbnailMixin:
    """Storage mixin that writes thumbnails synchronously when an image is saved.

    Mix it into any Django storage backend. Sizes come from the
    ``THUMBNAIL_SIZES`` setting, e.g.::

        THUMBNAIL_SIZES = {"small": (10, 10), "med": (20, 20)}

    Saving ``photos/cat.jpg`` then also produces ``photos/cat_small.jpg`` and
    ``photos/cat_med.jpg`` in the same backend. Retrieve their URLs with
    :meth:`thumbnail_url` or :meth:`get_thumbnails`.

    The naming and write steps are split into small overridable methods
    (:meth:`get_thumbnail_name`, :meth:`store_thumbnail`) so a project can layer
    a status model or lazy generation on top without forking the package.
    """

    thumbnail_setting = THUMBNAIL_SETTING

    #: Dedicated namespace for generated thumbnails. Set to "" to fall back to
    #: the in-place ``name_key.ext`` scheme (not recommended — see
    #: utils.get_thumbnail_name).
    thumbnail_prefix = DEFAULT_THUMBNAIL_PREFIX

    @property
    def thumbnail_sizes(self):
        return getattr(settings, self.thumbnail_setting, {}) or {}

    @property
    def thumbnail_max_pixels(self):
        # Off by default. Set THUMBNAIL_MAX_PIXELS to cap decoded image size
        # (width * height) and skip anything larger (decompression-bomb guard).
        return getattr(settings, "THUMBNAIL_MAX_PIXELS", None)

    # -- naming / detection (overridable) --------------------------------
    def get_thumbnail_name(self, name, key):
        return utils.get_thumbnail_name(name, key, self.thumbnail_prefix)

    def is_image(self, name):
        return utils.is_image(name)

    # -- write hook (overridable) ----------------------------------------
    def store_thumbnail(self, thumb_name, data):
        """Persist one thumbnail's bytes under the exact ``thumb_name``.

        Calls the *backend's* ``_save`` directly (via ``super()``) so it never
        recurses back into thumbnail generation. On backends that overwrite by
        key (e.g. S3 with ``file_overwrite=True``) this is a single atomic
        write. On backends that don't overwrite, any stale thumbnail is removed
        first so the name stays deterministic.
        """
        content = ContentFile(data)
        if getattr(self, "file_overwrite", False):
            super()._save(thumb_name, content)
            return
        if self.exists(thumb_name):
            self.delete(thumb_name)
        super()._save(thumb_name, content)

    # -- save hook --------------------------------------------------------
    def _save(self, name, content):
        # Save the original first; the backend may rename it on collision, so
        # use the returned name as the basis for the thumbnails.
        name = super()._save(name, content)
        if self.thumbnail_sizes and self.is_image(name):
            generate_thumbnails(
                self,
                name,
                self.thumbnail_sizes,
                source=content,
                max_pixels=self.thumbnail_max_pixels,
            )
        return name

    # -- delete hook ------------------------------------------------------
    def delete(self, name):
        """Delete ``name`` and clean up its thumbnails so they don't orphan."""
        super().delete(name)
        if not self.is_image(name):
            return
        for key in self.thumbnail_sizes:
            thumb_name = self.get_thumbnail_name(name, key)
            try:
                # super().delete avoids recursing into this method again.
                super().delete(thumb_name)
            except Exception:
                logger.warning(
                    "Failed to delete thumbnail %r for %r.",
                    thumb_name,
                    name,
                    exc_info=True,
                )

    # -- urls -------------------------------------------------------------
    def thumbnail_url(self, name, key):
        """URL of a single thumbnail, e.g. ``thumbnail_url(name, "small")``."""
        return self.url(self.get_thumbnail_name(name, key))

    def get_thumbnails(self, name):
        """Mapping of ``{size_key: url}`` for every configured size."""
        return {key: self.thumbnail_url(name, key) for key in self.thumbnail_sizes}


class AsyncThumbnailMixin(ThumbnailMixin):
    """Like :class:`ThumbnailMixin`, but offloads generation to a Celery task.

    The original file is saved synchronously; thumbnails are produced later by
    a worker that re-reads the original from this same storage. The worker
    finds the storage via Django's ``STORAGES`` registry, so the storage must
    be configured there under a key, and that key passed as ``alias``::

        STORAGES = {
            "thumbnails": {
                "BACKEND": "thumbnail_storage.AsyncThumbnailS3Storage",
                "OPTIONS": {"alias": "thumbnails", "bucket_name": "my-bucket"},
            },
        }

    If Celery is not installed, generation falls back to running inline.
    """

    #: STORAGES key used to rebuild this storage inside the worker.
    storage_alias = None

    def __init__(self, *args, alias=None, **kwargs):
        if alias is not None:
            self.storage_alias = alias
        super().__init__(*args, **kwargs)

    def _save(self, name, content):
        # Save the original WITHOUT generating thumbnails inline: skip
        # ThumbnailMixin._save and go straight to the backend's _save.
        name = super(ThumbnailMixin, self)._save(name, content)
        if self.thumbnail_sizes and self.is_image(name):
            from .tasks import enqueue_thumbnails

            enqueue_thumbnails(self.storage_alias, name)
        return name


class ThumbnailFileSystemStorage(ThumbnailMixin, FileSystemStorage):
    """Local-filesystem storage that generates thumbnails on save."""


try:
    from storages.backends.s3 import S3Storage
except ImportError:  # pragma: no cover - django-storages[s3] not installed
    pass
else:

    class ThumbnailS3Storage(ThumbnailMixin, S3Storage):
        """S3 storage (via django-storages) that generates thumbnails on save."""

    class AsyncThumbnailS3Storage(AsyncThumbnailMixin, S3Storage):
        """S3 storage that generates thumbnails asynchronously via Celery."""
