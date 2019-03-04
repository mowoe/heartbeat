# Heartbeat

The "Nachfolger" (new version) of my old Projects "Northern Lights" and "insta_rev", a better approach of an Database to store Images and analyze them, via various computer vision techniques, such as Face Detection.

### Idea
There is an endpoint (endpoint.py) software, where you can submit an image either via an url or via HTTP File upload. The images are saved and submitted into a database (MySQL). Every image gets an ID and is saved in a table along with its states. These states
You can use different techniques to process the images. 

### Setup

1. A MySQL (or mariadb) Database, in future maybe other ones will be supported too.
    1.1 