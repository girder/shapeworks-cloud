release: git init && pip install -e ./swcc && python manage.py reset_db --noinput &&  python manage.py migrate
web: git init && pip install -e ./swcc && gunicorn --bind 0.0.0.0:$PORT shapeworks_cloud.wsgi
worker: git init && pip install -e ./swcc && REMAP_SIGTERM=SIGQUIT celery --app shapeworks_cloud.celery worker --loglevel INFO --without-heartbeat
