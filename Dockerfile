FROM python:slim
RUN apt update && apt install -y cmake
RUN python3 -m pip install --no-cache --upgrade pip setuptools
RUN python -m pip install numpy
COPY ./ /heartbeat/
RUN python3 -m pip install --no-cache -r /heartbeat/requirements.txt
CMD ["cd", "/heartbeat", "&&", "gunicorn", "heartbeat:app"