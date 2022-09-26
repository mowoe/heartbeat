#!/bin/sh
cd /heartbeat && celery -A distribute_work worker --loglevel=INFO