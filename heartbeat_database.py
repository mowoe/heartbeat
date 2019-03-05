class HeartDB(object):
    def __init__(host,user,password,database):
        self.dbconfig = {
            "database": database,
            "user":user
            "host":host,
            "password":password
        }

    def connect(self)
        self.cnx = mysql.connector.connect(pool_name = "HeartPool",
            pool_size = 8,
            **self.dbconfig)

    def get_work(self,table):
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
        current_connection = self.cnx.get_connection()
        cursor = cnx.cursor()
        query = "INSERT INTO %s (id,status,info) VALUES (%s, %s, %s)"
        cursor.execute(query, (table, imageid, 1, additional_information))
        cursor.close()
        current_connection.close()
        return finished_result