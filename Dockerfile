FROM tiangolo/uwsgi-nginx-flask
RUN apt update
RUN apt install -y cmake
RUN pip install face_recognition
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt
RUN mkdir /app/uploaded_pics
COPY ./static /app/static
COPY ./templates /app/templates
COPY ./examples /app/examples
COPY ./heartbeat_db.py /app/heartbeat_db.py
COPY ./read_config.py /app/read_config.py
COPY ./heartbeat.py /app/main.py
RUN echo "ignore-sigpipe=true" >> /etc/uwsgi/uwsgi.ini
RUN echo "ignore-write-errors=true" >> /etc/uwsgi/uwsgi.ini
RUN echo "disable-write-exception=true" >> /etc/uwsgi/uwsgi.ini
