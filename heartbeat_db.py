import peewee
import requests
from peewee import MySQLDatabase, SqliteDatabase
from peewee import CharField, ForeignKeyField, DateTimeField, fn, BooleanField
import peewee
import boto3
from flask import send_file
import json
import datetime
import os
import time
import random
from swiftclient.service import SwiftService, SwiftError
import swiftclient
from swiftclient.exceptions import ClientException

db_type = ""
s3_client = ""
bucket = "heartbeat-images"
openstack_config = ""
options = {"region_name":"DE1"}

def init_db(db_type):
    global Image
    global Results
    global s3_client
    global openstack_config
    db_type = db_type
    dbconfig = json.load(open("db_auth.json","rb"))
    mysql_db = peewee.MySQLDatabase(**dbconfig)

    class Image(peewee.Model):
        filename = CharField()
        uploaded_date = DateTimeField(default=datetime.datetime.now)
        origin = CharField(default="unknown")
        other_data = CharField(default="null",max_length=7000)
        face_rec_worked =  BooleanField(default=False)
        class Meta:
            database = mysql_db

    class Results(peewee.Model):
        image_id = CharField()
        result_type = CharField()
        result = CharField(max_length=7000)
        class Meta:
            database = mysql_db  
    mysql_db.connect()
    mysql_db.create_tables([Image,Results])
    mysql_db.close()
    if db_type == "s3":
        aws_config = json.load(open("./s3_auth.json","rb"))
        s3_client = boto3.client('s3',**aws_config)
        print("established s3 connection!")
    elif db_type == "openstack":
        openstack_config = json.load(open("./openstack_auth.json","rb"))
        #swift_client = swiftclient.client.Connection(**openstack_config,os_options=options)
        #print("Swift connection established successfully!")
    return mysql_db


def upload_file(filename,origin="unknown",other_data={"unknown":1}):
    global openstack_config
    image = Image(filename=filename,origin=origin,other_data=other_data)
    image.save()
    print(db_type)
    if db_type=="file":
        pass
    elif db_type=="s3":
        filename_path = os.path.join("./uploaded_pics",filename)
        response = s3_client.upload_file(filename_path, bucket, filename)
        print("uploaded to s3!")
        os.remove(filename_path)
    elif db_type == "openstack":
        swift_client = swiftclient.client.Connection(**openstack_config,os_options=options)
        print("Swift connection established!")
        with open(os.path.join("./uploaded_pics",filename), 'rb') as local:
            swift_client.put_object(
                bucket,
                filename,
                contents=local,
                content_type='image/'+filename.split(".")[-1]
            )
        try:
            resp_headers = swift_client.head_object(bucket, filename)
            print('The object was successfully created')
        except SyntaxError as e:
            print(e,str(e))
        finally:
            swift_client.close()
            print("Swift client closed!")
            os.remove(os.path.join("./uploaded_pics",filename))


def get_file(image_id):
    try:
        filename = Image.select().where(Image.id==image_id).get().filename
        if db_type=="s3":
            with open(os.path.join("./",filename), 'wb') as f:
                s3_client.download_fileobj(bucket, filename, f)
            resp = send_file(os.path.join("./", filename), mimetype='image/png')
            os.remove(os.path.join("./", filename))
            return resp
        if db_type=="file":
            resp = send_file(os.path.join("./uploaded_pics", filename), mimetype='image/png')
            return resp
        if db_type=="openstack":
            swift_client = swiftclient.client.Connection(**openstack_config,os_options=options)
            resp_headers, obj_contents = swift_client.get_object(bucket, filename)
            with open(os.path.join("./",filename), 'wb') as local:
                local.write(obj_contents)
            resp = send_file(os.path.join("./",filename),mimetype="image/png")
            os.remove(os.path.join("./",filename))
            swift_client.close()
            return resp
    except Exception as b:
        print(b)
        return None


def get_all_work(work_type):
    query = Results.select().where(Results.result_type==work_type)
    results = []
    for x in query:
        results.append([x.image_id,x.id,x.result])
    return results

def request_work(work_type):
    query = Image.select().where(Image.face_rec_worked==False).limit(60)
    results = []
    for x in query:
        results.append(x.id)
    random.shuffle(results)
    return results

def submit_work(work_type,image_id,result):
    result = Results(image_id=image_id,result=result,result_type=work_type)
    result.save()
    query = Image.update(face_rec_worked=True).where(Image.id==image_id)
    query.execute()

def get_imgobj_from_id(image_id):
    return Image.select().where(Image.id==image_id).get()

def retrieve_model(save_path):
    if db_type=="s3":
        with open(os.path.join("./",save_path),"wb") as f:
            print(save_path.split("/")[-1])
            s3_client.download_fileobj(bucket,save_path.split("/")[-1],f)
        with open(os.path.join("./","trained_knn_list.clf"),"wb") as f:
            s3_client.download_fileobj(bucket,"trained_knn_list.clf",f)
