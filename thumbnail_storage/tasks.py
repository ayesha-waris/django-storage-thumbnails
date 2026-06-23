"""Celery integration for asynchronous thumbnail generation.

Celery is optional. If it is not installed, :func:`enqueue_thumbnails` runs the
job inline instead of dispatching it, so async storages still work (just
synchronously) without a broker.
"""

from .core import generate_thumbnails

try:  # Celery is an optional dependency.
    from celery import shared_task
except ImportError:  # pragma: no cover - celery not installed
    shared_task = None


def _resolve_storage(alias):
    """Rebuild the storage instance the worker should write thumbnails to."""
    from django.core.files.storage import storages

    return storages[alias]


def run_thumbnail_job(alias, name):
    """Re-read ``name`` from the aliased storage and write its thumbnails.

    Takes only the alias and the file name — never the image bytes — so it is
    cheap to put on the broker and safe to retry.
    """
    from django.conf import settings

    storage = _resolve_storage(alias)
    sizes = getattr(settings, storage.thumbnail_setting, {})
    max_pixels = getattr(storage, "thumbnail_max_pixels", None)
    # source=None -> the worker re-reads the original from storage.
    generate_thumbnails(storage, name, sizes, max_pixels=max_pixels)


if shared_task is not None:
    generate_thumbnails_task = shared_task(run_thumbnail_job)
else:  # pragma: no cover - exercised only without celery installed
    generate_thumbnails_task = None


def enqueue_thumbnails(alias, name):
    """Dispatch (or, without Celery, run) the thumbnail job for ``name``."""
    if alias is None:
        from django.core.exceptions import ImproperlyConfigured

        raise ImproperlyConfigured(
            "Async thumbnail storage needs an 'alias' that matches its key in "
            "the STORAGES setting so the Celery worker can find it."
        )
    if generate_thumbnails_task is not None:
        generate_thumbnails_task.delay(alias, name)
    else:
        run_thumbnail_job(alias, name)
