#This File uploads all images from a directory to heartbeat

import requests
import sys
from os import listdir
from os.path import isfile, join
import json
import tqdm 

host,port = "localhost",str(8000)

mypath = sys.argv[1] #Folder to upload
source = sys.argv[2] #The source where the images come from e.g. "google.com" or "camera"

payload = {
    "img_info":json.dumps({
        "source":source
    }),
    "origin":source
}

onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]

for fil in tqdm.tqdm(onlyfiles):
    if "jpg" in fil or "png" in fil or "jpeg" in fil:
        print("uploading: "+mypath+fil)
        files = {'file': open(mypath+fil,'rb')}
        #start = time.time()

        r = requests.post("http://{}:{}/api/add_image_file".format(host,port), files=files, allow_redirects=False, data=payload)
        print(r.text)

print("done")
