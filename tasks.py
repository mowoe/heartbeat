from celery import Celery
import heartbeat_db
import face_recognition
from heartbeat_db import HeartbeatDB
import pickle
import read_config
import json

heartbeat_config = read_config.HeartbeatConfig()
heartbeat_config.setup()


heartbeat_db = HeartbeatDB()

mysql_db = heartbeat_db.init_db(
    heartbeat_config.config["db_type"],
    heartbeat_config.config["db_auth"],
    heartbeat_config.config["object_storage_type"],
    heartbeat_config.config["object_storage_auth"],
)

model_path = "./trained_knn_model.clf"

celery = Celery('tasks', broker=heartbeat_config.config["celery_broker_url"], backend=heartbeat_config.config["celery_broker_url"])

@celery.task
def find_faces(image_id):
    print("Starting FaceFinder Thread.")
    results = heartbeat_db.request_work("face_encodings")
    filename = heartbeat_db.get_file(image_id)
    image = face_recognition.load_image_file(filename)
    face_locations = face_recognition.face_encodings(image)
    for location in face_locations:
        face_encoding = {"encoding": list(location)}
        heartbeat_db.submit_work("face_encodings", str(image_id), json.dumps(face_encoding))              
    else:
        face_encoding = {"encoding": []} 
        heartbeat_db.submit_work("face_encodings", str(image_id), json.dumps(face_encoding)) 
    print("I found {} Faced in image with id {}".format(len(face_locations),image_id))
            

@celery.task
def matching_faces(id):
    d = heartbeat_db.retrieve_model()
    if d:
        return 0, "There doesnt seem to exist a trained model, not locally nor in the file storage. Please train a model first before using heartbeat by visiting /admin."
    with open(model_path, "rb") as f:
        knn_clf = pickle.load(f)
    filename = heartbeat_db.get_file(id)
    print(filename)
    try:
        X_img = face_recognition.load_image_file(filename)
        X_face_locations = face_recognition.face_locations(X_img)
    except TypeError:
        print("TypeError Caught!")
        return 0, "Ein Fehler ist aufgetreten, ist eventuell kein Gesicht auf dem Bild oder ist das Bild zu gross?"
    if len(X_face_locations) == 0:
        return 0, "Wir konnten kein Gesicht auf deinem Bild finden!"
    faces_encodings = face_recognition.face_encodings(
        X_img, known_face_locations=X_face_locations
    )
    closest_distances = knn_clf.kneighbors(
        faces_encodings, n_neighbors=near_images_to_show
    )
    with open("./trained_knn_list.clf", "rb") as f:
        all_labels = pickle.load(f)

    print("These are the IDs of found images:")
    print(closest_distances[1][0])
    print("These are the scores of the images found:")
    print(closest_distances[0][0])
    labels = [all_labels[i] for i in closest_distances[1][0]]
    print("Real Labels:\n{}".format(labels))
    res = []
    for x in range(len(closest_distances[1][0])):
        score = closest_distances[0][0][x]
        label = all_labels[closest_distances[1][0][x]]
        if score <= distance_threshold:
            labels = []
            try:
                image = heartbeat_db.get_imgobj_from_id(label)
                origin = image.origin
                labels.append("origin: " + origin)
                print(image.other_data)
                other_data = json.loads(image.other_data)
                print(image.other_data, type(image.other_data))
                if type(other_data) != type(None):
                    for key in other_data:
                        print(key, other_data)
                        if len(str(other_data[key])) > 0:
                            labels.append(key + ": " + str(other_data[key]))
                res.append({"id": label, "score": str(
                    score)[:5], "labels": labels})
            except KeyError as e:
                print(e)
                return 1, "Images which are existent in the database, dont seem to be existent in the file storage."

    print(res)
    os.remove(filename)
    
    
