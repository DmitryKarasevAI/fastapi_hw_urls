#!/bin/bash


/fastapi_app/docker/wait-for-it.sh db:5432


alembic upgrade head

cd src

gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind=0.0.0.0:8000