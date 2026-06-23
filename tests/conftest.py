import os

# Dummy AWS credentials so boto3 / moto never touch a real account.
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

# If Celery is installed, run tasks inline (eager) so the async path is
# deterministic without a broker. If it's not installed, enqueue_thumbnails
# already falls back to running inline.
try:
    from celery import Celery
except ImportError:  # pragma: no cover
    pass
else:
    _celery_app = Celery("tests")
    _celery_app.conf.task_always_eager = True
    _celery_app.conf.task_eager_propagates = True
    _celery_app.set_default()

    import thumbnail_storage.tasks  # noqa: E402,F401  (registers the task)

    _celery_app.finalize()
