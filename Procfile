release: python manage.py migrate --noinput
web: gunicorn settings.wsgi:application --bind 0.0.0.0:$PORT
