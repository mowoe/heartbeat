import face_recognition
import requests
import urllib.request
import urllib
import cgi

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

if __name__ == "__main__":
    get_work()
