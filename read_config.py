import json
import os

def log_msg(msg):
    print("-"*60)
    print(msg)
    print("-"*60)

class HeartbeatConfig(object):
    def __init__(self):
        self.config = {}

    def setup(self):
        conf_present = os.path.isfile("./heartbeat_conf.json")
        if conf_present:
            self.config = json.load(open("./heartbeat_conf.json","r"))
        else:
            log_msg("heartbeat_conf.json not found, reading from env...")
            self.config = self.get_from_env()
            log_msg("Read Successful! Dumping to json...")
            with open("./heartbeat_conf.json","w") as f:
                json.dump(self.config,f)

    def get_from_env(self):
        object_storage_type = os.environ.get("OS_TYPE")
        if object_storage_type == "s3":
            object_storage_auth = {
            "aws_access_key_id":os.environ.get("AWS_ACCESS_KEY"),
            "aws_secret_access_key":os.environ.get("AWS_SECRET_KEY"),
            "region_name":os.environ.get("AWS_REGION"),
            "endpoint_url":os.environ.get("ENDPOINT_URL")
            }
        elif object_storage_type == "openstack":
            object_storage_auth = {
                "authurl":os.environ.get("OS_AUTH_URL"),
                "user":os.environ.get("OS_USERNAME"),
                "key":os.environ.get("OS_PASSWORD"),
                "tenant_name":os.environ.get("OS_TENANT_NAME"),
                "auth_version":'2'
            }
        else:
            log_msg("{} is not a valid Object Storage Option (found in ENV variables).".format(object_storage_type))
            exit()
        db_type = os.environ.get("DB_TYPE")
        if db_type == "mysql":
            db_auth = {
                "host":os.environ.get('DB_HOST'),
                "database":os.environ.get('DB_DATABASE'),
                "user":os.environ.get('DB_USER'),
                "password":os.environ.get('DB_PASSWORD'),
                "port":int(os.environ.get("DB_PORT"))
            }
        else:
            log_msg("{} is not a valid Database Option (found in ENV variables).".format(db_type))
        config = {
            "object_storage_type":object_storage_type,
            "object_storage_auth":object_storage_auth,
            "db_type":db_type,
            "db_auth":database_auth
        }
        return config

