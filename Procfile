release: ./manage.py migrate
web: gunicorn --bind 0.0.0.0:$PORT shapeworks_cloud.wsgi
worker: REMAP_SIGTERM=SIGQUIT celery --app shapeworks_cloud.celery worker --loglevel INFO --without-heartbeat
