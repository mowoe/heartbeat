import hashlib
import json
import math
import os
import os.path
import pickle
import time
import traceback
import urllib

import face_recognition
import flask_monitoringdashboard as dashboard
import numpy as np
import peewee
from flask import (Flask, g, redirect, render_template, request, send_file,
                   send_from_directory)
from sklearn import neighbors

import read_config
from distribute_work import facerec
from heartbeat_db import HeartbeatDB

heartbeat_config = read_config.HeartbeatConfig()
heartbeat_config.setup()

# test
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

MODEL_PATH = "./trained_knn_model.clf"
DISTANCE_THRESHOLD = 0.6
NEAR_IMAGES_TO_SHOW = 5


try:
    os.mkdir(UPLOAD_FOLDER)
except OSError:
    print(f"Creation of the directory {UPLOAD_FOLDER} failed")
else:
    print(f"Successfully created the directory {UPLOAD_FOLDER}")


def allowed_file(filename):
    return "." in filename and filename.rsplit(
        ".", 1)[1].lower() in ALLOWED_EXTENSIONS


def constr_resp(status, reason="healthy"):
    return {"status": status, "reason": reason}


def constr_resp_html(status, reason="healthy"):
    return render_template("constrresp.html", reason=reason, result=status)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.before_request
def _db_connect():
    g.start = time.time()
    if heartbeat_config.config["db_type"] == "mysql":
        mysql_db.connect()


@app.teardown_request
def _db_close(exc):
    #diff = time.time() - g.start
    #print("This request took {} seconds".format(diff))
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
        if isinstance(img_url, type(None)) or isinstance(
                information, type(None)):
            return constr_resp("error", "No url or Image provided")
        if ".png" in img_url:
            fend = ".png"
        elif ".jpg" in img_url:
            fend = ".jpg"
        else:
            return constr_resp("error", "no correct fileformat")
        time_hash = hashlib.sha256(str(time.time()).encode()).hexdigest()
        new_filename = str(time_hash) + fend
        print(f"Downloading Image {img_url}...")
        start_time = time.time()
        urllib.request.urlretrieve(
            img_url, os.path.join(UPLOAD_FOLDER, new_filename))
        print(f"Downloading took {str(time.time() - start_time)} seconds")
        print(information)
        information = json.loads(information)
        print(information)
        print("Uploading to DB and OS...")
        start_time = time.time()
        res = heartbeat_db.upload_file(filename=new_filename, origin=origin, other_data=information)
        print(f"Uploading to DB took {str(time.time() - start_time)} seconds")
        return constr_resp(res['status'], res['message'])
    except peewee.InterfaceError as error:
        print("PeeWee Interface broken!")
        mysql_db = heartbeat_db.init_db(
            heartbeat_config.config["db_type"],
            heartbeat_config.config["db_auth"],
            heartbeat_config.config["object_storage_type"],
            heartbeat_config.config["object_storage_auth"],
        )
        print(error)
        return constr_resp(
            "database error", "if this error keeps occuring contact admin"
        )
    except Exception as error:
        print(error)
        print(traceback.format_exc())
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
        print(information)
        information = json.loads(information)
        res = heartbeat_db.upload_file(filename=new_filename, origin=origin, other_data=information)
        if res["status"] == "success":
            url = "{}/api/download_image?image_id={}".format(
                heartbeat_config.config["hostname"], res["id"])
            facerec.delay(url)
        return constr_resp(res["status"], res["message"])
    except peewee.InterfaceError as error:
        print("PeeWee Interface broken!")
        mysql_db = heartbeat_db.init_db(
            heartbeat_config.config["db_type"],
            heartbeat_config.config["db_auth"],
            heartbeat_config.config["object_storage_type"],
            heartbeat_config.config["object_storage_auth"],
        )
        print(error)
        return constr_resp(
            "database error", "if this error keeps occuring contact admin"
        )
    except Exception as error:
        print(traceback.format_exc())
        return constr_resp(
            "error", "unknown error, maybe not all query parameters were specified?"
        )


@app.route("/api/submit_work", methods=["POST"])
def submit_work():
    start = time.time()
    work_type = request.form.get("work_type")
    img_id = request.form.get("image_id")
    resulted = request.form.get("result")
    heartbeat_db.submit_work(work_type, img_id, resulted)
    print(f"Saving the submitted work took {time.time() - start} seconds")
    return constr_resp("success")


@app.route("/api/get_all_work")
def get_all_work():
    work_type = request.args.get("work_type")
    results = heartbeat_db.get_all_work(work_type)
    return {"result": json.dumps(results)}


@app.route("/api/download_image")
def download_image():
    imgid = request.args.get("image_id")
    filename = heartbeat_db.get_file(imgid)
    resp = send_file(os.path.join("./", filename), mimetype="image/png")
    os.remove(os.path.join("./", filename))
    if isinstance(resp, type(None)):
        resp = render_template(
            "error.html",
            errormessage="Das Bild scheint nicht mehr vorhanden zu sein. Sorry!",
        )
        return resp, 404
    return resp, 200


