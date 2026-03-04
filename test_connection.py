import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv(override=True)

config = {
    "host": os.getenv("MYSQL_HOST"),
    "port": int(os.getenv("MYSQL_PORT", 3306)),
    "user": os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASSWORD"),
}

try:
    conn = mysql.connector.connect(**config)
    print(f"Connected to MySQL {conn.server_info}")
    print(f"Host: {config['host']}:{config['port']}")

    cursor = conn.cursor()
    cursor.execute("SHOW DATABASES")
    print("\nDatabases:")
    for (db,) in cursor:
        print(f"  - {db}")

    cursor.close()
    conn.close()
    print("\nConnection closed.")
except mysql.connector.Error as e:
    print(f"Connection failed: {e}")
