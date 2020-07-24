from flask import Flask
from flask import request, make_response
from flask import send_file, render_template, redirect
import hashlib
from werkzeug.utils import secure_filename
import time
import os
import json
import math
from sklearn import neighbors
import os.path
import pickle
import face_recognition
import numpy as np
import requests
import argparse
import urllib
from heartbeat_db import HeartbeatDB
import sys
import peewee
import read_config
from threading import Thread
from celery import Celery

heartbeat_config = read_config.HeartbeatConfig()
heartbeat_config.setup()


heartbeat_db = HeartbeatDB()

mysql_db = heartbeat_db.init_db(
    heartbeat_config.config["db_type"],
    heartbeat_config.config["db_auth"],
    heartbeat_config.config["object_storage_type"],
    heartbeat_config.config["object_storage_auth"],
)


UPLOAD_FOLDER = "./uploaded_pics/"
ALLOWED_EXTENSIONS = set(["png", "jpg", "jpeg", "gif"])

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

model_path = "./trained_knn_model.clf"
distance_threshold = 0.5
near_images_to_show = 5


app.config['CELERY_BROKER_URL'] = 'amqp://heartbeat-rabbit:5672/0'

#celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery = Celery(app.name, broker=heartbeat_config.config["celery_broker_url"])
celery.conf.update(app.config)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def constr_resp(status, reason="healthy"):
    return json.dumps({"status": status, "reason": reason})


@app.before_request
def _db_connect():
    if heartbeat_config.config["db_type"] == "mysql":
        mysql_db.connect()


@app.teardown_request
def _db_close(exc):
    if heartbeat_config.config["db_type"] == "mysql":
        if not mysql_db.is_closed():
            mysql_db.close()


@app.route("/api/add_image", methods=["POST"])
def add_image():
    print("Started add_image API call")
    try:
        img_url = request.form.get("img_url")
        information = request.form.get("img_info")
        origin = request.form.get("origin")
        if type(img_url) == type(None) or type(information) == type(None):
            return constr_resp("error", "No url or Image provided")
        if ".png" in img_url:
            fend = ".png"
        elif ".jpg" in img_url:
            fend = ".jpg"
        else:
            return constr_resp("error", "no correct fileformat")
        time_hash = hashlib.sha256(str(time.time()).encode()).hexdigest()
        new_filename = str(time_hash) + fend
        print("Downloading Image {}...".format(img_url))
        s = time.time()
        urllib.request.urlretrieve(img_url, os.path.join(UPLOAD_FOLDER, new_filename))
        print("Downloading took {} seconds".format(str(time.time()-s)))
        information = json.loads(information)
        information = json.dumps(information)
        print("Uploading to DB and OS...")
        s = time.time()
        heartbeat_db.upload_file(new_filename, origin, information)
        print("Uploading to DB took {} seconds".format(str(time.time()-s)))
        return constr_resp("success")
    except peewee.InterfaceError as e:
        print("PeeWee Interface broken!")
        mysql_db = heartbeat_db.init_db(
            heartbeat_config.config["db_type"],
            heartbeat_config.config["db_auth"],
            heartbeat_config.config["object_storage_type"],
            heartbeat_config.config["object_storage_auth"],
        )
        print(e)
        return constr_resp(
            "database error", "if this error keeps occuring contact admin"
        )
    except Exception as e:
        print(e)
        return constr_resp(
            "error", "unknown error, maybe not all query parameters were specified?"
        )


@app.route("/api/add_image_file", methods=["POST"])
def add_image_file():
    try:
        information = request.form.get("img_info")
        origin = request.form.get("origin")
        time_hash = hashlib.sha256(str(time.time()).encode()).hexdigest()
        new_filename = str(time_hash) + ".png"
        file = request.files["file"]
        file.save(os.path.join(UPLOAD_FOLDER, new_filename))
        information = json.loads(information)
        information = json.dumps(information)
        heartbeat_db.upload_file(new_filename, origin, information)
        return constr_resp("success")
    except peewee.InterfaceError as e:
        print("PeeWee Interface broken!")
        mysql_db = heartbeat_db.init_db(
            heartbeat_config.config["db_type"],
            heartbeat_config.config["db_auth"],
            heartbeat_config.config["object_storage_type"],
            heartbeat_config.config["object_storage_auth"],
        )
        print(e)
        return constr_resp(
            "database error", "if this error keeps occuring contact admin"
        )
    except Exception as e:
        print(e)
        return constr_resp(
            "error", "unknown error, maybe not all query parameters were specified?"
        )

@app.route("/api/request_work", methods=["GET"])
def request_work():
    work_type = request.args.get("work_type")
    results = heartbeat_db.request_work(work_type)
    if len(results) > 0:
        return constr_resp(str(results[0]))
    else:
        return constr_resp("error", "empty")


@app.route("/api/submit_work", methods=["POST"])
def submit_work():
    start = time.time()
    work_type = request.form.get("work_type")
    img_id = request.form.get("image_id")
    resulted = request.form.get("result")
    heartbeat_db.submit_work(work_type, img_id, resulted)
    print("submit work took {} seconds".format(time.time() - start))
    return constr_resp("success")


@app.route("/api/get_all_work")
def get_all_work():
    work_type = request.args.get("work_type")
    results = heartbeat_db.get_all_work(work_type)
    return json.dumps({"result": json.dumps(results)})


@app.route("/api/download_image")
def download_image():
    imgid = request.args.get("image_id")
    resp = heartbeat_db.get_file(imgid)
    if type(resp) == type(None):
        resp = render_template(
            "error.html",
            errormessage="Das Bild scheint nicht mehr vorhanden zu sein. Sorry!",
        )
    return resp


