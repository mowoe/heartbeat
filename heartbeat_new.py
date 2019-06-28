from flask import Flask
from flask import request, make_response
from flask import send_file, render_template, redirect
import hashlib
from werkzeug.utils import secure_filename
import time
import os
from peewee import MySQLDatabase, SqliteDatabase
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
import argparse

parser = argparse.ArgumentParser(description='Face recognition Software')
parser.add_argument('--testing', dest='testing', action='store_true',
                    default=False,
                    help='If testing is true (CI)')

args = parser.parse_args()

testing = args.testing

UPLOAD_FOLDER = './uploaded_pics/'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not testing:
    dbconfig = json.load(open("db_auth.json","rb"))
    mysql_db = peewee.MySQLDatabase(**dbconfig)
else:
    mysql_db = SqliteDatabase('my_app.db', pragmas={'journal_mode': 'wal'})

model_path = "./examples/trained_knn_model.clf"
distance_threshold = 0.6
near_images_to_show = 5

class Image(peewee.Model):
    filename = CharField()
    uploaded_date = DateTimeField(default=datetime.datetime.now)
    origin = CharField(default="unknown")
    other_data = CharField(default="null")
    class Meta:
        database = mysql_db

class Results(peewee.Model):
    image_id = CharField()#ForeignKeyField(Image, backref='id')
    result_type = CharField(max_length=7000)
    result = CharField()
    class Meta:
        database = mysql_db

if not testing:
    mysql_db.connect()
    mysql_db.create_tables([Image,Results])
    mysql_db.close()
else:
    mysql_db.create_tables([Image,Results])

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def constr_resp(status,reason="healthy"):
        return json.dumps({'status':status, 'reason':reason})

@app.before_request
def _db_connect():
    if not testing:
        mysql_db.connect()

@app.teardown_request
def _db_close(exc):
    if not testing:
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
    if len(results) > 0:
        return constr_resp(str(results[0]))
    else:
        return constr_resp("error","empty")

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
    return render_template("index.html")

@app.route("/upload")
def upload_frontend():
    return render_template("upload.html")

@app.route("/get_matching_images",methods=['POST'])
def frontend_matching_images():
    with open(model_path, 'rb') as f:
        knn_clf = pickle.load(f)
    file = request.files['file']
    file.save(file.filename)
    print(file.filename)
    X_img = face_recognition.load_image_file(file.filename)
    X_face_locations = face_recognition.face_locations(X_img,model="cnn")
    if len(X_face_locations) == 0:
        return []
    print(1)
    faces_encodings = face_recognition.face_encodings(X_img, known_face_locations=X_face_locations)
    closest_distances = knn_clf.kneighbors(faces_encodings, n_neighbors=near_images_to_show)
    with open("trained_knn_list.clf",'rb') as f:
        all_labels = pickle.load(f)
    print(closest_distances[1][0])
    res = []
    for x in range(len(closest_distances[1][0])):
        score = closest_distances[0][0][x]
        label = all_labels[closest_distances[1][0][x]]
        if score <= distance_threshold:
            res.append({"id":label,"score":str(score)[:5]})
    print(res)
    os.remove(file.filename)
    return render_template("result.html",images=res)

@app.route("/admin",methods=['GET'])
def admin_panel():
    action = request.args.get('action')
    if type(action) != type(None):
        if action == "update_knn":
            X = []
            y = []
            counter = 0
            work_type = 'face_encodings'
            query = Results.select().where(Results.result_type==work_type)
            results = []
            for x in query:
                results.append([x.image_id,x.id,x.result])
            all_encodings = results
            for encoding in all_encodings:
                print(encoding)
                face_bounding_boxes = json.loads(encoding[2])["encoding"]
                if len(face_bounding_boxes) > 2:
                    X.append(np.array(face_bounding_boxes))
                    y.append(encoding[0])
                    counter+=1
            print("found {} encodings".format(counter))

            n_neighbors = int(round(math.sqrt(len(X))))

            knn_clf = neighbors.KNeighborsClassifier(n_neighbors=n_neighbors, algorithm="ball_tree", weights='distance')
            knn_clf.fit(X, y)

            with open(model_path, 'wb') as f:
                pickle.dump(knn_clf, f)
            with open("trained_knn_list.clf",'wb') as f:
                pickle.dump(y,f)
        return redirect("/admin")
    else:
        return render_template("admin.html")

@app.route("/upload_new",methods=['POST','GET'])
def upload_via_frontend():
    if 'file' not in request.files:
        return render_template("upload_new.html")
    file = request.files['file']
    if file.filename == '':
        return render_template("upload_new.html")
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        hash_object = hashlib.sha256(str(time.time()).encode())
        hex_dig = hash_object.hexdigest()
        new_filename = str(hex_dig) + "." + filename.split(".")[-1]
        file.save(os.path.join(UPLOAD_FOLDER, new_filename))
        image = Image(filename=new_filename)
        image.save()
        return render_template("success.html")
    return render_template("upload_new.html")


if __name__ == "__main__":
    app.run(debug=True)