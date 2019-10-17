FROM mowoe/ngface:latest
RUN apt update
RUN apt install -y cmake
COPY ./requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt
COPY ./static /app/static
COPY ./templates /app/templates
COPY ./examples /app/examples
COPY ./heartbeat_db.py /app/heartbeat_db.py
RUN mkdir /app/uploaded_pics
COPY ./heartbeat_new.py /app/main.py