@app.route("/api/get_matching_images", methods=["POST"])
def get_matching_images():
    with open(MODEL_PATH, "rb") as opened_file:
        knn_clf = pickle.load(opened_file)
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
        closest_distances[0][i][0] <= DISTANCE_THRESHOLD
        for i in range(len(x_face_locations))
    ]
    print(
        json.dumps(
            [
                (pred, loc) if rec else ("unknown", loc)
                for pred, loc, rec in zip(
                    knn_clf.predict(
                        faces_encodings), x_face_locations, are_matches
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
    return {
        "result": [
            (pred, loc) if rec else ("unknown", loc)
            for pred, loc, rec in zip(
                knn_clf.predict(
                    faces_encodings), x_face_locations, are_matches
            )
        ]
    }


@app.route("/")
def main():
    return render_template("index.html")


@app.route("/upload")
def upload_frontend():
    return render_template("upload.html")


@app.route("/get_matching_images", methods=["POST"])
def frontend_matching_images():
    model_not_present = heartbeat_db.retrieve_model()
    if model_not_present:
        return render_template(
            "error.html",
            errormessage="There doesnt seem to exist a trained model, not locally nor in the \
            file storage. Please train a model first before using heartbeat by visiting /admin."
        )
    with open(MODEL_PATH, "rb") as opened_file:
        knn_clf = pickle.load(opened_file)
    file = request.files["file"]
    file.save(file.filename)
    print(file.filename)
    try:
        x_img = face_recognition.load_image_file(file.filename)
        x_face_locations = face_recognition.face_locations(x_img)
    except TypeError:
        print("TypeError Catched!")
        return render_template(
            "error.html",
            errormessage="Ein Fehler ist aufgetreten, ist eventuell kein Gesicht auf dem Bild \
                oder  ist das Bild zu gross?",
        )
    if len(x_face_locations) == 0:
        return render_template(
            "error.html",
            errormessage="Wir konnten kein Gesicht auf deinem Bild finden!",
        )
    faces_encodings = face_recognition.face_encodings(
        x_img, known_face_locations=x_face_locations
    )
    closest_distances = knn_clf.kneighbors(
        faces_encodings, n_neighbors=NEAR_IMAGES_TO_SHOW
    )
    with open("./trained_knn_list.clf", "rb") as opened_file:
        all_labels = pickle.load(opened_file)

    print("These are the IDs of found images:")
    print(closest_distances[1][0])
    print("These are the scores of the images found:")
    print(closest_distances[0][0])
    labels = [all_labels[i] for i in closest_distances[1][0]]
    print(f"Real Labels:\n{labels}")
    res = []
    for closest_distance_index in range(len(closest_distances[1][0])):
        score = closest_distances[0][0][closest_distance_index]
        label = all_labels[closest_distances[1][0][closest_distance_index]]
        if score <= DISTANCE_THRESHOLD:
            labels = []
            try:
                image = heartbeat_db.get_imgobj_from_id(label)
                origin = image.origin
                labels.append("origin: " + origin)
                print(image.other_data)
                other_data = json.loads(image.other_data)
                print(image.other_data, type(image.other_data))
                if isinstance(other_data, type(None)):
                    for key in other_data:
                        print(key, other_data)
                        if len(str(other_data[key])) > 0:
                            labels.append(key + ": " + str(other_data[key]))
                res.append({"id": label, "score": str(
                    score)[:5], "labels": labels})
            except KeyError as error:
                print(error)
                errormessage=f"Images which are existent in the database dont seem to be existent \
                     in the file storage. {error}"
                return render_template(
                    "error.html", errormessage = errormessage)

    print(res)
    os.remove(file.filename)
    return render_template("result.html", images=res)


@app.route("/delete", methods=["POST"])
def delete_file():
    imgid = request.args.get("image_id")
    heartbeat_db.get_file(imgid)
    return render_template("success.html")


@app.route("/api/get_stats", methods=["GET"])
def get_stats():
    counts = heartbeat_db.get_stats()
    res = {
        "processed": counts[0],
        "total": counts[1],
        "encodings": counts[2]
    }
    return res


@app.route("/admin", methods=["GET"])
def admin_panel():
    action = request.args.get("action")
    if isinstance(action, type(None)):
        counts = heartbeat_db.get_stats()
        not_operational = heartbeat_db.check_operational()
        return render_template(
            "admin.html", not_operational=not_operational, counts=counts)
    try:
        if action == "update_knn":
            print("Starting")
            print("Started Thread!")
            x_loactions, y_locations = [], []
            counter = 0
            work_type = "face_encodings"
            results = heartbeat_db.get_all_work(work_type)
            all_encodings = results
            for encoding in all_encodings:
                face_bounding_boxes = json.loads(encoding[2])["encoding"]
                if len(face_bounding_boxes) > 2:
                    x_loactions.append(np.array(face_bounding_boxes))
                    y_locations.append(encoding[0])
                    counter += 1
            print(f"found {counter} encodings")

            n_neighbors = int(round(math.sqrt(len(x_loactions))))

            knn_clf = neighbors.KNeighborsClassifier(
                n_neighbors=n_neighbors, algorithm="ball_tree", weights="distance"
            )
            knn_clf.fit(x_loactions, y_locations)

            with open(MODEL_PATH, "wb") as opened_file:
                pickle.dump(knn_clf, opened_file)
            with open("trained_knn_list.clf", "wb") as opened_file:
                pickle.dump(y_locations, opened_file)
            heartbeat_db.safe_model()
        if action == "delete_empty":
            print("Deleting all images with no faces detected on.")
            heartbeat_db.delete_empty()
    except peewee.InterfaceError as error_message:
        print("PeeWee Interface broken!")
        mysql_db = heartbeat_db.init_db(
            heartbeat_config.config["db_type"],
            heartbeat_config.config["db_auth"],
            heartbeat_config.config["object_storage_type"],
            heartbeat_config.config["object_storage_auth"],
        )
        print(error_message)
    finally:
        return redirect("/admin")
        


@app.route("/upload_new", methods=["POST", "GET"])
def upload_via_frontend():
    return render_template("upload_new.html")


if __name__ == "__main__":
    dashboard.config.init_from(file='./dash_cfg.cfg')
    dashboard.bind(app)
    app.run("0.0.0.0", port=5001, debug=True)
