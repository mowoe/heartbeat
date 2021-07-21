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
import faulthandler

faulthandler.enable()
queueLock = threading.Lock()

def replenish_queue(queue, host, port):
    print("replenishing queue...")
    queueLock.acquire()
    img_ids = []
    for x in tqdm.tqdm(range(50)):
        resp = requests.get(
                "http://" + host + ":" + port + "/api/request_work?work_type=face_encodings"
            )
        resp_json = resp.json()
        image_id = resp_json["status"]
        if "empty" == resp_json["reason"]:
            #queue.put_nowait("empty")
            break
        img_ids.append(image_id)
    for image_id in tqdm.tqdm(img_ids):    
        queue.put(image_id)
    queueLock.release()


class Submitter(threading.Thread):
    def __init__(self,submit_queue,host,port):
        self.submit_queue = submit_queue
        self.host = host
        self.port = port
        threading.Thread.__init__(self)
    
    def work(self):
        try:
            data = self.submit_queue.get(timeout=3)
        except queue.Empty:
            return
        work_type = data["work_type"]
        if work_type == "face_encodings":
            resp = requests.post("http://{}:{}/api/submit_work".format(self.host,self.port),data=data)
            print(resp.text)

    def run(self):
        print("Submitter thread starting...")
        while True:
            self.work()


class FaceRecThread(threading.Thread):
    def __init__(self, q, threadID, host, port, submit_queue):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.counter = 0
        self.host = host
        self.port = port
        self.q = q
        self.submit_queue = submit_queue

    def download_file(self, url):
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
    


    def get_work(self):
        if queueLock.locked():
            time.sleep(5)
            return
        try:
            try:
                image_id = self.q.get(timeout=3)  
            except queue.Empty:
                return

            fname = self.download_file("http://{}:{}/api/download_image?image_id={}".format(self.host,self.port,image_id))

            image = face_recognition.load_image_file(fname)
            face_locations = face_recognition.face_encodings(image)

            

            for location in face_locations:
                face_encoding = {"encoding": list(location)}
                self.submit_queue.put({
                    "work_type": "face_encodings",
                    "image_id": str(image_id),
                    "result":json.dumps(face_encoding)
                })                
            else:
                face_encoding = {"encoding": []}
                self.submit_queue.put({
                    "work_type": "face_encodings",
                    "image_id": str(image_id),
                    "result":json.dumps(face_encoding)
                })   
            
            self.counter += 1
            self.q.task_done()
        finally:
            if os.path.isfile(fname):
                os.remove(fname)

    def run(self):
        print("Thread {} starting...".format(self.threadID))
        while True:
            self.get_work()


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

    submit_queue = queue.Queue()
    submitter = Submitter(submit_queue,host,port)

    threads = []
    
    for x in range(num_threads):
        thread = FaceRecThread(q, x, host, port, submit_queue)
        thread.start()
        threads.append(thread)
    
    submitter.start()

    monitor(q, host, port, threads)
