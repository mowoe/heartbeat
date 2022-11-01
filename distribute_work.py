import hashlib
import json
import time
from urllib.parse import urlparse

import face_recognition
import requests
from celery import Celery
from kombu.utils.url import safequote

import read_config

heartbeat_config = read_config.HeartbeatConfig()
heartbeat_config.setup()


if heartbeat_config.config["celery_aws_type"] == "elasticmq":
    celery = Celery('distribute_work', broker="sqs://x:x@localhost:9324")
    celery.conf["task_default_queue"] = heartbeat_config.config["celery_queue_name"]
elif heartbeat_config.config["celery_aws_type"] == "sqs":
    aws_access_key=safequote(heartbeat_config.config["celery_aws_key"])
    aws_secret_key=safequote(heartbeat_config.config["celery_aws_secret"])
    broker_url = f"sqs://{aws_access_key}:{aws_secret_key}@"
    celery = Celery('work_delivery.distribute_work', broker=broker_url)
    celery.conf["task_default_queue"] = heartbeat_config.config["celery_queue_name"]
    celery.conf["broker_transport_options"] = {
        'region': 'eu-central-1',
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
    local_filename = str(hex_dig) + ".png"
    with requests.get(url, stream=True) as response:
        response.raise_for_status()
        with open(local_filename, "wb") as opened_file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    opened_file.write(chunk)
    return local_filename


@celery.task
def facerec(url):
    local_filename = download_file(url)
    image = face_recognition.load_image_file(local_filename)
    face_locations = face_recognition.face_encodings(image)
    image_id = url.split("=")[-1]
    print(f"Image Id:{image_id}")
    for face_location in face_locations:
        print(f"Found Face {face_location}")
        face_encoding = {"encoding": list(face_location)}
        data = {
            "work_type": "face_encodings",
            "image_id": str(image_id),
            "result": json.dumps(face_encoding)
        }
        parsed_uri = urlparse(url)
        result = f'{parsed_uri.scheme}://{parsed_uri.netloc}'
        requests.post(f"{result}/api/submit_work", data=data)
    if len(face_locations) < 1:
        print("Found no faces.")
        face_encoding = {"encoding": []}
        data = {
            "work_type": "face_encodings",
            "image_id": str(image_id),
            "result": json.dumps(face_encoding)
        }
        parsed_uri = urlparse(url)
        result = '{uri.scheme}://{uri.netloc}'.format(uri=parsed_uri)
        requests.post(f"{result}/api/submit_work", data=data)
