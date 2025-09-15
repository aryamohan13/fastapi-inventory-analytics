from db import get_connection

# Change this to the office DB name you want to test
db_name = "your_office_dbname"

conn = get_connection(db_name)
if conn:
    print("✅ Connected successfully")
    conn.close()
else:
    print("❌ Connection failed")
