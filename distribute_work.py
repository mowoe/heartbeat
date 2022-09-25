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

def read_celery_conf():
    if os.path.exists("./heartbeat_celery_conf.json"):
        with open("heartbeat_celery_conf.json","r") as f:
            cfile = json.load(f)
            queue_name = cfile["QUEUE_NAME"]
            queue_url = cfile["QUEUE_URL"]
            aws_secret_key = cfile["AWS_SECRET_KEY"]
            aws_access_key = cfile["AWS_ACCESS_KEY"]
        return queue_name, queue_url, safequote(aws_secret_key), safequote(aws_access_key)
    else:
        raise Exception("Config for celery not found.")


queue_name, queue_url, aws_secret_key, aws_access_key = read_celery_conf()

broker_url = "sqs://{aws_access_key}:{aws_secret_key}@".format(
    aws_access_key=aws_access_key, aws_secret_key=aws_secret_key,
)

broker_transport_options = {'region': 'eu-central-1'}

celery = Celery('work_delivery.distribute_work', broker=broker_url)

celery.conf["task_default_queue"] = queue_name
celery.conf["broker_transport_options"] = {
    'region': 'eu-central-1',
    'predefined_queues': {
       queue_name: {
            'url': queue_url
        }
    }
}


def download_file(url):
    hash_object = hashlib.sha256(str(time.time()).encode())
    hex_dig = hash_object.hexdigest()
    local_filename = str(hex_dig) + ".png"
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
