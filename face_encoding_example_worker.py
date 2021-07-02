import face_recognition
import requests
import urllib.request
import urllib
import cgi
import json
import sys
import threading
import hashlib
import time
import os
import argparse

verbose = True

if not os.path.isfile("./config.json"):
    first_run = True
    if type(os.environ.get("HB_HOST")) == type(None):
        print("No Host supplied!")
        exit()
    config = {"host": os.environ.get("HB_HOST"), "port": str(os.environ.get("HB_PORT"))}
    with open("./config.json", "w") as f:
        json.dump(config, f)

with open("./config.json", "r") as f:
    config = json.load(f)
    host = config["host"]
    port = config["port"]

parser = argparse.ArgumentParser(description='Do Facerec stuff on heartbeat.')
parser.add_argument('port', metavar='N', type=str,
                     help='an integer for the accumulator')
parser.add_argument('host', metavar='N', type=str,
                     help='an integer for the accumulator')       
parser.add_argument('num_threads', metavar='N', type=int,
                     help='an integer for the accumulator')           
args = parser.parse_args()
host = args.host
port = args.port
num_threads = args.num_threads
print(host,port,num_threads)

class FaceRecThread(threading.Thread):
    def __init__(self, threadID, host):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.counter = 0

    def download_file(self, url):
        try:
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
        except Exception as e:
            print(e)

    def get_work(self):
        try:
            resp = requests.get(
                "http://" + host + ":" + port + "/api/request_work?work_type=face_encodings"
            )
            resp_json = resp.json()
            image_id = resp_json["status"]
            if "empty" == resp_json["reason"]:
                #print("empty")
                fname = ""
                return
            fname = self.download_file(
                "http://"
                + host
                + ":"
                + port
                + "/api/download_image?image_id="
                + str(image_id)
            )
            image = face_recognition.load_image_file(fname)
            face_locations = face_recognition.face_encodings(image)
            for location in face_locations:
                face_encoding = {"encoding": list(location)}
                data = {
                    "image_id": str(image_id),
                    "work_type": "face_encodings",
                    "result": json.dumps(face_encoding),
                }
                resp = requests.post(
                    "http://" + host + ":" + port + "/api/submit_work", data=data
                )
            else:
                face_encoding = {"encoding": []}
                data = {
                    "image_id": str(image_id),
                    "work_type": "face_encodings",
                    "result": json.dumps(face_encoding),
                }
                resp = requests.post(
                    "http://" + host + ":" + port + "/api/submit_work", data=data
                )
            self.counter += 1
        except Exception as e:
            print(e)
            face_encoding = {"encoding": []}
            data = {
                "image_id": str(image_id),
                "work_type": "face_encodings",
                "result": json.dumps(face_encoding),
            }
            resp = requests.post(
                "http://" + host + ":" + port + "/api/submit_work", data=data
            )
        finally:
            if os.path.isfile(fname):
                os.remove(fname)

    def run(self):
        print("Thread {} starting...".format(self.threadID))
        while True:
            try:
                self.get_work()
            except Exception as e:
                print(e)
            time.sleep(1)


def monitor(threads):
    start = time.time()
    time.sleep(5)
    while True:
        all_sums = 0
        for thread in threads:
            all_sums += thread.counter
        al = int(time.time() - start)
        # print("-"*100)
        print(
            "In sum processed images (not empty): {} in {} seconds -> {}i/s".format(
                all_sums, al, round(all_sums / al, 3)
            )
        )
        print("-" * 100)
        time.sleep(10)


if __name__ == "__main__":
    threads = []
    for x in range(num_threads):
        thread = FaceRecThread(x, host)
        thread.start()
        threads.append(thread)
    monitor(threads)
