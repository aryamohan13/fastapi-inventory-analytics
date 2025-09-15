import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Get MySQL credentials from .env
MYSQL_HOST = os.getenv("DB_HOST", "127.0.0.1")
MYSQL_USER = os.getenv("DB_USER", "root")
MYSQL_PASSWORD = os.getenv("DB_PASSWORD", "")
MYSQL_PORT = int(os.getenv("DB_PORT", 3306))

def get_connection(db_name: str):
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            port=MYSQL_PORT,
            database=db_name
        )
        return conn
    except Error as e:
        print(f"Error connecting to database '{db_name}': {e}")
        return None
