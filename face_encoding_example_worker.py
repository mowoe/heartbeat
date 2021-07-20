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
import queue
import tqdm


def replenish_queue(queue, host, port):
    print("replenishing queue...")
    for x in tqdm.tqdm(range(50)):
        resp = requests.get(
                "http://" + host + ":" + port + "/api/request_work?work_type=face_encodings"
            )
        resp_json = resp.json()
        image_id = resp_json["status"]
        if "empty" == resp_json["reason"]:
            #queue.put_nowait("empty")
            break
        queue.put_nowait(image_id)


class FaceRecThread(threading.Thread):
    def __init__(self, q, threadID, host, port):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.counter = 0
        self.host = host
        self.port = port
        self.q = q

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
            try:
                image_id = self.q.get(timeout=3)  # 3s timeout
                print(image_id)
            except queue.Empty:
                return
            # do whatever work you have to do on work
            
            fname = self.download_file(
                "http://"
                + self.host
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
                    "http://" + self.host + ":" + port + "/api/submit_work", data=data
                )
            else:
                face_encoding = {"encoding": []}
                data = {
                    "image_id": str(image_id),
                    "work_type": "face_encodings",
                    "result": json.dumps(face_encoding),
                }
                resp = requests.post(
                    "http://" + self.host + ":" + self.port + "/api/submit_work", data=data
                )
            self.counter += 1
            self.q.task_done()
        except Exception as e:
            print(e)
            face_encoding = {"encoding": []}
            data = {
                "image_id": str(image_id),
                "work_type": "face_encodings",
                "result": json.dumps(face_encoding),
            }
            resp = requests.post(
                "http://" + self.host + ":" + self.port + "/api/submit_work", data=data
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


def monitor(q, host, port, threads):
    start = time.time()
    time.sleep(5)
    while True:
        if q.qsize() < 40:
            replenish_queue(q,host,port)
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
    host = "heartbeat-pve"
    port = str(8000)
    num_threads = 1
    print(host,port,num_threads)
    q = queue.Queue()

    replenish_queue(q,host,port)

    threads = []
    
    for x in range(num_threads):
        thread = FaceRecThread(q, x, host, port)
        thread.start()
        threads.append(thread)
    
    monitor(q, host, port, threads)
