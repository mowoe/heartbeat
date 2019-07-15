## Heartbeat

Heartbeat is a Face Recognition app, that you can upload Images to find more Images with the same face.

#### This Project *__can__* be used for evil shit, but the main Purpose was to show how easy and dangerous it is to build a mass surveillance service.

[:warning: This Demo](https://heartbeat.mowoe.com) is fed with Images from various social Media Sites, e.g. Instagram. You can upload a picture of yourself or anyone else and Heartbeat will try to find images with the same person on it.


## Deployment
The easiest way to deploy Heartbeat is by using docker:
```bash
sudo docker run --name heartbeat \
                -p 80:80 \
                -e DB_HOST=example.com \
                -e DB_PORT=3306 \
                -e DB_DATABASE=heartbeat \
                -e DB_PASSWORD=password\
                -e DB_USER=heartbeat \
                -e db_type=file \
                mowoe/heartbeat:latest
```
You can choose if you would like the uploaded pictures to be saved locallly (in the Docker container), or if you want them to be saved in an AWS S3 Bucket (is way cheaper than normal storage on VPS). To use Local space use the docker variable ```-e db_type=file```. To use the AWS S3 Storage change it to ```-e db_type=s3```. You also need to specify 
