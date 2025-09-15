from db import get_connection

# Example test — replace 'your_db_name' with an actual database name in your MySQL
connection = get_connection("zing")

if connection:
    cursor = connection.cursor()
    cursor.execute("SHOW TABLES;")
    for table in cursor.fetchall():
        print(table)
    connection.close()
