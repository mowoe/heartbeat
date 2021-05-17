## Heartbeat &nbsp;[![Build Status](https://travis-ci.com/mowoe/heartbeat.svg?branch=master)](https://travis-ci.com/mowoe/heartbeat)



Heartbeat is a Face Recognition app, that you can upload Images to find more Images with the same face.

#### This Project *__can__* be used for evil shit, but the main Purpose was to show how easy and dangerous it is to build a mass surveillance service.

[:warning: This Demo](https://heartbeat.mowoe.com) is fed with Images from various social Media Sites, e.g. Instagram. You can upload a picture of yourself or anyone else and Heartbeat will try to find images with the same person on it.

## Play Around
1. Go to [heartbeat.mowoe.com](https://heartbeat.mowoe.com)
2. Click "Start".
3. Upload a Picture of someone, e.g. German chancellor Angela Merkel.
4. Click "Upload".
5. Wait for the results.

<p align="center">
  <img src="https://github.com/mowoe/heartbeat/raw/master/images/use.gif"/>
</p>




## Deployment
Heartbeat needs an MySQL(-compatible) Database to store its faces and images. You need to create a user and a Database, the necessary tables are created by the peewee ORM itself.
### The easiest way to deploy Heartbeat is by using docker:
**You need a MySQL database running**, e.g. on the docker host.
If you create a database 'heartbeat', a user 'heartbeat', with the password 'heartbeat', you can just use the following command to start a heartbeat instance.\
The appropriate SQL code is:
```sql
CREATE DATABASE heartbeat;
CREATE USER 'heartbeat'@'localhost' IDENTIFIED BY 'heartbeat';
GRANT ALL PRIVILEGES ON heartbeat.* TO 'heartbeat'@'localhost';
FLUSH PRIVILEGES;
```
:warning: **Please do not use the default login** shown here under any circumstances! \
Finally you can start the docker container:
```bash
sudo docker run --name heartbeat \
                -p 127.0.0.1:5000:80 \
                -e DB_HOST=172.17.0.1\
                -e DB_PORT=3306 \
                -e DB_PASSWORD=heartbeat \
                -e DB_DATABASE=heartbeat \
                -e DB_USER=heartbeat \
                -e DB_TYPE=mysql \
                -e OS_TYPE=local \
                mowoe/heartbeat:latest
```
**When using any object storage, please be aware, that the bucket _needs_ to be named `heartbeat`.**
You can choose if you would like the uploaded pictures to be saved locallly (in the Docker container), or if you want them to be saved in an AWS S3 Bucket (is way cheaper than normal storage on VPS, as you quickly get into the Terabytes of images). To use Local space use the docker variable ```-e OS_TYPE=local```. To use the AWS S3 Storage change it to ```-e OS_TYPE=s3```. You also need to specify ```-e AWS_ACCESS_KEY=awskey```,```-e AWS_SECRET_KEY=aws_key``` and ```-e AWS_REGION=eu-central-1```(or any other region). Heartbeat supports other Bucket Storage Systems too, this is why you need to specify ```-e endpoint_url=http://s3.eu-central-1.amazonaws.com``` or any other Endpoint to an AWS S3 Storage like interface (like [min.io](https://min.io))

## Creating the Face Recognition Model

As the creation of the model can take very long, it is not done automatically. This means a face recognition request to heartbeat will fail, if you didnt train a model yet. You can train a model by going to https://heartbeat-host/admin. This is not advised for huge amounts of images, as the nginx will timeout. If you have large amounts of data, please use a script, which does the training by itself and then uploads the model to your Data storage. This script is still WIP and not published.

## Flowcharts

### Workers
![Heartbeat worker Phase 1](https://github.com/mowoe/heartbeat/raw/master/images/heartbeat_worker_first_step.png "Logo Title Text 1")

##### Phase 1: The Worker requests an unprocessed Image and gets an id in response

![Heartbeat worker Phase 1](https://github.com/mowoe/heartbeat/raw/master/images/heartbeat_worker_second_step.png "Logo Title Text 1")

##### Phase 2: The Worker downloads the Image from the Server via the requested id.

![Heartbeat worker Phase 1](https://github.com/mowoe/heartbeat/raw/master/images/heartbeat_worker_last_step.png "Logo Title Text 1")

##### Phase 3: The worker processes the image (face recognition) and submits the result (mathematical representation) back to the heartbeat server.

## (API) Usage
### Upload an Image
To upload an Image via the API, you have to supply the URL to the image, direct Upload is currently only via the Frontend supported. You also have to supply an origin of the image, so it can later be traced back. If you have any other information about the image, you can supply them via the ```"img_info"``` Key. This is just a JSON Object with all Infos about the Image, which can also be used later for tracing the Image back.
```http
POST /api/add_image HTTP/1.1
Host: heartbeat.mowoe.com
Content-Type: application/json; charset=utf-8

{
  "img_url": "https://example.com/example.png",
  "img_info": "{'uploaded_date':128370}",
  "origin": "example.com"
}
```
### Request Work
To request Work form the Server you just have to supply a ```"work_type"``` Key, as Heartbeat theoretically also supports other recognition types than just Face Rec
```http
GET /api/request_work?work_type=face_recognition HTTP/1.1
Host: heartbeat.mowoe.com
```
### Submit Work
To submit the requested Work you have to supply the work and the image_id, that was retrieved when requesting work.
```http
POST /api/submit_work HTTP/1.1
Host: heartbeat.mowoe.com
Content-Type: application/json; charset=utf-8

{
  "result": "[representation of the face in a vector]",
  "image_id": "12345678",
  "work_type": "face_recognition"
}
```

