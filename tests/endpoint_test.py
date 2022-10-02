import requests
import json
import hashlib
import time

url = "http://127.0.0.1:80"

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

import numpy
from PIL import Image

imarray = numpy.random.rand(100,100,3) * 255
im = Image.fromarray(imarray.astype('uint8')).convert('RGBA')
im.save('result_image.png')
files = {'file': open('result_image.png','rb')}

data = {
        'origin':"test",
        'img_info':json.dumps({
            "img_was_found_on":"test"
        }),
}
    
resp = requests.post(url+"/api/add_image_file",data=data, files=files)
print(resp.text)
if resp.status_code != 200:
    print(resp.text)
    exit(1)
assert resp.json()["status"] != "error"
print("Uploading succeeded!")

#Wait 10 seconds, to let the workers pickup our uploaded image
time.sleep(10)

#Test correct encoding numbers
resp = requests.get(url+"/api/get_stats")
resp = resp.json()
print(resp)
assert resp["processed"] == 1
assert resp["total"] == 1
assert resp["encodings"] == 0