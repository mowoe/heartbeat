from flask import Flask, Response
from flask import request
import json

class EndpointAction(object):
    def __init__(self,action):
        self.action = action

    def __call__(self, *args):
        self.response = self.action(args)
        return self.response

class Server(object):
    def __init__(self,port=9721,bind_address='127.0.0.1'):
        self.port = port
        self.bind_address = bind_address
        self.webapp = Flask(__name__)

    def setup(self):
        self.webapp.add_url_rule('/add_image', "image_add", EndpointAction(self.add_image))

    def constr_resp(self,status,reason="healthy"):
        return json.dumps({'status':status, 'reason':reason})

    def add_image(self,args):
        img_url = request.args.get('img_url')
        information = request.args.get('img_info')
        if type(img_url) == type(None) or type(information) == type(None):
            response = Response(self.constr_resp("error","No url or Image provided"), status=401, headers={})
            return response
        response = Response(self.constr_resp("success"), status=200, headers={})
        return response

    def listen(self):
        self.webapp.run(port=self.port,host=self.bind_address)

if __name__ == "__main__":
    serv = Server()
    serv.setup()
    serv.listen()