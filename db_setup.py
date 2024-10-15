import os
import mysql.connector
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def setup_database():
    db = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST'),
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASSWORD'),
        database=os.getenv('MYSQL_DB')
    )
    cursor = db.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ct_extensions (
        pk INT AUTO_INCREMENT PRIMARY KEY,
        extension_icon VARCHAR(255),
        extension_name VARCHAR(255) NOT NULL,
        authorization_url VARCHAR(255) NOT NULL,
        token_url VARCHAR(255) NOT NULL,
        scope VARCHAR(255) NOT NULL,
        client_id VARCHAR(255) NOT NULL,
        client_secret VARCHAR(255) NOT NULL,
        description VARCHAR(500),
        incoming_webhook_url VARCHAR(450),
        token TEXT
    )
    ''')

    db.commit()
    cursor.close()
    db.close()

if __name__ == "__main__":
    setup_database()
