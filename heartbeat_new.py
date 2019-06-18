from flask import Flask
from flask import request, make_response
from flask import send_file, render_template
import hashlib
from werkzeug.utils import secure_filename
import time
import os
from peewee import MySQLDatabase
from peewee import CharField, ForeignKeyField, DateTimeField, fn
import peewee
import datetime
import json
import math
from sklearn import neighbors
import os.path
import pickle
import face_recognition
from face_recognition.face_recognition_cli import image_files_in_folder
import numpy as np
import requests


UPLOAD_FOLDER = './uploaded_pics/'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
dbconfig = json.load(open("db_auth.json","rb"))
mysql_db = peewee.MySQLDatabase(**dbconfig)
model_path = "./examples/trained_knn_model.clf"
distance_threshold = 0.4


class Image(peewee.Model):
    filename = CharField()
    uploaded_date = DateTimeField(default=datetime.datetime.now)
    origin = CharField(default="unknown")
    other_data = CharField(default="null")
    class Meta:
        database = mysql_db

class Results(peewee.Model):
    image_id = CharField()#ForeignKeyField(Image, backref='id')
    result_type = CharField()
    result = CharField()
    class Meta:
        database = mysql_db

class ResultStatus(peewee.Model):
    image_id = CharField()#ForeignKeyField(Image, backref='id')
    result_type = CharField()
    class Meta:
        database = mysql_db


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def constr_resp(status,reason="healthy"):
        return json.dumps({'status':status, 'reason':reason})

@app.before_request
def _db_connect():
    mysql_db.connect()

@app.teardown_request
def _db_close(exc):
    if not mysql_db.is_closed():
        mysql_db.close()

@app.route("/api/add_image")
def add_image():
    img_url = request.args.get('img_url')
    information = request.args.get('img_info')
    if type(img_url) == type(None) or type(information) == type(None):
        response = Response(constr_resp("error","No url or Image provided"), status=401, headers={})
        return response
    information = json.loads(information)
    response = Response(constr_resp("success"), status=200, headers={})
    return response


@app.route("/api/add_image_via_file",methods=['POST'])
def add_file():
    if 'file' not in request.files:
        return constr_resp("error","no file part")
    file = request.files['file']
    if file.filename == '':
        return constr_resp("error","no file supplied")
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        hash_object = hashlib.sha256(str(time.time()).encode())
        hex_dig = hash_object.hexdigest()
        new_filename = str(hex_dig) + "." + filename.split(".")[-1]
        file.save(os.path.join(UPLOAD_FOLDER, new_filename))
        image = Image(filename=new_filename)
        image.save()
        return constr_resp("success")
    return constr_resp("error","unknown")

@app.route("/api/request_work",methods=['GET'])
def request_work():
    start = time.time()
    work_type = request.args.get('work_type')
    #print(work_type)
    already_worked = Results.select(Results.image_id).where(Results.result_type==work_type)
    query = Image.select().where(Image.id.not_in(already_worked)).order_by(fn.Rand())
    results = []
    for x in query:
        results.append(x.id)
    print("get work took {} seconds".format(time.time()-start))
    return constr_resp(str(results[0]))

@app.route("/api/submit_work",methods=['POST'])
def submit_work():
    start = time.time()
    work_type = request.form.get('work_type')
    img_id = request.form.get('image_id')
    resulted = request.form.get('result')
    #print(work_type,img_id,resulted)
    result = Results(image_id=img_id,result=resulted,result_type=work_type)
    result.save()
    print("submit work took {} seconds".format(time.time()-start))
    return constr_resp("success")

@app.route("/api/get_all_work")
def get_all_work():
    work_type = request.args.get('work_type')
    query = Results.select().where(Results.result_type==work_type)
    results = []
    for x in query:
        results.append([x.image_id,x.id,x.result])
    return json.dumps({"result":json.dumps(results)})

@app.route("/api/download_image")
def download_image():
    imgid = request.args.get('image_id')
    filename = Image.select().where(Image.id==imgid).get().filename
    print("filename {}".format(filename))
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), mimetype='image/png')

@app.route("/api/get_matching_images",methods=['POST'])
def get_matching_images():
    with open(model_path, 'rb') as f:
            knn_clf = pickle.load(f)
    file = request.files['file']
    file.save("facerec_img.png")
    X_img = face_recognition.load_image_file("facerec_img.png")
    X_face_locations = face_recognition.face_locations(X_img)
    if len(X_face_locations) == 0:
        return []
    faces_encodings = face_recognition.face_encodings(X_img, known_face_locations=X_face_locations)

    closest_distances = knn_clf.kneighbors(faces_encodings, n_neighbors=1)
    are_matches = [closest_distances[0][i][0] <= distance_threshold for i in range(len(X_face_locations))]
    print(json.dumps([(pred, loc) if rec else ("unknown", loc) for pred, loc, rec in zip(knn_clf.predict(faces_encodings), X_face_locations, are_matches)]))
    print([(pred, loc) if rec else ("unknown", loc) for pred, loc, rec in zip(knn_clf.predict(faces_encodings), X_face_locations, are_matches)])
    return json.dumps({"result":[(pred, loc) if rec else ("unknown", loc) for pred, loc, rec in zip(knn_clf.predict(faces_encodings), X_face_locations, are_matches)]})

@app.route("/")
def main():
    return render_template("index.jinja")

@app.route("/upload")
def upload_frontend():
    return render_template("upload.html")

@app.route("/get_matching_images",methods=['POST'])
def frontend_matching_images():
    with open(model_path, 'rb') as f:
            knn_clf = pickle.load(f)
    file = request.files['file']
    file.save("facerec_img.png")
    X_img = face_recognition.load_image_file("facerec_img.png")
    X_face_locations = face_recognition.face_locations(X_img)
    if len(X_face_locations) == 0:
        return []
    faces_encodings = face_recognition.face_encodings(X_img, known_face_locations=X_face_locations)

    closest_distances = knn_clf.kneighbors(faces_encodings, n_neighbors=1)
    are_matches = [closest_distances[0][i][0] <= distance_threshold for i in range(len(X_face_locations))]
    results = [(pred, loc) if rec else ("unknown", loc) for pred, loc, rec in zip(knn_clf.predict(faces_encodings), X_face_locations, are_matches)]
    print(results)
    return render_template("result.html",images=[results[0][0]])

if __name__ == "__main__":
    mysql_db.connect()
    mysql_db.create_tables([Image,Results,ResultStatus])
    mysql_db.close()
    app.run(debug=True)