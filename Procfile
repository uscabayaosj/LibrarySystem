release: python -c "from app import init_db; init_db()"
web: gunicorn app:app --bind 0.0.0.0:$PORT --timeout 60
