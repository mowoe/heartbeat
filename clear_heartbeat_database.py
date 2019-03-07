# This script clears the database and deletes all saved files.
import os
from os import listdir
from os.path import isfile, join
import mysql.connector
import json
from mysql.connector import pooling

tables_to_clear = ["images","face_recognition"]

mypath = "./uploaded_pics/"

onlyfiles = [f for f in listdir(mypath) if isfile(join(mypath, f))]

for fil in onlyfiles:
    if "jpg" in fil or "png" in fil or "jpeg" in fil:
        os.remove(mypath+fil)
    else:
        print("{} no image!".format(fil))

print("Deleted all Files! Clearing Database...")

dbconfig = json.load(open("db_auth.json","rb"))

cnx = mysql.connector.pooling.MySQLConnectionPool(pool_name = "HeartPool",
            pool_size = 4,
            **dbconfig)

for table in tables_to_clear:
    query = "DELETE FROM {} WHERE 1".format(table)
    current_connection = cnx.get_connection()
    cursor = current_connection.cursor()
    cursor.execute(query)
    current_connection.commit()
    cursor.close()
    current_connection.close()

print("Done clearing Tables")