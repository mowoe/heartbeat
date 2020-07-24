import peewee
import requests
from peewee import MySQLDatabase, SqliteDatabase
from peewee import CharField, ForeignKeyField, DateTimeField, fn, BooleanField, TimestampField
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
import hashlib
from shutil import copyfile

bucket = "heartbeat-images"
object_storage_auth = ""
options = {"region_name": "DE1"}
BUF_SIZE = 1024

def hash_file(filename):
    sha1 = hashlib.sha1()
    with open(filename, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha1.update(data)
    return sha1.hexdigest()

def setup_classes(mysql_db):
    class Image(peewee.Model):
        filename = CharField()
        uploaded_date = TimestampField(default=time.time())
        origin = CharField(default="unknown")
        other_data = CharField(default="null", max_length=7000)
        face_rec_worked = BooleanField(default=False)
        file_hash = CharField(default=None)

        class Meta:
            database = mysql_db

    class Results(peewee.Model):
        image_id = CharField()
        result_type = CharField()
        result = CharField(max_length=7000)

        class Meta:
            database = mysql_db

    return Image, Results


class StoredImage(object):
    def __init__(self, filename, object_storage_type, object_storage_auth):
        self.filename = filename
        self.object_storage_type = object_storage_type
        self.object_storage_auth = object_storage_auth
        self.just_name = self.filename.split("/")[-1]
        if self.object_storage_type == "s3":
            self.s3_client = boto3.client("s3", **object_storage_auth)
            print("established s3 connection!")
        elif self.object_storage_type == "local":
            if not os.path.exists("./heartbeat-images"):
                os.makedirs("./heartbeat-images")

    def safe_file(self):
        if self.object_storage_type == "openstack":
            swift_client = swiftclient.client.Connection(
                os_options=options, **self.object_storage_auth
            )
            with open(self.filename, "rb") as local:
                swift_client.put_object(
                    bucket,
                    self.just_name,
                    contents=local,
                    content_type="image/" + self.filename.split(".")[-1],
                )
            try:
                assert type(swift_client.head_object(bucket, self.just_name)) != type(
                    None
                )
            except AssertionError as e:
                print(e, str(e))
            finally:
                swift_client.close()

        elif self.object_storage_type == "s3":
            self.s3_client.upload_file(self.filename, bucket, self.just_name)
            print("uploaded to s3!")

        elif self.object_storage_type == "local":
            copyfile(self.filename, os.path.join("./heartbeat-images", self.filename.split("/")[-1]))



    def load_file(self):
        if self.object_storage_type == "openstack":
            swift_client = swiftclient.client.Connection(
                os_options=options, **self.object_storage_auth
            )
            resp_headers, obj_contents = swift_client.get_object(bucket, self.filename)
            with open(os.path.join("./", self.filename), "wb") as local:
                local.write(obj_contents)
            swift_client.close()

        elif self.object_storage_type == "s3":
            with open(os.path.join("./", self.filename), "wb") as f:
                self.s3_client.download_fileobj(bucket, self.filename, f)

        elif self.object_storage_type == "local":
            copyfile(os.path.join("./heartbeat-images", self.filename.split("/")[-1]),os.path.join(".",self.filename))


    def delete_locally(self):
        os.remove(self.filename)


class HeartbeatDB(object):
    def __init__(self):
        pass

    def init_db(self, db_type, dbconfig, object_storage_type, object_storage_auth):
        mysql_db = peewee.MySQLDatabase(**dbconfig)
        self.Image, self.Results = setup_classes(mysql_db)
        self.db_type = db_type
        self.object_storage_type = object_storage_type
        self.object_storage_auth = object_storage_auth
        mysql_db.connect()
        mysql_db.create_tables([self.Image, self.Results])
        mysql_db.close()
        return mysql_db

    def upload_file(self, filename, origin="unknown", other_data={"unknown": 1}):
        path = os.path.join("./uploaded_pics", filename)
        file_hash = hash_file(path)
        for result in self.Image.select().where(self.Image.file_hash==file_hash).execute():
            print("Duplicate: {}!".format(file_hash))
            return #An Image with the same hash is already in the database.
        image = self.Image(filename=filename, origin=origin, other_data=other_data, file_hash=file_hash)
        print("Uploaded to DB.")
        image.save()
        stored_image = StoredImage(
            path, self.object_storage_type, self.object_storage_auth
        )
        print("Uploaded to Object Storage.")
        stored_image.safe_file()
        stored_image.delete_locally()

    def get_file(self, image_id):
        filename = self.Image.select().where(self.Image.id == image_id).get().filename
        stored_image = StoredImage(
            filename, self.object_storage_type, self.object_storage_auth
        )
        stored_image.load_file()
        resp = send_file(os.path.join("./", filename), mimetype="image/png")
        stored_image.delete_locally()
        return resp

    def get_all_work(self, work_type):
        query = self.Results.select().where(self.Results.result_type == work_type)
        results = []
        for x in query:
            results.append([x.image_id, x.id, x.result])
        return results

    def request_work(self, work_type):
        query = self.Image.select().where(self.Image.face_rec_worked == False).limit(60)
        results = []
        for x in query:
            results.append(x.id)
        random.shuffle(results)
        return results

    def submit_work(self, work_type, image_id, result):
        result = self.Results(image_id=image_id, result=result, result_type=work_type)
        result.save()
        query = self.Image.update(face_rec_worked=True).where(self.Image.id == image_id)
        query.execute()

    def get_imgobj_from_id(self, image_id):
        return self.Image.select().where(self.Image.id == image_id).get()

    def retrieve_model(self):
        if os.path.isfile("trained_knn_list.clf"):
            if int(os.path.getmtime('trained_knn_list.clf')) < (int(time.time()-3600)):
                print("Model is already new enough")
                return
        print("Downloading model.")
        remotelist = StoredImage(
            "trained_knn_list.clf", self.object_storage_type, self.object_storage_auth
        )
        remotelist.load_file()
        remotefile = StoredImage(
            "trained_knn_model.clf", self.object_storage_type, self.object_storage_auth
        )
        remotefile.load_file()

    def safe_model(self):
        remotelist = StoredImage(
            "trained_knn_list.clf", self.object_storage_type, self.object_storage_auth
        )
        remotelist.safe_file()
        remotefile = StoredImage(
            "trained_knn_model.clf", self.object_storage_type, self.object_storage_auth
        )
        remotefile.safe_file()
