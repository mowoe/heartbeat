FROM python:slim
RUN apt update && apt install -y cmake build-essential libcurl4-openssl-dev libssl-dev gcc
RUN python -m pip install --no-cache --upgrade pip setuptools
COPY ./ /heartbeat/
RUN python3 -m pip install --no-cache -r /heartbeat/requirements.txt
RUN useradd -ms /bin/bash celery
COPY --chown=celery ./ /home/celery/heartbeat/
WORKDIR /heartbeat
CMD ["gunicorn", "--error-logfile", "-", "--access-logfile", "-","heartbeat:app", "-b", ":80"]