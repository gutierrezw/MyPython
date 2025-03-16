from pymysql import connect


def create_connection(host=None, user=None, password=None, database=None):
    connection = None
    try:
        connection = connect(
            host=host,
            user=user,
            passwd=password,
            database=database
        )
        print("Connection to MySQL DB successful")
    except connect.Error as e:
        print(f"The error '{e}' occurred")
    return connection


def execute_query(connection, query, data=None):
    cursor = connection.cursor()
    try:
        if data:
            cursor.execute(query, data)
        else:
            cursor.execute(query)
        connection.commit()
        print("Query executed successfully")
    except Error as e:
        print(f"The error '{e}' occurred")


def add_record(connection, table_name, record):
    placeholders = ', '.join(['%s'] * len(record))
    columns = ', '.join(record.keys())
    query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
    data = tuple(record.values())
    execute_query(connection, query, data)


def update_record(connection, table_name, record, condition):
    set_clause = ', '.join([f"{k} = %s" for k in record.keys()])
    query = f"UPDATE {table_name} SET {set_clause} WHERE {condition}"
    data = tuple(record.values())
    execute_query(connection, query, data)


def delete_record(connection, table_name, condition):
    query = f"DELETE FROM {table_name} WHERE {condition}"
    execute_query(connection, query)
