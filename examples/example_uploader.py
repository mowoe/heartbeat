#This File uploads all images from a directory to heartbeat

import requests
import sys
from os import listdir
from os.path import isfile, join

host,port = "localhost",str(5000)

mypath = sys.argv[1]

onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]

for fil in onlyfiles:
    if "jpg" in fil or "png" in fil or "jpeg" in fil:
        print("uploading: "+mypath+fil)
        files = {'file': open(mypath+fil,'rb')}
        #start = time.time()
        r = requests.post("http://"+host+":"+port+"/api/add_image_via_file", files=files, allow_redirects=False)
        print(r.text)

print("done")
