import hashlib
import json
import os
import random
import time
from shutil import copyfile

import boto3
import peewee
import swiftclient
import tqdm
from peewee import (JOIN, BooleanField, CharField)

BUCKET = "heartbeat-images"
OBJECT_STORAGE_AUTH = ""
OPTIONS = {"region_name": "DE1"}
BUF_SIZE = 1024


def hash_file(filename):
    sha1 = hashlib.sha1()
    with open(filename, 'rb') as opened_file:
        while True:
            data = opened_file.read(BUF_SIZE)
            if not data:
                break
            sha1.update(data)
    return sha1.hexdigest()


def setup_classes(mysql_db):
    class Image(peewee.Model):
        filename = CharField()
        #uploaded_date = TimestampField(default=time.time)
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


class StoredImage:
    def __init__(self, filename, object_storage_type, object_storage_auth):
        self.filename = filename
        self.object_storage_type = object_storage_type
        self.object_storage_auth = object_storage_auth
        self.just_name = self.filename.split("/")[-1]
        if self.object_storage_type == "s3":
            self.s3_client = boto3.client("s3", **object_storage_auth)
            #print("established s3 connection!")
        elif self.object_storage_type == "local":
            if not os.path.exists("./heartbeat-images"):
                os.makedirs("./heartbeat-images")

    def safe_file(self):
        if self.object_storage_type == "openstack":
            swift_client = swiftclient.client.Connection(
                os_options=OPTIONS, **self.object_storage_auth
            )
            with open(self.filename, "rb") as local:
                swift_client.put_object(
                    BUCKET,
                    self.just_name,
                    contents=local,
                    content_type="image/" + self.filename.split(".")[-1],
                )
            try:
                assert not isinstance(swift_client.head_object(
                    BUCKET, self.just_name), type(None))
            except AssertionError as error:
                print(error, str(error))
            finally:
                swift_client.close()

        elif self.object_storage_type == "s3":
            self.s3_client.upload_file(self.filename, BUCKET, self.just_name)
            print("uploaded to s3!")

        elif self.object_storage_type == "local":
            copyfile(self.filename, os.path.join(
                "./heartbeat-images", self.filename.split("/")[-1]))

    def remove_file(self):
        #print("Deleting {}".format(self.filename))
        if self.object_storage_type == "openstack":
            raise NotImplementedError

        if self.object_storage_type == "s3":
            # print(self.filename)
            self.s3_client.delete_object(
                Bucket=BUCKET, Key=self.filename)
            # print(delete)

        elif self.object_storage_type == "local":
            os.remove(os.path.join("./heartbeat-images", self.filename))
        #print("removed {}".format(self.filename))

    def load_file(self):
        if self.object_storage_type == "openstack":
            swift_client = swiftclient.client.Connection(
                os_options=OPTIONS, **self.object_storage_auth
            )
            resp_headers, obj_contents = swift_client.get_object(
                BUCKET, self.filename)
            with open(os.path.join("./", self.filename), "wb") as local:
                local.write(obj_contents)
            swift_client.close()

        elif self.object_storage_type == "s3":
            with open(os.path.join("./", self.filename), "wb") as opened_file:
                self.s3_client.download_fileobj(
                    BUCKET, self.filename, opened_file)

        elif self.object_storage_type == "local":
            copyfile(os.path.join("./heartbeat-images",
                     self.filename.split("/")[-1]), os.path.join(".", self.filename))

    def get_all_files(self):
        if self.object_storage_type == "openstack":
            raise NotImplementedError
        if self.object_storage_type == "s3":
            files = []
            for key in self.s3_client.list_objects(Bucket=BUCKET)['Contents']:
                files.append(key["Key"])
            return files

        if self.object_storage_type == "local":
            files = []
            for filename in os.listdir("./heartbeat-images"):
                if os.path.isfile(os.path.join("./heartbeat-images", filename)):
                    files.append(filename)
            return files

    def delete_locally(self):
        os.remove(self.filename)


