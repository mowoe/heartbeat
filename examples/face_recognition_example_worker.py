import face_recognition
import requests
import urllib.request
import urllib
import cgi
import json
import sys
import cv2

verbose = int(sys.argv[1])
print(verbose)

def get_work():
    resp = requests.get("http://localhost:9721/request_work/face_recognition")
    resp_json = resp.json()
    image_id = resp_json["status"]
    response = urllib.request.urlopen("http://localhost:9721/get_image/"+str(image_id))
    _, params = cgi.parse_header(response.headers.get('Content-Disposition', ''))
    filename = params['filename']
    fname_end = filename.split(".")[-1]
    print("Received ImageID: {}".format(image_id))
    urllib.request.urlretrieve("http://localhost:9721/get_image/"+str(image_id),"face_rec_fram."+fname_end)
    print("downloaded Image!")
    image = face_recognition.load_image_file("face_rec_fram."+fname_end)
    print("detecting...")
    face_locations = face_recognition.face_locations(image)
    print(face_locations)
    resp = requests.get("http://localhost:9721/submit_work?imageid="+str(image_id)+"&table=face_recognition&info="+json.dumps(face_locations))
    if verbose:
        cvimg = cv2.imread("face_rec_fram."+fname_end)
        for face_location in face_locations:
            top, right, bottom, left = face_location
            print("A face is located at pixel location Top: {}, Left: {}, Bottom: {}, Right: {}".format(top, left, bottom, right))
            cv2.rectangle(cvimg,(left,top),(right,bottom),(255,0,0),2)
        cv2.imshow("faces",cv2.resize(cvimg,(0,0),fx=0.5,fy=0.5))
        cv2.waitKey(0)

if __name__ == "__main__":
    while True:
        get_work()
