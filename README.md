# django-storage-thumbnails

Automatically generate image thumbnails whenever a file is saved through a
Django storage backend. Works with **local filesystem** storage and **Amazon
S3** (via [django-storages](https://github.com/jschneier/django-storages)).

## Install

Not on PyPI yet — install from the git repo:

```bash
# local filesystem only
pip install "django-storage-thumbnails @ git+https://github.com/ayesha-waris/django-storage-thumbnails.git"

# with S3 support
pip install "django-storage-thumbnails[s3] @ git+https://github.com/ayesha-waris/django-storage-thumbnails.git"
```

For local development against a checkout, use an editable install:

```bash
pip install -e "/path/to/django-storage-thumbnails[s3]"
```

## Configure

Add the sizes you want to your Django settings. Sizes accept either a
`(width, height)` tuple or a `"WxH"` string:

```python
THUMBNAIL_SIZES = {
    "small": (10, 10),
    "med": (20, 20),
}
```

Then point your model/field (or `STORAGES`) at a thumbnail-aware storage.

### Local filesystem

```python
from thumbnail_storage import ThumbnailFileSystemStorage

storage = ThumbnailFileSystemStorage()
name = storage.save("photos/cat.jpg", my_image_file)
# also writes: thumbnails/small/photos/cat.jpg, thumbnails/med/photos/cat.jpg
```

### Amazon S3

```python
from thumbnail_storage import ThumbnailS3Storage

storage = ThumbnailS3Storage(bucket_name="my-bucket")
storage.save("photos/cat.jpg", my_image_file)
```

### In a model

```python
from django.db import models
from thumbnail_storage import ThumbnailFileSystemStorage

class Photo(models.Model):
    image = models.ImageField(
        upload_to="photos/",
        storage=ThumbnailFileSystemStorage(),
    )
```

## Getting thumbnail links

Thumbnails are stored under a dedicated `thumbnails/<size>/` prefix so they can
never collide with or overwrite a user's uploaded file. Deleting the original
also removes its thumbnails.

```python
storage.thumbnail_url("photos/cat.jpg", "small")
# -> "/media/thumbnails/small/photos/cat.jpg"

storage.get_thumbnails("photos/cat.jpg")
# -> {"small": "/media/thumbnails/small/photos/cat.jpg",
#     "med":   "/media/thumbnails/med/photos/cat.jpg"}
```

## Use it with any backend

`ThumbnailMixin` can be mixed into any Django `Storage` subclass:

```python
from thumbnail_storage import ThumbnailMixin
from storages.backends.azure_storage import AzureStorage

class ThumbnailAzureStorage(ThumbnailMixin, AzureStorage):
    pass
```

## Async generation with Celery (S3)

For S3, you usually don't want to block the upload request while thumbnails are
generated. Use the async storage: it saves the original immediately and hands
the thumbnail work to a Celery worker, which re-reads the original from S3 — so
only the **file name** travels over the broker, never the image bytes.

```bash
pip install "django-storage-thumbnails[s3,celery]"
```

Register the storage under a key in `STORAGES` and pass that key as `alias`
(the worker uses it to rebuild the same backend):

```python
# settings.py
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "thumbnails": {
        "BACKEND": "thumbnail_storage.AsyncThumbnailS3Storage",
        "OPTIONS": {"alias": "thumbnails", "bucket_name": "my-bucket"},
    },
}
```

```python
from django.core.files.storage import storages

storage = storages["thumbnails"]
storage.save("photos/cat.jpg", img)   # returns immediately; thumbnails follow
```

Make sure your Celery app autodiscovers `thumbnail_storage.tasks`, and that the
worker can reach the same S3 bucket. If Celery isn't installed, generation
quietly falls back to running inline.

### Fetching while a thumbnail is still being made

Names are deterministic, so `thumbnail_url()` returns the URL right away — even
before the worker finishes. Use it with a fallback to the original so there's no
broken image in the brief window before the thumbnail exists:

```html
<img src="{{ small_url }}" onerror="this.onerror=null; this.src='{{ original_url }}'">
```

Need a guaranteed "ready" signal or to generate sizes only on first view? The
`get_thumbnail_name` and `store_thumbnail` methods are overridable — subclass to
record a status row or to generate lazily, without forking the package.

## How it works

On `_save`, if the saved file's extension is a known image type and
`THUMBNAIL_SIZES` is non-empty, a thumbnail is generated for each size with
Pillow (`Image.thumbnail`, which preserves aspect ratio — so a `"10x10"` size is
a bounding box, not an exact crop) and saved under `thumbnails/<key>/<name>` in
the same backend. Non-images and unreadable files are passed through untouched,
and any per-size failure is logged and skipped without affecting the upload or
the other sizes. Override `thumbnail_prefix` to change the namespace, or
`get_thumbnail_name` / `store_thumbnail` to change naming or write behavior.

## Running the tests

```bash
pip install -e ".[test]"
pytest
```
