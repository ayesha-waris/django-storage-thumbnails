SECRET_KEY = "test-secret-key"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# The feature under test: thumbnail sizes config.
THUMBNAIL_SIZES = {"small": (10, 10), "med": (20, 20)}

# Named storages so the async path can rebuild the backend inside a worker.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
    "thumbnails": {
        "BACKEND": "thumbnail_storage.AsyncThumbnailS3Storage",
        "OPTIONS": {
            "alias": "thumbnails",
            "bucket_name": "test-thumbnails-bucket",
            "region_name": "us-east-1",
        },
    },
}
