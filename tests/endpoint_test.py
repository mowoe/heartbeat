import requests
import json

resp = requests.get("http://localhost:5000/")
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
    
resp = requests.post("http://localhost:5000"+"/api/add_image",data=data,headers=headers)
if resp.status_code != 200:
    print(resp.text)
    exit(1)
resp = requests.get("http://localhost:5000/api/request_work?work_type=face_encodings")
if resp.status_code != 200:
    print(resp.text)
    exit(1)
resp_json = resp.json()
image_id = resp_json["status"]
fname = self.download_file("http://localhost:5000"+"/api/download_image?image_id="+str(image_id))
image = face_recognition.load_image_file(fname)
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
    resp = requests.post("http://localhost:5000"+"/api/submit_work",data=data)
    if resp.status_code != 200:
        print(resp.text)
        exit(1)
if not ran:
    face_encoding = {"encoding":[]}
    data = {
        "image_id":str(image_id),
        "work_type":"face_encodings",
        "result":json.dumps(face_encoding)
    }
    resp = requests.post("http://localhost:5000"+"/api/submit_work",data=data)
    if resp.status_code != 200:
        print(resp.text)
        exit(1)