@app.route("/api/get_matching_images", methods=["POST"])
def get_matching_images():
    with open(model_path, "rb") as f:
        knn_clf = pickle.load(f)
    file = request.files["file"]
    file.save("facerec_img.png")
    x_img = face_recognition.load_image_file("facerec_img.png")
    x_face_locations = face_recognition.face_locations(x_img)
    if len(x_face_locations) == 0:
        return []
    faces_encodings = face_recognition.face_encodings(
        x_img, known_face_locations=x_face_locations
    )

    closest_distances = knn_clf.kneighbors(faces_encodings, n_neighbors=1)
    are_matches = [
        closest_distances[0][i][0] <= distance_threshold
        for i in range(len(x_face_locations))
    ]
    print(
        json.dumps(
            [
                (pred, loc) if rec else ("unknown", loc)
                for pred, loc, rec in zip(
                    knn_clf.predict(faces_encodings), x_face_locations, are_matches
                )
            ]
        )
    )
    print(
        [
            (pred, loc) if rec else ("unknown", loc)
            for pred, loc, rec in zip(
                knn_clf.predict(faces_encodings), x_face_locations, are_matches
            )
        ]
    )
    return json.dumps(
        {
            "result": [
                (pred, loc) if rec else ("unknown", loc)
                for pred, loc, rec in zip(
                    knn_clf.predict(faces_encodings), x_face_locations, are_matches
                )
            ]
        }
    )


@app.route("/")
def main():
    return render_template("index.html")


@app.route("/upload")
def upload_frontend():
    return render_template("upload.html")


@app.route("/get_matching_images", methods=["POST"])
def frontend_matching_images():
    heartbeat_db.retrieve_model()
    with open(model_path, "rb") as f:
        knn_clf = pickle.load(f)
    file = request.files["file"]
    file.save(file.filename)
    print(file.filename)
    try:
        X_img = face_recognition.load_image_file(file.filename)
        X_face_locations = face_recognition.face_locations(X_img)
    except TypeError:
        print("TypeError Catched!")
        return render_template(
            "error.html",
            errormessage="Ein Fehler ist aufgetreten, ist eventuell kein Gesicht auf dem Bild oder ist das Bild zu gross?",
        )
    if len(X_face_locations) == 0:
        return render_template(
            "error.html",
            errormessage="Wir konnten kein Gesicht auf deinem Bild finden!",
        )
    faces_encodings = face_recognition.face_encodings(
        X_img, known_face_locations=X_face_locations
    )
    closest_distances = knn_clf.kneighbors(
        faces_encodings, n_neighbors=near_images_to_show
    )
    with open("./trained_knn_list.clf", "rb") as f:
        all_labels = pickle.load(f)
    print(closest_distances[1][0])
    res = []
    for x in range(len(closest_distances[1][0])):
        score = closest_distances[0][0][x]
        label = all_labels[closest_distances[1][0][x]]
        if score <= distance_threshold:
            labels = []
            image = heartbeat_db.get_imgobj_from_id(label)
            origin = image.origin
            labels.append("origin: " + origin)
            other_data = json.loads(image.other_data)
            if type(other_data) != type(None):
                for key in other_data:
                    if len(str(other_data[key])) > 0:
                        labels.append(key + ": " + str(other_data[key]))
            res.append({"id": label, "score": str(score)[:5], "labels": labels})

    print(res)
    os.remove(file.filename)
    return render_template("result.html", images=res)


@app.route("/admin", methods=["GET"])
def admin_panel():
    action = request.args.get("action")
    if type(action) != type(None):
        try:
            if action == "update_knn":
                print("Starting")
                print("Started Thread!")
                X,y = [], []
                counter = 0
                work_type = "face_encodings"
                results = heartbeat_db.get_all_work(work_type)
                all_encodings = results
                for encoding in all_encodings:
                    face_bounding_boxes = json.loads(encoding[2])["encoding"]
                    if len(face_bounding_boxes) > 2:
                        X.append(np.array(face_bounding_boxes))
                        y.append(encoding[0])
                        counter += 1
                print("found {} encodings".format(counter))

                n_neighbors = int(round(math.sqrt(len(X))))

                knn_clf = neighbors.KNeighborsClassifier(
                    n_neighbors=n_neighbors, algorithm="ball_tree", weights="distance"
                )
                knn_clf.fit(X, y)

                with open(model_path, "wb") as f:
                    pickle.dump(knn_clf, f)
                with open("trained_knn_list.clf", "wb") as f:
                    pickle.dump(y, f)
                heartbeat_db.safe_model()
                print(task.ready())
        except peewee.InterfaceError as e:
            print("PeeWee Interface broken!")
            mysql_db = heartbeat_db.init_db(
                heartbeat_config.config["db_type"],
                heartbeat_config.config["db_auth"],
                heartbeat_config.config["object_storage_type"],
                heartbeat_config.config["object_storage_auth"],
            )
            print(e)
        finally:
            return redirect("/admin")
    else:
        return render_template("admin.html")


@app.route("/upload_new", methods=["POST", "GET"])
def upload_via_frontend():
    if "file" not in request.files:
        return render_template("upload_new.html")
    file = request.files["file"]
    if file.filename == "":
        return render_template("upload_new.html")
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        hash_object = hashlib.sha256(str(time.time()).encode())
        hex_dig = hash_object.hexdigest()
        new_filename = str(hex_dig) + "." + filename.split(".")[-1]
        file.save(os.path.join(UPLOAD_FOLDER, new_filename))
        heartbeat_db.upload_file(new_filename)
        return render_template("success.html")
    return render_template("upload_new.html")


if __name__ == "__main__":
    app.run("0.0.0.0", port=5001)#,debug=True)
