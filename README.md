:warning: This is under heavy development. Do not use if you dont know exactly what you're doing!

# Heartbeat

The "Nachfolger" (new version) of my old Projects "Northern Lights" and "insta_rev", a better approach of a Database to store Images and analyze them, via various computer vision techniques, such as Face Detection.

----

### Idea
There is an endpoint (endpoint.py) software, where you can submit an image either via an url or via HTTP File upload. The images are saved and submitted into a database (MySQL). Every image gets an ID and is saved in a table along with its states. These states represent the status of the software that has already processed the image. The database is structured like this:
#### 1. Table: Overview (Filename and Meta-Data)
    

| id | Filename | uploaded_date | origin | other_data |
| -------- | -------- | -------- | -------- | -------- |
|KLASF | KSPNVCUEPANCGDZ.jpg     |  1551691084    | public_webcam | blargh
|UDFH8 | IHDIOUCHJKSDHSLA.jpg     |  1551691085    | instagram     | foo

This Table is the basic information table, where information about the image is saved and can be looked up.

#### 2. Table: First Software (in this example: Face Detection)
    

| id | status | info | ... |
| -------- | -------- | -------- | -------- |
| KLASF     | 1     | {['x':200,'y':363,'w':200,'h':200]}     | ... |
| UDFH8     | 0     | -     | ... |

Every table is handled by heartbeat_database. It is initialized with the tables/software, that will be used. The endpoint can be used to read or write to any of these tables.

#### 3. Table: Additional Tables for software

For some Software it can be a good idea to create a second table, where it can save some data, which is only needed or useful for this software. This needs to be supported by the endpoint in the code of the software. 
An Example:


| face_id | face_encoding | id |
| -------- | -------- | -------- |
| KDLKJEHJD     | [blargh]    | KLASF     |


----
### Flow
1. An Image is uploaded via HTTP, the response is the generated ImageID
2. The Image is saved in the database along with its ID, there will be created a row in every of the other tables with status=0
3. A Software (again, for example Face Detection) requests new work.
4. The endpoint chooses an image with the earliest upload date from the table belonging to the requesting software where "status = 0" and answers with its id. At the same time the status gets updated to the current timestamp. Thsi prevents another worker requesting this image, but it has also a "timeout capability", the software can check if the work is taking to long and can then free the image for work.
5. The software has to get the image now via another endpoint, supplying the ImageID
6. The software processes the Image (detects faces)
7. The software now uploads the work, again supplying the ImageID.
8. The endpoint updates the table with the uploaded data.

----


### Setup

1. A MySQL (or mariadb) Database, in future maybe other ones will be supported too. **ALL** columns except id and Filename (no matter in which table) have to have a standard value, for example NULL.
2. The first Table has to be created with the four mandatory columns (id, Filename, uploaded_date, origin). 
3. After that, you can create as much tables as you want, one for each softeare that will be processing the images

### Docker Container Build

For an easier build, there is a docker Image, which you have to build by yourself. A Dockerfile is located in this folder. Steps to build:

1. Create a db_auth.json file with the credentials to a mysql database, under the scheme of db_auth_sample.sjon
2. Build it!
3. Run it!

### A little sitenote:

This can be used for very evil stuff, but it was meant to show how easy it is to build a mass surveillance system.

Mass surveillance is very very very bad! (Just to make that clear)