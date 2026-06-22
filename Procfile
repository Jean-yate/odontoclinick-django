web: python manage.py collectstatic --noinput && gunicorn settings.wsgi:application --bind 0.0.0.0:$PORT --timeout 60
