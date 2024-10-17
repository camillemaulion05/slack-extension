DROP TABLE IF EXISTS extension_db.ct_webhook_urls;
DROP TABLE IF EXISTS extension_db.ct_webhooks;
DROP TABLE IF EXISTS extension_db.ct_extension_actions;
DROP TABLE IF EXISTS extension_db.ct_ws_profiles;
DROP TABLE IF EXISTS extension_db.ct_extension_profiles;
DROP TABLE IF EXISTS extension_db.ct_extension_installations;
DROP TABLE IF EXISTS extension_db.ct_extensions;
DROP TABLE IF EXISTS extension_db.ct_accounts;

CREATE TABLE IF NOT EXISTS extension_db.ct_accounts (
                acct_id INT AUTO_INCREMENT PRIMARY KEY,
                acct_name VARCHAR(255) NOT NULL UNIQUE,
                acct_friendly_name VARCHAR(65) NOT NULL UNIQUE,
                acct_url VARCHAR(255) NOT NULL,
                disabled BOOLEAN DEFAULT FALSE
            );
CREATE TABLE IF NOT EXISTS extension_db.ct_extensions (
                pk INT AUTO_INCREMENT PRIMARY KEY,
                extension_code VARCHAR(6) NOT NULL,
                extension_name VARCHAR(255) NOT NULL,
                description TEXT,
                authorization_url VARCHAR(255) NOT NULL,
                token_url VARCHAR(255) NOT NULL,
                client_id VARCHAR(255) NOT NULL,
                client_secret VARCHAR(255) NOT NULL,
                scope VARCHAR(255) NOT NULL
            );
CREATE TABLE IF NOT EXISTS extension_db.ct_extension_installations (
                pk INT AUTO_INCREMENT PRIMARY KEY,     
                installation_id VARCHAR(6) NOT NULL,
                extension_pk INT NOT NULL,
                account_id INT NOT NULL,
                incoming_webhook_url VARCHAR(255) NULL,
                token VARCHAR(255) NULL,
                FOREIGN KEY (extension_pk) REFERENCES ct_extensions(pk) ON DELETE CASCADE,  
                FOREIGN KEY (account_id) REFERENCES ct_accounts(acct_id) ON DELETE CASCADE     
            );
CREATE TABLE IF NOT EXISTS extension_db.ct_extension_profiles (
                profile_id INT AUTO_INCREMENT PRIMARY KEY,
                profile_name VARCHAR(255) NOT NULL,
                profile_code VARCHAR(6) NOT NULL,
                extension_installation_pk INT NOT NULL,
                FOREIGN KEY (extension_installation_pk) REFERENCES ct_extension_installations(pk) ON DELETE CASCADE
            );
CREATE TABLE IF NOT EXISTS extension_db.ct_ws_profiles (
                profile_id INT AUTO_INCREMENT PRIMARY KEY,
                account_id INT NOT NULL,
                profile_name VARCHAR(255) NULL,
                app_key VARCHAR(255) NULL,
                app_secret VARCHAR(255) NULL,
                token_url VARCHAR(255) NULL,
                extension_installation_pk INT NOT NULL,
                FOREIGN KEY (account_id) REFERENCES ct_accounts(acct_id) ON DELETE CASCADE,
                FOREIGN KEY (extension_installation_pk) REFERENCES ct_extension_installations(pk) ON DELETE CASCADE
            );
CREATE TABLE IF NOT EXISTS extension_db.ct_extension_actions (
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
            );
CREATE TABLE IF NOT EXISTS extension_db.ct_webhooks (
                id INT AUTO_INCREMENT PRIMARY KEY,  
                webhook_code VARCHAR(255) NOT NULL,
                webhook_name VARCHAR(255) NOT NULL,
                secret VARCHAR(255) NOT NULL,
                extension_installation_pk INT NOT NULL,
                FOREIGN KEY (extension_installation_pk) REFERENCES ct_extension_installations(pk) ON DELETE CASCADE
            );
CREATE TABLE IF NOT EXISTS extension_db.ct_webhook_urls (
                webhook_url_pk INT AUTO_INCREMENT PRIMARY KEY,  
                url VARCHAR(255) NOT NULL,                      
                webhook_id INT NOT NULL,                         
                FOREIGN KEY (webhook_id) REFERENCES ct_webhooks(id) ON DELETE CASCADE 
            );