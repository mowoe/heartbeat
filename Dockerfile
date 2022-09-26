FROM python:slim
RUN apt update && apt install -y cmake build-essential
RUN python -m pip install --no-cache --upgrade pip setuptools
COPY ./ /heartbeat/
RUN python3 -m pip install --no-cache -r /heartbeat/requirements.txt
CMD ["gunicorn", "--access-logfile", "-","heartbeat:app", "-b", ":80", "--chdir","/heartbeat/"]