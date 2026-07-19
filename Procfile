web: python manage.py migrate --noinput && python manage.py seed_demo_analyses && python manage.py ensure_admin && gunicorn config.wsgi --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 180
