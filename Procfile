web: PYTHONPATH=src gunicorn -w 1 -b 0.0.0.0:${PORT:-8080} thronos_pawssworfmanager.http_service:wsgi_app
