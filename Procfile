release: python manage.py migrate --noinput
web: gunicorn config.wsgi:application --config gunicorn.conf.py
