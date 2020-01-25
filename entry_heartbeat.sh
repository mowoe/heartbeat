sleep 20
cd /app/ && celery worker -D -A main.celery -f heratcel.log -l info
/start.sh