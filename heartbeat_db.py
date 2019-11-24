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

bucket = "heartbeat-images"
object_storage_auth = ""
options = {"region_name":"DE1"}

def setup_classes(mysql_db):
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

    return Image, Results

class HeartbeatDB(object):
    def __init__(self):
        pass

    def init_db(self,db_type, dbconfig, object_storage_type, object_storage_auth):
        mysql_db = peewee.MySQLDatabase(**dbconfig)
        self.Image, self.Results = setup_classes(mysql_db)
        self.db_type = db_type
        self.object_storage_type = object_storage_type
        self.object_storage_auth = object_storage_auth
        mysql_db.connect()
        mysql_db.create_tables([self.Image,self.Results])
        mysql_db.close()

        if object_storage_type == "s3":
            self.s3_client = boto3.client('s3',**object_storage_auth)
            print("established s3 connection!")
        elif object_storage_type == "openstack":
            pass
        return mysql_db

    def upload_file(self,filename,origin="unknown",other_data={"unknown":1}):
        image = self.Image(filename=filename,origin=origin,other_data=other_data)
        image.save()
        if self.object_storage_type=="file":
            pass
        elif self.object_storage_type =="s3":
            filename_path = os.path.join("./uploaded_pics",filename)
            response = self.s3_client.upload_file(filename_path, bucket, filename)
            print("uploaded to s3!")
            os.remove(filename_path)
        elif self.object_storage_type == "openstack":
            swift_client = swiftclient.client.Connection(os_options=options,**self.object_storage_auth)
            print("Swift connection established!")
            with open(os.path.join("./uploaded_pics",filename), 'rb') as local:
                swift_client.put_object(
                    bucket,
                    filename,
                    contents=local,
                    content_type='image/'+filename.split(".")[-1]
                )
            try:
                print(filename)
                assert type(swift_client.head_object(bucket, filename)) !=  type(None)
                print('The object was successfully created')
            except SyntaxError as e:
                print(e,str(e))
            finally:
                swift_client.close()
                print("Swift client closed!")
                os.remove(os.path.join("./uploaded_pics",filename))

    def get_file(self,image_id):
        try:
            filename = self.Image.select().where(self.Image.id==image_id).get().filename
            if self.object_storage_type=="s3":
                with open(os.path.join("./",filename), 'wb') as f:
                    self.s3_client.download_fileobj(bucket, filename, f)
                resp = send_file(os.path.join("./", filename), mimetype='image/png')
                os.remove(os.path.join("./", filename))
                return resp
            if self.object_storage_type=="file":
                resp = send_file(os.path.join("./uploaded_pics", filename), mimetype='image/png')
                return resp
            if self.object_storage_type=="openstack":
                swift_client = swiftclient.client.Connection(os_options=options,**self.object_storage_auth)
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


    def get_all_work(self,work_type):
        query = self.Results.select().where(self.Results.result_type==work_type)
        results = []
        for x in query:
            results.append([x.image_id,x.id,x.result])
        return results

    def request_work(self,work_type):
        query = self.Image.select().where(self.Image.face_rec_worked==False).limit(60)
        results = []
        for x in query:
            results.append(x.id)
        random.shuffle(results)
        return results

    def submit_work(self,work_type,image_id,result):
        result = self.Results(image_id=image_id,result=result,result_type=work_type)
        result.save()
        query = self.Image.update(face_rec_worked=True).where(self.Image.id==image_id)
        query.execute()

    def get_imgobj_from_id(self,image_id):
        return self.Image.select().where(self.Image.id==image_id).get()

    def retrieve_model(self,save_path):
        if self.object_storage_type=="s3":
            with open(os.path.join("./",save_path),"wb") as f:
                print(save_path.split("/")[-1])
                self.s3_client.download_fileobj(bucket,save_path.split("/")[-1],f)
            with open(os.path.join("./","trained_knn_list.clf"),"wb") as f:
                self.s3_client.download_fileobj(bucket,"trained_knn_list.clf",f)
