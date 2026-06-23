from django.core.files.storage import storages
from django.db import models


def thumbnail_storage():
    """Resolve the async S3 storage from the STORAGES registry.

    Passed as a callable so settings are read lazily (and migrations stay
    stable across environments).
    """
    return storages["thumbnails"]


class Photo(models.Model):
    image = models.ImageField(upload_to="photos/", storage=thumbnail_storage)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.image.name

    @property
    def thumbnails(self):
        """``{size_key: url}`` for this photo's thumbnails."""
        return self.image.storage.get_thumbnails(self.image.name)
