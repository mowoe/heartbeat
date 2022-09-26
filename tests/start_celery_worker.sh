#!/bin/sh
cd /heartbeat && celery -A distribute_work purge
cd /heartbeat && celery -A distribute_work worker --loglevel=INFO --uid 1000