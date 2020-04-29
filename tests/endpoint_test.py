import requests
import json
import hashlib
import time

url = "http://heartbeat:80"

def download_file(donw_url):
    hash_object = hashlib.sha256(str(time.time()).encode())
    hex_dig = hash_object.hexdigest()
    local_filename = str(hex_dig) + ".png"
    with requests.get(donw_url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): 
                if chunk: 
                    f.write(chunk)
    return local_filename

resp = requests.get(url+"/")
if resp.status_code != 200:
    print(resp.text)
    exit(1)
data = {
        'origin':"test",
        'img_info':json.dumps({
            "img_was_found_on":"test"
        }),
        'img_url':'https://mowoe.com/flasche_quadrat.png'
}
    
resp = requests.post(url+"/api/add_image",data=data)
if resp.status_code != 200:
    print(resp.text)
    exit(1)
print("Uploading succeeded!")
resp = requests.get(url+"/api/request_work?work_type=face_encodings")
if resp.status_code != 200:
    print(resp.text)
    exit(1)
print("Requesting work succeeded!")
resp_json = resp.json()
print(resp_json)
image_id = resp_json["status"]
print(image_id)
fname = download_file(url+"/api/download_image?image_id="+str(image_id))
print("Filename for downloading is: {}".format(fname))    
face_encoding = {"encoding":[]}
data = {
    "image_id":str(image_id),
    "work_type":"face_encodings",
    "result":json.dumps(face_encoding)
}
resp = requests.post(url+"/api/submit_work",data=data)
if resp.status_code != 200:
    print(resp.text)
    exit(1)
print("Submitting data succeeded!")  
