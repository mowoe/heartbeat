import mysql.connector
from mysql.connector import pooling
import time
import json 
import re

class HeartDB(object):
    def __init__(self):
        self.table_name_validator = re.compile(r'^[0-9a-zA-Z_\$]+$')
        self.dbconfig = json.load(open("db_auth.json","rb"))

    def init_tables(self, tables):
        self.tables = tables

    def connect(self):
        self.cnx = mysql.connector.pooling.MySQLConnectionPool(pool_name = "HeartPool",
            pool_size = 8,
            **self.dbconfig)
        self.cnx.autocommit = True

    def add_image(self,path,origin):
        start = time.time()
        finished_result = 1
        current_connection = self.cnx.get_connection()
        cursor = current_connection.cursor()
        start = time.time()
        query = "INSERT INTO images (filename,origin) VALUES (%s, %s)"
        cursor.execute(query, (path,origin))
        query = "SELECT id FROM images WHERE filename=%s"
        cursor.execute(query, (path,))
        start = time.time()
        for result in cursor:
            imageID = str(result[0])
        
        for additional_table in self.tables:
            if not self.table_name_validator.match(additional_table):
                return "sqli detected"
            query = "INSERT INTO "+additional_table+" (id) VALUES (%s)"
            cursor.execute(query, (str(imageID),))
        start = time.time()
        current_connection.commit()
        current_connection.close()
        return finished_result

    def get_work(self,table):
        if not self.table_name_validator.match(table):
            return "sqli detected"
        if table not in self.tables:
            return "Not a valid table!"
        finished_result = 0
        current_connection = self.cnx.get_connection()
        cursor = current_connection.cursor()
        query = "SELECT id FROM "+table+" WHERE status=0 ORDER BY id ASC LIMIT 1"
        cursor.execute(query)
        for result in cursor:
            finished_result = result[0]
        
        query = "UPDATE "+table+" SET status = %s WHERE id=%s"
        cursor.execute(query, (int(time.time()),finished_result))
        current_connection.commit()
        cursor.close()
        current_connection.close()
        return finished_result

    def submit_work(self, table, imageid, additional_information):
        finished_result = 1
        if not self.table_name_validator.match(table):
            return "sqli detected"
        if table not in self.tables:
            return "Not a valid table!"
        finished_result = 1
        current_connection = self.cnx.get_connection()
        cursor = current_connection.cursor()
        query = "UPDATE "+table+" SET status=%s, info=%s WHERE id = %s;"
        cursor.execute(query, (1, additional_information,imageid))
        current_connection.commit()
        cursor.close()
        current_connection.close()
        return finished_result

    def get_filename_from_id(self,imgid):
        current_connection = self.cnx.get_connection()
        cursor = current_connection.cursor()
        sql = "SELECT filename FROM images WHERE id = %s"
        cursor.execute(sql, (imgid,))
        for res in cursor:
            finished_result = res[0]
        current_connection.commit()
        cursor.close()
        current_connection.close()
        return finished_result