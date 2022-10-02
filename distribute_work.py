from kombu.utils.url import safequote
from celery import Celery
import os
import json
import face_recognition
import requests
import urllib.request
import hashlib
import time
from urllib.parse import urlparse
import read_config

heartbeat_config = read_config.HeartbeatConfig()
heartbeat_config.setup()


if heartbeat_config.config["celery_aws_type"] == "elasticmq":
    celery = Celery('distribute_work', broker="sqs://x:x@localhost:9324")
    celery.conf["task_default_queue"] = heartbeat_config.config["celery_queue_name"]
elif heartbeat_config.config["celery_aws_type"] == "sqs":
    broker_url = "sqs://{aws_access_key}:{aws_secret_key}@".format(
        aws_access_key=safequote(heartbeat_config.config["celery_aws_key"]), aws_secret_key=safequote(heartbeat_config.config["celery_aws_secret"]),
    )
    celery = Celery('work_delivery.distribute_work', broker=broker_url)
    celery.conf["task_default_queue"] = heartbeat_config.config["celery_queue_name"]
    celery.conf["broker_transport_options"] = {
        'region': 'elasticmq',
        'predefined_queues': {
        heartbeat_config.config["celery_queue_name"]: {
                'url': heartbeat_config.config["celery_queue_url"]
            }
        }
    }
else:
    raise NotImplementedError


def download_file(url):
    hash_object = hashlib.sha256(str(time.time()).encode())
    hex_dig = hash_object.hexdigest()
    local_filename = "/home/celery/"+str(hex_dig) + ".png"
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    return local_filename


@celery.task
def facerec(url):
    lf = download_file(url)
    image = face_recognition.load_image_file(lf)
    face_locations = face_recognition.face_encodings(image)
    image_id = url.split("=")[-1]
    print("Image Id:{}".format(image_id))
    for n in face_locations:
        print("Found Face {}".format(n))
        face_encoding = {"encoding": list(n)}
        data = {
            "work_type": "face_encodings",
            "image_id": str(image_id),
            "result":json.dumps(face_encoding)
        }
        parsed_uri = urlparse(url)
        result = '{uri.scheme}://{uri.netloc}'.format(uri=parsed_uri)
        resp = requests.post("{}/api/submit_work".format(result),data = data)
