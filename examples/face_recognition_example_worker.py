import face_recognition
import requests
import urllib.request
import urllib
import cgi
import json
import sys
import cv2
import threading
import hashlib
import time
import os

verbose = int(sys.argv[1])
print(verbose)

host = sys.argv[2]

class FaceRecThread(threading.Thread):
    def __init__(self,threadID,host):
        threading.Thread.__init__(self)
        self.threadID = threadID
    def download_file(self,url):
        hash_object = hashlib.sha256(str(time.time()).encode())
        hex_dig = hash_object.hexdigest()
        local_filename = str(hex_dig) + ".png"
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    if chunk: 
                        f.write(chunk)
        return local_filename

    def get_work(self):
        resp = requests.get("http://"+host+":5000/api/request_work?work_type=face_recognition")
        resp_json = resp.json()
        image_id = resp_json["status"]
        print(image_id)
        fname = self.download_file("http://"+host+":5000/api/download_image?image_id="+str(image_id))
        print("downloaded Image!")
        try:
            image = face_recognition.load_image_file(fname)
            print("detecting...")
            face_locations = face_recognition.face_locations(image)
            print(face_locations)
            resp = requests.get("http://"+host+":5000/api/submit_work?image_id="+str(image_id)+"&work_type=face_recognition&result="+json.dumps(face_locations))
        except Exception as e:
            print(e)
            resp = requests.get("http://"+host+":5000/api/submit_work?image_id="+str(image_id)+"&work_type=face_recognition&result=error")
        finally:
            os.remove(fname)

    def run(self):
        while True:
            print("Getting Work: {}".format(self.threadID))
            self.get_work()

if __name__ == "__main__":
    for x in range(int(sys.argv[3])):
        thread = FaceRecThread(x,host)
        thread.start()
