FROM tiangolo/uwsgi-nginx-flask:python3.7
RUN apt update
RUN apt install -y cmake
RUN pip install mysql.connector
RUN pip install peewee
RUN pip install face_recognition
RUN pip install scikit-learn
COPY ./static /app/static
COPY ./templates /app/templates
COPY ./examples /app/examples
RUN mkdir /app/uploaded_pics
COPY db_auth.json /app/db_auth.json
COPY ./heartbeat_new.py /app/main.py
RUN pip install requests
RUN pip install PyMySQL
