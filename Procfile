web: python manage.py collectstatic --noinput && python manage.py migrate --noinput && gunicorn settings.wsgi:application --bind 0.0.0.0:$PORT
