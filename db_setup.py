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

    # Create the ct_extensions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ct_extensions (
        pk INT AUTO_INCREMENT PRIMARY KEY,
        extension_name VARCHAR(255) NOT NULL,
        extension_icon VARCHAR(255),
        description TEXT,
        authorization_url VARCHAR(255) NOT NULL,
        token_url VARCHAR(255) NOT NULL,
        client_id VARCHAR(255) NOT NULL,
        client_secret VARCHAR(255) NOT NULL,
        scope VARCHAR(255),
        token VARCHAR(255),
        incoming_webhook_url VARCHAR(255),
        is_installed BOOLEAN DEFAULT FALSE
    )
    ''')

    # Create the extension_actions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS extension_actions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        app_id INT NOT NULL,
        action_name VARCHAR(255) NOT NULL,
        table_source VARCHAR(255) NOT NULL,
        event_type VARCHAR(255) NOT NULL,
        message TEXT NOT NULL,
        response_field_mapped_to VARCHAR(255),
        FOREIGN KEY (app_id) REFERENCES ct_extensions(pk) ON DELETE CASCADE
    )
    ''')

    db.commit()
    cursor.close()
    db.close()

if __name__ == "__main__":
    setup_database()
