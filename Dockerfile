FROM tiangolo/uwsgi-nginx-flask:python3.7
RUN apt update
RUN apt install -y cmake
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt
COPY ./static /app/static
COPY ./templates /app/templates
COPY ./examples /app/examples
RUN mkdir /app/uploaded_pics
COPY ./heartbeat_new.py /app/main.py
