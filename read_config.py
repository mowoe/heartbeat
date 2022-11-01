import json
import os
import sys

def log_msg(msg):
    print("-"*60)
    print(msg)
    print("-"*60)


class HeartbeatConfig:
    def __init__(self):
        self.config = {}

    def setup(self):
        conf_present = os.path.isfile("./heartbeat_conf.json")
        if conf_present:
            with open("./heartbeat_conf.json", "r", encoding="utf-8") as opened_file:
                self.config = json.load(opened_file)
        else:
            log_msg("heartbeat_conf.json not found, reading from env...")
            self.config = self.get_from_env()
            log_msg("Read Successful! Dumping to json...")
            with open("./heartbeat_conf.json", "w", encoding="utf-8") as opened_file:
                json.dump(self.config, opened_file)

    def get_from_env(self):
        object_storage_type = os.environ.get("OS_TYPE")
        if object_storage_type == "s3":
            object_storage_auth = {
                "aws_access_key_id": os.environ.get("AWS_ACCESS_KEY"),
                "aws_secret_access_key": os.environ.get("AWS_SECRET_KEY"),
                "region_name": os.environ.get("AWS_REGION"),
                "endpoint_url": os.environ.get("ENDPOINT_URL")
            }
        elif object_storage_type == "openstack":
            object_storage_auth = {
                "authurl": os.environ.get("OS_AUTH_URL"),
                "user": os.environ.get("OS_USERNAME"),
                "key": os.environ.get("OS_PASSWORD"),
                "tenant_name": os.environ.get("OS_TENANT_NAME"),
                "auth_version": '2'
            }
        elif object_storage_type == "local":
            object_storage_auth = {}
        else:
            log_msg(
                f"{object_storage_type} is not a valid Object Storage Option\
                     (found in ENV variables).")
            sys.exit()
        db_type = os.environ.get("DB_TYPE")
        if db_type == "mysql":
            db_auth = {
                "host": os.environ.get('DB_HOST'),
                "database": os.environ.get('DB_DATABASE'),
                "user": os.environ.get('DB_USER'),
                "password": os.environ.get('DB_PASSWORD'),
                "port": int(os.environ.get("DB_PORT"))
            }
        else:
            log_msg(
                f"{db_type} is not a valid Database Option (found in ENV variables).")
            sys.exit()

        celery_aws_key = os.environ.get('CELERY_AWS_KEY')
        celery_aws_secret = os.environ.get('CELERY_AWS_SECRET')
        celery_queue_name = os.environ.get('CELERY_QUEUE_NAME')
        celery_queue_url = os.environ.get('CELERY_QUEUE_URL')
        celery_aws_type = os.environ.get('CELERY_AWS_TYPE')
        hostname = os.environ.get('HEARTBEAT_HOSTNAME')
        config = {
            "object_storage_type": object_storage_type,
            "object_storage_auth": object_storage_auth,
            "db_type": db_type,
            "db_auth": db_auth,
            "celery_broker_url": os.environ.get("CELERY_BROKER_URL"),
            "celery_aws_key": celery_aws_key,
            "celery_aws_secret": celery_aws_secret,
            "celery_queue_name": celery_queue_name,
            "celery_queue_url": celery_queue_url,
            "celery_aws_type": celery_aws_type,
            "hostname": hostname
        }

        return config
