from flask import Flask, Response, request, redirect, url_for
import json
from werkzeug.utils import secure_filename
import os
import time
import hashlib
import heartbeat_database

UPLOAD_FOLDER = './uploaded_pics/'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class EndpointAction(object):
    def __init__(self,action):
        self.action = action

    def __call__(self, *args):
        self.response = self.action(args)
        return self.response

class Server(object):
    def __init__(self, hdb, port=9721,bind_address='127.0.0.1'):
        self.port = port
        self.bind_address = bind_address
        self.webapp = Flask(__name__)
        self.HeartDB = hdb

    def setup(self):
        self.webapp.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
        self.webapp.add_url_rule('/add_image', "image_add", EndpointAction(self.add_image))
        self.webapp.add_url_rule('/add_image_via_file', "file_add", EndpointAction(self.add_file), methods=['POST'])
        self.webapp.add_url_rule('/request_work/<table>', request_work, EndpointAction(self.request_work))

    def constr_resp(self,status,reason="healthy"):
        return json.dumps({'status':status, 'reason':reason})

    def add_file(self,args):
        if 'file' not in request.files:
            return self.constr_resp("error","no file part")
        file = request.files['file']
        if file.filename == '':
            return self.constr_resp("error","no file supplied")
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            hash_object = hashlib.sha256(str(time.time()).encode())
            hex_dig = hash_object.hexdigest()
            new_filename = str(hex_dig) + "." + filename.split(".")[-1]
            file.save(os.path.join(self.webapp.config['UPLOAD_FOLDER'], new_filename))
            return self.constr_resp("success")

    def add_image(self,args):
        img_url = request.args.get('img_url')
        information = request.args.get('img_info')
        if type(img_url) == type(None) or type(information) == type(None):
            response = Response(self.constr_resp("error","No url or Image provided"), status=401, headers={})
            return response
        information = json.loads(information)
            
        response = Response(self.constr_resp("success"), status=200, headers={})
        return response

    def request_work(self,table):
        print("Table: {}".format(table))
        resp_id = self.HeartDB.get_work(table)
        return Response(self.constr_resp(resp_id),status=200)

    def submit_work(self,args):
        pass

    def listen(self):
        self.webapp.run(port=self.port,host=self.bind_address)

class Client(object):
    def __init__(self):
        pass

if __name__ == "__main__":
    hdb = heartbeat_database.HeartDB("host","user","password","db")
    hdb.init_tables(["face_recognition"])
    hdb.connect()
    serv = Server()
    serv.setup()
    serv.listen()