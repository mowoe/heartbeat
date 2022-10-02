#!/bin/sh
cd /home/celery/heartbeat && celery -A distribute_work worker --loglevel=INFO --uid 1000