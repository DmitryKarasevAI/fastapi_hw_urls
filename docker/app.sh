#!/bin/bash

/fastapi_app/docker/wait-for-it.sh db:5432 --timeout=5 --strict

export PYTHONPATH=/fastapi_app

cd /fastapi_app/src

alembic upgrade head


exec gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind=0.0.0.0:8000
