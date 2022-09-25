FROM alpine:latest
RUN apk add --update --no-cache python3 && ln -sf python3 /usr/bin/python
RUN python3 -m ensurepip
RUN python3 -m pip install --no-cache --upgrade pip setuptools
COPY ./ /heartbeat/
RUN python3 -m pip install -r /heartbeat/requirements.txt
CMD ["cd", "/heartbeat", "&&", "gunicorn", "heartbeat:app"