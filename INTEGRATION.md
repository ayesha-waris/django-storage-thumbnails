# Using `django-storage-thumbnails` in your app

Automatic image thumbnails for Django storage backends (local filesystem or
Amazon S3). Thumbnails are generated **synchronously when a file is saved** and
stored under a dedicated `thumbnails/<size>/` prefix.

---

## 1. Install

Pick whichever delivery method you were given:

**From a Git repo:**
```bash
pip install "django-storage-thumbnails[s3] @ git+https://github.com/<owner>/django-storage-thumbnails.git"
```

**From a wheel file** (e.g. `django_storage_thumbnails-0.1.0-py3-none-any.whl`):
```bash
pip install "/path/to/django_storage_thumbnails-0.1.0-py3-none-any.whl[s3]"
```

**From a source folder:**
```bash
pip install -e "/path/to/django-storage-thumbnails[s3]"
```

> Drop the `[s3]` extra if you only need local-filesystem storage.

---

## 2. Configure sizes (settings.py)

```python
THUMBNAIL_SIZES = {
    "small": (64, 64),
    "med": (256, 256),
}
```
Each size is a `(width, height)` box (or a `"WxH"` string). Aspect ratio is
preserved, so `(64, 64)` means "fit within 64×64", not an exact crop.

Optional safety cap (off by default) — skip decoding images bigger than this:
```python
THUMBNAIL_MAX_PIXELS = 40_000_000  # 40 megapixels
```

---

## 3. Point your storage at it

### S3
```python
# settings.py
STORAGES = {
    "default": {
        "BACKEND": "thumbnail_storage.ThumbnailS3Storage",
        "OPTIONS": {
            "bucket_name": "your-bucket",
            "region_name": "us-east-1",
        },
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
```
S3 credentials come from the standard AWS sources (env vars
`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`, an instance role, etc.).

### Local filesystem
```python
STORAGES = {
    "default": {"BACKEND": "thumbnail_storage.ThumbnailFileSystemStorage"},
}
```

### Or per-field (without changing the default storage)
```python
from django.db import models
from thumbnail_storage import ThumbnailS3Storage

class Photo(models.Model):
    image = models.ImageField(
        upload_to="photos/",
        storage=ThumbnailS3Storage(bucket_name="your-bucket"),
    )
```

---

## 4. Use it

Saving an image automatically creates its thumbnails:
```python
photo.image.save("cat.jpg", my_file)
# also creates: thumbnails/small/photos/cat.jpg, thumbnails/med/photos/cat.jpg
```

Get the links:
```python
storage = photo.image.storage
storage.thumbnail_url(photo.image.name, "small")
# -> ".../thumbnails/small/photos/cat.jpg"

storage.get_thumbnails(photo.image.name)
# -> {"small": ".../thumbnails/small/...", "med": ".../thumbnails/med/..."}
```

In a template, with a fallback to the original while you like:
```html
<img src="{{ small_url }}" onerror="this.onerror=null; this.src='{{ original_url }}'">
```

Deleting the file removes its thumbnails too:
```python
storage.delete(photo.image.name)   # also deletes the thumbnails
```

---

## Good to know

- **Synchronous**: thumbnails are made during `save()`, so a very large upload
  makes that one request slower. Fine for typical app uploads.
- **Supported inputs**: jpg/jpeg, png, gif, bmp, tiff, webp. Non-images and
  unreadable files are stored untouched (no thumbnails).
- **Failures never break the upload**: a bad image or one bad size is logged
  and skipped; the original always saves.
- **Naming is deterministic** and lives in its own `thumbnails/` namespace, so a
  thumbnail can never overwrite a user's file.
- **Customize**: subclass and set `thumbnail_prefix`, or override
  `get_thumbnail_name` / `store_thumbnail`.
- **Want generation off the request thread?** There's an optional Celery path
  (`AsyncThumbnailS3Storage`) — not required for the setup above.
