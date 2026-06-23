# Example project

A minimal Django project that stores uploads on S3 and generates thumbnails
**synchronously on save** using `django-storage-thumbnails`. No Celery, broker,
or worker required.

## 1. Install

```bash
pip install -e "..[s3]"   # the package, from the repo root
```

## 2. Environment

```bash
export AWS_STORAGE_BUCKET_NAME=your-bucket
export AWS_S3_REGION_NAME=us-east-1
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
```

## 3. Migrate

```bash
cd example
python manage.py migrate
```

## 4. Run

```bash
python manage.py demo_thumbnails
# or with your own image:
python manage.py demo_thumbnails --image /path/to/photo.jpg --name cat.jpg
```

You'll see the original URL followed by `[ready] small` / `[ready] med`. Check
your bucket — alongside `demo.jpg` you'll find:

```
thumbnails/small/demo.jpg
thumbnails/med/demo.jpg
```

Deleting the `Photo` (or calling `storage.delete(name)`) removes those
thumbnails too.

## How it's wired

- `exampleproj/settings.py` — `THUMBNAIL_SIZES` and the
  `STORAGES["thumbnails"]` entry pointing at `ThumbnailS3Storage`.
- `gallery/models.py` — a `Photo` model whose `ImageField` uses the thumbnail
  storage; `photo.thumbnails` returns `{size: url}`.

> Want generation off the request thread later? Swap the backend to
> `AsyncThumbnailS3Storage` (add an `"alias"` option matching the STORAGES key)
> and run a Celery worker. Not needed for this setup.
