#!/bin/sh
cd /heartbeat && celery -A heartbeat.distribute_work worker --loglevel=INFO