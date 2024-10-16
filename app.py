import os
import http.server
import socketserver
import urllib.parse
import mysql.connector
import requests
import random
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Check for required environment variables
required_env_vars = ['MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DB', 'APP_URL', 'PORT']
for var in required_env_vars:
    if os.getenv(var) is None:
        print(f"Error: Environment variable {var} is not set.")
        exit(1)

PORT = int(os.environ.get('PORT', 8000))
APP_URL = os.getenv("APP_URL")

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        print(f"Requested path: {self.path}")

        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open('templates/index.html', 'r') as file:
                self.wfile.write(file.read().encode())

        elif self.path.startswith('/assets'):
            return http.server.SimpleHTTPRequestHandler.do_GET(self)
        
        elif self.path.startswith('/extensions'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            extensions_data = self.get_extensions()
            extensions_html = ""

            if extensions_data:
                for extension in extensions_data:
                    extensions_html += f"<tr><td>{extension[0]}</td><td>{extension[1]}</td><td>{extension[2]}</td><td>{extension[3]}</td><td>{extension[4]}</td><td>{extension[5]}</td><td>{extension[6]}</td></tr>"
            else:
                extensions_html = "<tr><td colspan='12'>No extensions found.</td></tr>"

            try:
                with open('templates/extensions.html', 'r') as file:
                    template = file.read()
                    response_html = template.replace("{{ extensions }}", extensions_html)
                    self.wfile.write(response_html.encode())
            except FileNotFoundError:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Error: Template file not found.")
                return
            
        elif self.path.startswith('/extension-add'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            try:
                with open('templates/extension-add.html', 'r') as file:
                    self.wfile.write(file.read().encode())
            except FileNotFoundError:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Error: Template file not found.")

        elif self.path.startswith('/accounts/'):
            # Extract account ID from the URL
            acct_id = self.path.split('/')[-1]
            accounts_data = self.get_account_by_id(acct_id)
            if accounts_data:
                acct_name = accounts_data[1]
            else: 
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Account not found.")
                return
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            # Fetch installed extensions for the account
            extensions_data = self.get_installed_extensions(acct_id)
            extensions_html = ""
                
            if extensions_data:
                for extension in extensions_data:
                    extensions_html += f"<tr><td>{extension[0]}</td><td>{extension[1]}</td><td>{extension[2]}</td><td>{extension[2]}</td></tr>"
            else:
                extensions_html = "<tr><td colspan='4'>No installed extensions found for this account.</td></tr>"

            try:
                with open('templates/account-extensions.html', 'r') as file:
                    template = file.read()
                    response_html = template.replace("{{ account_name }}", acct_name).replace("{{ extensions }}", extensions_html)
                    self.wfile.write(response_html.encode())
            except FileNotFoundError:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Error: Template file not found.")
                    
        elif self.path.startswith('/accounts'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            accounts_data = self.get_accounts()
            accounts_html = ""

            if accounts_data:
                for account in accounts_data:
                    acct_id, acct_name, acct_friendly_name, disabled = account
                    status = "Active" if disabled == 0 else "Inactive"
                    accounts_html += f"<tr><td>{acct_name}</td><td>{acct_friendly_name}</td><td>{status}</td><td><a href='/accounts/{acct_id}'>View Installed Extensions</a></td></tr>"
            else:
                accounts_html = "<tr><td colspan='12'>No accounts found.</td></tr>"

            try:
                with open('templates/accounts.html', 'r') as file:
                    template = file.read()
                    response_html = template.replace("{{ accounts }}", accounts_html)
                    self.wfile.write(response_html.encode())
            except FileNotFoundError:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Error: Template file not found.")
                return
            
        elif self.path.startswith('/account-add'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            try:
                with open('templates/account-add.html', 'r') as file:
                    self.wfile.write(file.read().encode())
            except FileNotFoundError:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Error: Template file not found.")
        
        elif self.path.startswith('/extension_actions/'):
            app_id = self.path.split('/')[-1]
            print(f"Requested extension actions for app_id: {app_id}")  # Debug log
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()

            actions_data = self.get_extension_actions(app_id)
            print(f"Actions data: {actions_data}")  # Debug log
            actions_html = ""
            
            if actions_data:
                for action in actions_data:
                    actions_html += f"<tr><td>{action[1]}</td><td>{action[2]}</td><td>{action[3]}</td><td>{action[4]}</td><td>{action[5]}</td></tr>"
            else:
                actions_html = "<tr><td colspan='5'>No actions found for this extension.</td></tr>"
            
            with open('templates/extension_actions.html', 'r') as file:
                template = file.read()
                response_html = template.replace("{{ app_id }}", app_id).replace("{{ actions }}", actions_html)
                self.wfile.write(response_html.encode())

        elif self.path.startswith('/create_action/'):
            app_id = self.path.split('/')[-1]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            try:
                with open('templates/create_action.html', 'r') as file:
                    template = file.read()
                    response_html = template.replace("{{ app_id }}", app_id)
                    self.wfile.write(response_html.encode())
            except FileNotFoundError:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Error: Template file not found.")
                return

        
                return

        elif self.path.startswith('/login'):
            app_id = self.path.split('/')[-1]
            self.handle_login(app_id)

        elif self.path.startswith('/callback'):
            app_id = self.path.split('/')[-1].split('?')[0]
            self.handle_callback(app_id)

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/submit_extension':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            self.submit_extension(post_data)
            self.send_response(303)
            self.send_header('Location', '/extensions')
            self.end_headers()

        elif self.path == '/submit_account':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            self.submit_account(post_data)
            self.send_response(303)
            self.send_header('Location', '/accounts')
            self.end_headers()

        elif self.path == '/submit_action':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            self.submit_action(post_data)
            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()

    def connect_db(self):
        try:
            return mysql.connector.connect(
                host=os.getenv('MYSQL_HOST'),
                user=os.getenv('MYSQL_USER'),
                password=os.getenv('MYSQL_PASSWORD'),
                database=os.getenv('MYSQL_DB')
            )
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return None

    def generate_random_code(self, length=6):
        characters = 'abcdefghijklmnopqrstuvwxyz0123456789'  # lowercase letters and numbers
        return ''.join(random.choice(characters) for _ in range(length))

    def get_extensions(self):
        db = self.connect_db()
        if not db:
            return []
        try:
            cursor = db.cursor()
            cursor.execute('SELECT pk, extension_code, extension_name, description, authorization_url, token_url, scope FROM ct_extensions')
            extensions = cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
            return []
        finally:
            cursor.close()
            db.close()
        return extensions

    def submit_extension(self, data):
        params = urllib.parse.parse_qs(data.decode())
        extension_code = self.generate_random_code()
        extension_name = params.get('extension_name')[0]
        description = params.get('description', [None])[0]
        authorization_url = params.get('authorization_url')[0]
        token_url = params.get('token_url')[0]
        client_id = params.get('client_id')[0]
        client_secret = params.get('client_secret')[0]
        scope = params.get('scope')[0]

        db = self.connect_db()
        if not db:
            return
        try:
            cursor = db.cursor()
            cursor.execute('''INSERT INTO ct_extensions (extension_code, extension_name, description,
                              authorization_url, token_url, client_id, client_secret, scope)
                              VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
                           (extension_code, extension_name, description, 
                            authorization_url, token_url, client_id, client_secret, scope))  
            db.commit()
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
        finally:
            cursor.close()
            db.close()

    def get_accounts(self):
        db = self.connect_db()
        if not db:
            return []
        try:
            cursor = db.cursor()
            cursor.execute('SELECT acct_id, acct_name, acct_friendly_name, disabled FROM ct_accounts')
            accounts = cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
            return []
        finally:
            cursor.close()
            db.close()
        return accounts
    
    def get_account_by_id(self, acct_id):
        db = self.connect_db()
        if not db:
            return None
        try:
            cursor = db.cursor()
            cursor.execute("SELECT acct_id, acct_name, acct_friendly_name, disabled FROM ct_accounts WHERE acct_id = %s", (acct_id,))
            return cursor.fetchone()
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
            return None
        finally:
            cursor.close()
            db.close()
    
    def get_installed_extensions(self, account_id):
        db = self.connect_db()
        if not db:
            return []
        try:
            cursor = db.cursor()
            cursor.execute("""
                SELECT e.pk, e.extension_name, e.description
                FROM ct_extensions e 
                JOIN ct_extension_installations ei ON e.pk = ei.extension_pk 
                JOIN ct_accounts a ON a.acct_id = ei.account_id 
                WHERE ei.account_id = %s
            """, (account_id,))
            extensions = cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
            return []
        finally:
            cursor.close()
            db.close()
        return extensions

    def submit_account(self, data):
        params = urllib.parse.parse_qs(data.decode())
        acct_name = params.get('acct_name')[0]
        acct_friendly_name = params.get('acct_friendly_name')[0]

        db = self.connect_db()
        if not db:
            return
        try:
            cursor = db.cursor()
            cursor.execute('''INSERT INTO ct_accounts (acct_name, acct_friendly_name)
                              VALUES (%s, %s)''',
                           (acct_name, acct_friendly_name))  
            db.commit()
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
        finally:
            cursor.close()
            db.close()
    
    def get_extension_actions(self, app_id):
        db = self.connect_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM extension_actions WHERE app_id = %s", (app_id,))
        actions = cursor.fetchall()
        cursor.close()
        db.close()
        return actions

    def submit_action(self, data):
        params = urllib.parse.parse_qs(data.decode())
        action_name = params.get('action_name')[0]
        table_source = params.get('table_source')[0]
        event_type = params.get('event_type')[0]
        message = params.get('message')[0]
        response_field_mapped_to = params.get('response_field_mapped_to')[0]
        app_id = params.get('app_id')[0]

        db = self.connect_db()
        if not db:
            return
        try:
            cursor = db.cursor()
            cursor.execute('''INSERT INTO extension_actions (app_id, action_name, table_source, event_type, message, response_field_mapped_to)
                              VALUES (%s, %s, %s, %s, %s, %s)''',
                           (app_id, action_name, table_source, event_type, message, response_field_mapped_to))  
            db.commit()
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
        finally:
            cursor.close()
            db.close()

    

    def handle_login(self, app_id):
        db = self.connect_db()
        if not db:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Database connection failed.")
            return
        try:
            cursor = db.cursor()
            cursor.execute("SELECT client_id, authorization_url, scope FROM ct_extensions WHERE pk = %s", (app_id,))
            service = cursor.fetchone()
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Database error.")
            return
        finally:
            cursor.close()
            db.close()

        if service:
            client_id = service[0]
            authorization_url = service[1]
            scope = service[2]

            auth_url = f"{authorization_url}?client_id={client_id}&scope={scope}&redirect_uri={APP_URL}/callback/{app_id}"
            self.send_response(302)
            self.send_header('Location', auth_url)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def handle_callback(self, app_id):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        authorization_code = params.get('code')

        if not authorization_code:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing authorization code.")
            return

        db = self.connect_db()
        if not db:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Database connection failed.")
            return
        try:
            cursor = db.cursor()
            cursor.execute("SELECT client_id, client_secret, token_url, extension_name FROM ct_extensions WHERE pk = %s", (app_id,))
            service = cursor.fetchone()
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Database error.")
            return
        finally:
            cursor.close()
            db.close()

        if service:
            client_id = service[0]
            client_secret = service[1]
            token_url = service[2]
            extension_name = service[3]

            token_data = {
                'client_id': client_id,
                'client_secret': client_secret,
                'code': authorization_code[0],
                'redirect_uri': f"{APP_URL}/callback/{app_id}",
                'grant_type': 'authorization_code'
            }

            print("Access Token Request:", token_data)

            response = requests.post(token_url, data=token_data)
            token_response = response.json()

            print("Access Token Response:", token_response)

            if token_response.get("ok"):
                access_token = token_response.get('access_token')

                incoming_webhook_url = None
                if extension_name == "Slack":
                    incoming_webhook_url = token_response.get('incoming_webhook', {}).get('url')

                if access_token:
                    db = self.connect_db()
                    if not db:
                        self.send_response(500)
                        self.end_headers()
                        self.wfile.write(b"Database connection failed.")
                        return
                    try:
                        cursor = db.cursor()
                        if incoming_webhook_url:
                            cursor.execute(
                                "UPDATE ct_extensions SET token = %s, incoming_webhook_url = %s, is_installed = %s WHERE pk = %s",
                                (access_token, incoming_webhook_url, 1, app_id)
                            )
                        else:
                            cursor.execute(
                                "UPDATE ct_extensions SET token = %s, is_installed = %s WHERE pk = %s",
                                (access_token, 1, app_id)
                            )

                        db.commit()
                    except mysql.connector.Error as err:
                        print(f"Database error: {err}")
                        self.send_response(500)
                        self.end_headers()
                        self.wfile.write(b"Database error.")
                        return
                    finally:
                        cursor.close()
                        db.close()

                    self.send_response(302)
                    self.send_header('Location', '/')
                    self.end_headers()
                else:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Access token not found in response.")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(f"Error exchanging authorization code for access token: {token_response.get('error')}".encode())
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
        print(f"Serving at port {PORT}")
        httpd.serve_forever()
