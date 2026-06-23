import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "example-insecure-key-do-not-use-in-prod"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.staticfiles",
    "gallery",
]

MIDDLEWARE = []
ROOT_URLCONF = "exampleproj.urls"
TEMPLATES = []
WSGI_APPLICATION = None

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
USE_TZ = True
STATIC_URL = "static/"

# --- Thumbnails -----------------------------------------------------------
THUMBNAIL_SIZES = {"small": (64, 64), "med": (256, 256)}

# Read from your environment:
#   AWS_STORAGE_BUCKET_NAME, AWS_S3_REGION_NAME,
#   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY  (the last two used by boto3)
AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME", "")
AWS_S3_REGION_NAME = os.environ.get("AWS_S3_REGION_NAME", "us-east-1")

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
    # Synchronous thumbnail-generating S3 backend: thumbnails are created during
    # save(). No Celery/broker required. (Swap to AsyncThumbnailS3Storage with an
    # "alias" option later if you want to offload generation to a worker.)
    "thumbnails": {
        "BACKEND": "thumbnail_storage.ThumbnailS3Storage",
        "OPTIONS": {
            "bucket_name": AWS_STORAGE_BUCKET_NAME,
            "region_name": AWS_S3_REGION_NAME,
        },
    },
}
