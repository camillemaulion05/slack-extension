import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def setup_database():
    try:
        db = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST'),
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DB')
        )
        
        if db.is_connected():
            cursor = db.cursor()

            # Create the ct_accounts table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS ct_accounts (
                acct_id INT AUTO_INCREMENT PRIMARY KEY,
                acct_name VARCHAR(255) NOT NULL UNIQUE,
                acct_friendly_name VARCHAR(65) NOT NULL UNIQUE,
                acct_url VARCHAR(255) NOT NULL,
                disabled BOOLEAN DEFAULT FALSE
            )
            ''')

            # Create the ct_extensions table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS ct_extensions (
                pk INT AUTO_INCREMENT PRIMARY KEY,
                extension_code VARCHAR(6) NOT NULL,
                extension_name VARCHAR(255) NOT NULL,
                description TEXT,
                authorization_url VARCHAR(255) NOT NULL,
                token_url VARCHAR(255) NOT NULL,
                client_id VARCHAR(255) NOT NULL,
                client_secret VARCHAR(255) NOT NULL,
                scope VARCHAR(255) NOT NULL
            )
            ''')

            # Create the ct_extension_installations table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS ct_extension_installations (
                pk INT AUTO_INCREMENT PRIMARY KEY,     
                installation_id VARCHAR(6) NOT NULL,
                extension_pk INT NOT NULL,
                account_id INT NOT NULL,
                incoming_webhook_url VARCHAR(255) NULL,
                token VARCHAR(255) NULL,
                FOREIGN KEY (extension_pk) REFERENCES ct_extensions(pk) ON DELETE CASCADE,  
                FOREIGN KEY (account_id) REFERENCES ct_accounts(acct_id) ON DELETE CASCADE     
            )
            ''')

            # Create the ct_extension_profiles table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS ct_extension_profiles (
                profile_id INT AUTO_INCREMENT PRIMARY KEY,
                profile_name VARCHAR(255) NOT NULL,
                profile_code VARCHAR(6) NOT NULL,
                extension_installation_pk INT NOT NULL,
                FOREIGN KEY (extension_installation_pk) REFERENCES ct_extension_installations(pk) ON DELETE CASCADE
            )
            ''')

            # Create the ct_ws_profiles table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS ct_ws_profiles (
                profile_id INT AUTO_INCREMENT PRIMARY KEY,
                account_id INT NOT NULL,
                profile_name VARCHAR(255) NULL,
                app_key VARCHAR(255) NULL,
                app_secret VARCHAR(255) NULL,
                extension_installation_pk INT NOT NULL,
                FOREIGN KEY (account_id) REFERENCES ct_accounts(acct_id) ON DELETE CASCADE
                FOREIGN KEY (extension_installation_pk) REFERENCES ct_extension_installations(pk) ON DELETE CASCADE
            )
            ''')

            # Create the ct_extension_actions table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS ct_extension_actions (
                action_id INT AUTO_INCREMENT PRIMARY KEY,
                action_name VARCHAR(255) NOT NULL,
                action_code VARCHAR(6) NOT NULL UNIQUE,
                extension_installation_pk INT NOT NULL,
                profile_id INT NOT NULL,
                table_source VARCHAR(255) NOT NULL,
                event_type VARCHAR(255) NOT NULL,
                message TEXT NOT NULL,
                response_field_mapped_to VARCHAR(255),
                webhook_event_id INT NULL,
                FOREIGN KEY (extension_installation_pk) REFERENCES ct_extension_installations(pk) ON DELETE CASCADE,
                FOREIGN KEY (profile_id) REFERENCES ct_extension_profiles(profile_id) ON DELETE CASCADE
            )
            ''')

            db.commit()
            print("Database setup completed successfully.")

    except Error as e:
        print(f"Error: {e}")

    finally:
        if db.is_connected():
            cursor.close()
            db.close()
            print("Database connection closed.")

if __name__ == "__main__":
    setup_database()