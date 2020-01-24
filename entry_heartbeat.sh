sleep 20
cd /app/ && celery worker -D -A main.celery -l info
/start.sh