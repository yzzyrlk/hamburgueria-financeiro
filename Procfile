web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
release: python -c "from app.core.bootstrap import apply_schema; apply_schema()"
