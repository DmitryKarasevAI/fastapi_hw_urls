#!/bin/bash

./docker/wait-for-it.sh app:9999 --timeout=5 --strict

locust -f ./locustfile.py --headless -u 100 -r 10 -t 1m --host http://app:8000
