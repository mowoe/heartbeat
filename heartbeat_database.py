import mysql.connector

class HeartDB(object):
    def __init__(host,user,password,database):
        self.dbconfig = {
            "database": database,
            "user":user
            "host":host,
            "password":password
        }

    def init_tables(tables):
        self.tables = tables

    def connect(self):
        self.cnx = mysql.connector.connect(pool_name = "HeartPool",
            pool_size = 8,
            **self.dbconfig)

    def add_image(self,path,origin):
        finished_result = 1
        current_connection = self.cnx.get_connection()
        cursor = cnx.cursor()
        query = "INSERT INTO images (Filename,uploaded_date,origin) VALUES (%s, %s, %s); SELECT id FROM images WHERE Filename=%s"
        cursor.execute(query, (path,time.time(),origin,path))
        for result in cursor:
            imageID = result
        for additional_table in self.tables:
            query = "INSERT INTO %s (id, status,info) VALUES (%s, %s, %s)"
            cursor.execute(query, (additional_table, imageID, "", ""))
        cursor.close()
        current_connection.close()
        return finished_result

    def get_work(self,table):
        if table not in self.tables:
            return "Not a valid table!"
        finished_result = 0
        current_connection = self.cnx.get_connection()
        cursor = cnx.cursor()
        query = "SELECT * FROM %s WHERE status=0 ORDER BY id ASC"
        cursor.execute(query, (table,))
        for result in cursor:
            finished_result = result
        cursor.close()
        current_connection.close()
        return finished_result

    def submit_work(self, table, imageid, additional_information):
        finished_result = 1
        if table not in self.tables:
            return "Not a valid table!"
        finished_result = 1
        current_connection = self.cnx.get_connection()
        cursor = cnx.cursor()
        query = "INSERT INTO %s (id,status,info) VALUES (%s, %s, %s)"
        cursor.execute(query, (table, imageid, 1, additional_information))
        cursor.close()
        current_connection.close()
        return finished_result