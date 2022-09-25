FROM python:slim
RUN python3 -m ensurepip
RUN python3 -m pip install --no-cache --upgrade pip setuptools
RUN python -m pip install numpy
COPY ./ /heartbeat/
RUN python3 -m pip install -r /heartbeat/requirements.txt
CMD ["cd", "/heartbeat", "&&", "gunicorn", "heartbeat:app"