class HeartbeatDB:
    def __init__(self):
        self.Image, self.Results = None, None
        self.db_type = None
        self.object_storage_type = None
        self.object_storage_auth = None

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

    def upload_file(self, filename, other_data, origin="unknown"):
        if not other_data:
            other_data = {"unknown": 1}
        path = os.path.join("./uploaded_pics", filename)
        file_hash = hash_file(path)
        for result in self.Image.select().where(self.Image.file_hash == file_hash).execute():
            res = {
                "status": "error",
                "message": "This Image is already in our Database."
            }
            # An Image with the same hash is already in the database.
            return res
        other_data = json.dumps(other_data)
        image = self.Image(filename=filename, origin=origin,
                           other_data=other_data, file_hash=file_hash)
        image.save()
        stored_image = StoredImage(
            path, self.object_storage_type, self.object_storage_auth
        )
        stored_image.safe_file()
        stored_image.delete_locally()
        res = {
            "status": "success",
            "message": f"This image got assigned ID {image.id}. \
                Permalink: /api/download_image?image_id={image.id}",
            "id": image.id,
            "link": f"/api/download_image?image_id={image.id}"
        }
        return res

    def get_file(self, image_id):
        filename = self.Image.select().where(self.Image.id == image_id).get().filename
        stored_image = StoredImage(
            filename, self.object_storage_type, self.object_storage_auth
        )
        stored_image.load_file()
        return filename

    def get_all_work(self, work_type):
        query = self.Results.select().where(self.Results.result_type == work_type)
        results = []
        for result in query:
            results.append([result.image_id, result.id, result.result])
        return results

    def request_work(self, work_type):
        query = self.Image.select().where(self.Image.face_rec_worked ==
                                          False).order_by(peewee.fn.Rand()).limit(60)
        results = []
        for result in query:
            results.append(result.id)
        random.shuffle(results)
        return results

    def submit_work(self, work_type, image_id, result):
        result = self.Results(
            image_id=image_id, result=result, result_type=work_type)
        result.save()
        query = self.Image.update(face_rec_worked=True).where(
            self.Image.id == image_id)
        query.execute()

    def get_imgobj_from_id(self, image_id):
        return self.Image.select().where(self.Image.id == image_id).get()

    def retrieve_model(self):
        if os.path.isfile("trained_knn_list.clf"):
            if int(os.path.getmtime('trained_knn_list.clf')) < (int(time.time()-3600)):
                print("Model is already new enough")
                return 0
        print("Downloading model.")
        remotelist = StoredImage(
            "trained_knn_list.clf", self.object_storage_type, self.object_storage_auth
        )
        remotefile = StoredImage(
            "trained_knn_model.clf", self.object_storage_type, self.object_storage_auth
        )
        try:
            remotelist.load_file()
            remotefile.load_file()
            return 0
        except FileNotFoundError:
            return 1

    def safe_model(self):
        remotelist = StoredImage(
            "trained_knn_list.clf", self.object_storage_type, self.object_storage_auth
        )
        remotelist.safe_file()
        remotefile = StoredImage(
            "trained_knn_model.clf", self.object_storage_type, self.object_storage_auth
        )
        remotefile.safe_file()

    def get_stats(self):
        count_processed = self.Image.select().where(
            self.Image.face_rec_worked == True).count()
        count_total = self.Image.select().count()
        count_encodings = self.Results.select().where(
            self.Results.result != "{\"encoding\": []}").count()
        return [count_processed, count_total, count_encodings]

    def delete_empty(self):
        res = self.Results.delete().where(self.Results.result ==
                                          "{\"encoding\": []}").execute()
        print(f"Deleted {res} empty encodings.")
        query = self.Image.select().join(self.Results, JOIN.LEFT_OUTER,
                                         on=self.Image.id ==
                                         self.Results.image_id).where(
            self.Results.image_id.is_null())
        print(query)
        for image in tqdm.tqdm(query):
            #print(image.id, image.filename, image.face_rec_worked)
            if image.face_rec_worked:
                stored_image = StoredImage(
                    image.filename, self.object_storage_type, self.object_storage_auth
                )
                stored_image.remove_file()
                image.delete_instance()
        print("Checking if DB and filestorage are in sync...")
        stored_image = StoredImage(
            "dummyfile", self.object_storage_type, self.object_storage_auth)
        files = stored_image.get_all_files()
        for filename in files:
            hits = self.Image.select().where(self.Image.filename == filename).count()
            if hits < 1:
                print(f"File {filename} was not found in db")
            else:
                print(f"File {filename} was found in db")

    def check_operational(self):
        count_processed, count_total, count_encodings = self.get_stats()
        not_operational = count_encodings <= 5
        retrieve_model_unsuccessful = self.retrieve_model()
        if not not_operational:
            not_operational = retrieve_model_unsuccessful

        return not_operational
