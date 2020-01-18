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
import hashlib

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
        uploaded_date = DateTimeField(default=datetime.datetime.now)
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
    def __init__(self, filename, object_storage_type, object_storage_auth, bucket):
        self.filename = filename
        self.bucket = bucket
        self.object_storage_type = object_storage_type
        self.object_storage_auth = object_storage_auth
        self.just_name = self.filename.split("/")[-1]
        if self.object_storage_type == "s3":
            self.s3_client = boto3.client("s3", **object_storage_auth)
            print("established s3 connection!")

    def safe_file(self):
        if self.object_storage_type == "openstack":
            swift_client = swiftclient.client.Connection(
                os_options=options, **self.object_storage_auth
            )
            with open(self.filename, "rb") as local:
                swift_client.put_object(
                    self.bucket,
                    self.just_name,
                    contents=local,
                    content_type="image/" + self.filename.split(".")[-1],
                )
            try:
                assert type(swift_client.head_object(self.bucket, self.just_name)) != type(
                    None
                )
            except AssertionError as e:
                print(e, str(e))
            finally:
                swift_client.close()

        elif self.object_storage_type == "s3":
            assert type(
                self.s3_client.upload_file(self.filename, self.bucket, self.just_name)
            ) != type(None)
            print("uploaded to s3!")

    def load_file(self):
        if self.object_storage_type == "openstack":
            swift_client = swiftclient.client.Connection(
                os_options=options, **self.object_storage_auth
            )
            resp_headers, obj_contents = swift_client.get_object(self.bucket, self.filename)
            with open(os.path.join("./", self.filename), "wb") as local:
                local.write(obj_contents)
            swift_client.close()

        elif self.object_storage_type == "s3":
            with open(os.path.join("./", self.filename), "wb") as f:
                self.s3_client.download_fileobj(self.bucket, self.filename, f)
            resp = send_file(os.path.join("./", self.filename), mimetype="image/png")
            os.remove(os.path.join("./", self.filename))
            return resp

    def delete_locally(self):
        os.remove(self.filename)


class HeartbeatDB(object):
    def __init__(self):
        pass

    def init_db(self, db_type, dbconfig, object_storage_type, object_storage_auth, bucket):
        mysql_db = peewee.MySQLDatabase(**dbconfig)
        self.Image, self.Results = setup_classes(mysql_db)
        self.db_type = db_type
        self.object_storage_type = object_storage_type
        self.object_storage_auth = object_storage_auth
        self.bucket = bucket
        mysql_db.connect()
        mysql_db.create_tables([self.Image, self.Results])
        mysql_db.close()
        return mysql_db

    def upload_file(self, filename, origin="unknown", other_data={"unknown": 1}):
        path = os.path.join("./uploaded_pics", filename)
        file_hash = hash_file(path)
        for result in self.Image.select().where(self.Image.file_hash==file_hash).execute():
            print("Duplicate!")
            return #An Image with the same hash is already in the database.
        image = self.Image(filename=filename, origin=origin, other_data=json.dumps(other_data), file_hash=file_hash)
        image.save()
        stored_image = StoredImage(
            path, self.object_storage_type, self.object_storage_auth, self.bucket
        )
        stored_image.safe_file()
        stored_image.delete_locally()

    def get_file(self, image_id):
        filename = self.Image.select().where(self.Image.id == image_id).get().filename
        stored_image = StoredImage(
            filename, self.object_storage_type, self.object_storage_auth, self.bucket
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
        remotelist = StoredImage(
            "trained_knn_list.clf", self.object_storage_type, self.object_storage_auth, self.bucket
        )
        remotelist.load_file()
        remotefile = StoredImage(
            "trained_knn_model.clf", self.object_storage_type, self.object_storage_auth, self.bucket
        )
        remotefile.load_file()

    def safe_model(self):
        remotelist = StoredImage(
            "trained_knn_list.clf", self.object_storage_type, self.object_storage_auth, self.bucket
        )
        remotelist.safe_file()
        remotefile = StoredImage(
            "trained_knn_model.clf", self.object_storage_type, self.object_storage_auth, self.bucket
        )
        remotefile.safe_file()
