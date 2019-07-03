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

verbose = sys.argv[1]
print(verbose)

host = sys.argv[2]
port = str(sys.argv[4])

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
        resp = requests.get("http://"+host+":"+port+"/api/request_work?work_type=face_encodings")
        resp_json = resp.json()
        image_id = resp_json["status"]
        if "empty" == resp_json["reason"]:
            print("empty")
            return
        print(image_id)
        fname = self.download_file("http://"+host+":"+port+"/api/download_image?image_id="+str(image_id))
        print("downloaded Image!")
        try:

            image = face_recognition.load_image_file(fname)
            print("detecting...")
            face_locations = face_recognition.face_encodings(image)
            ran = False
            for location in face_locations:
                ran = True                
                face_encoding = {"encoding":list(location)}
                data = {
                    "image_id":str(image_id),
                    "work_type":"face_encodings",
                    "result":json.dumps(face_encoding)
                }
                resp = requests.post("http://"+host+":"+port+"/api/submit_work",data=data)
                print(resp.text)
            if not ran:
                face_encoding = {"encoding":[]}
                data = {
                    "image_id":str(image_id),
                    "work_type":"face_encodings",
                    "result":json.dumps(face_encoding)
                }
                resp = requests.post("http://"+host+":"+port+"/api/submit_work",data=data)
        except Exception as e:
            face_encoding = {"encoding":[]}
            data = {
                "image_id":str(image_id),
                "work_type":"face_encodings",
                "result":json.dumps(face_encoding)
            }
            resp = requests.post("http://"+host+":"+port+"/api/submit_work",data=data)
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
