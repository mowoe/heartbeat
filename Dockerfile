FROM python:slim
RUN apt update && apt install -y cmake build-essential
RUN python3 -m pip install --no-cache --upgrade pip setuptools
RUN python -m pip install numpy
COPY ./ /heartbeat/
RUN python3 -m pip install --no-cache -r /heartbeat/requirements.txt
CMD ["gunicorn", "heartbeat:app", "--chdir","/heartbeat/"]