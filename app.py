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
    def send_html_response(self, template_path, replacements=None):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        try:
            with open(template_path, 'r') as file:
                template = file.read()
                if replacements:
                    for key, value in replacements.items():
                        template = template.replace(key, value)
                self.wfile.write(template.encode())
        except FileNotFoundError:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Error: Template file not found.")

    def do_GET(self):
        print(f"Requested path: {self.path}")

        if self.path == '/':
            self.send_html_response('templates/index.html')

        elif self.path.startswith('/assets'):
            return super().do_GET()

        elif self.path.startswith('/extensions'):
            extensions_data = self.get_extensions()
            extensions_html = "".join(
                f"<tr><td>{extension[0]}</td><td>{extension[1]}</td><td>{extension[2]}</td><td>{extension[3]}</td><td>{extension[4]}</td></tr>"
                for extension in extensions_data
            ) or "<tr><td colspan='12'>No extensions found.</td></tr>"
            self.send_html_response('templates/extensions.html', {"{{ extensions }}": extensions_html})

        elif self.path.startswith('/extension-add'):
            self.send_html_response('templates/extension-add.html')

        elif self.path.startswith('/accounts/'):
            acct_id = self.path.split('/')[-1]
            accounts_data = self.get_account_by_id(acct_id)

            if not accounts_data:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Account not found.")
                return

            acct_name, acct_url = accounts_data[0], accounts_data[1]
            installed_extensions_data = self.get_installed_extensions(acct_id)
            installed_extensions_html = "".join(
                f"<tr><td>{installed_extension[0]}</td><td>{installed_extension[1]}</td><td>{installed_extension[2]}</td></tr>"
                for installed_extension in installed_extensions_data
            ) or "<tr><td colspan='4'>No extensions are installed yet.</td></tr>"

            available_extensions_data = self.get_available_extensions(acct_id)
            available_extensions_html = "".join(
                f"<tr><td>{available_extension[0]}</td><td>{available_extension[1]}</td><td><a href='/{available_extension[2]}/install?account_url={acct_url}'>Install</a></td></tr>"
                for available_extension in available_extensions_data
            ) or "<tr><td colspan='4'>No available extensions.</td></tr>"

            self.send_html_response('templates/account-extensions.html', {
                "{{ account_name }}": acct_name,
                "{{ installed_extensions }}": installed_extensions_html,
                "{{ available_extensions }}": available_extensions_html,
            })

        elif self.path.startswith('/accounts'):
            accounts_data = self.get_accounts()
            accounts_html = "".join(
                f"<tr><td>{acct_name}</td><td>{acct_friendly_name}</td><td>{acct_url}</td><td>{status}</td><td><a href='/accounts/{acct_id}'>View Installed Extensions</a></td></tr>"
                for acct_id, acct_name, acct_friendly_name, acct_url, disabled in accounts_data
                for status in ["Active" if disabled == 0 else "Inactive"]
            ) or "<tr><td colspan='12'>No accounts found.</td></tr>"
            self.send_html_response('templates/accounts.html', {"{{ accounts }}": accounts_html})

        elif self.path.startswith('/account-add'):
            self.send_html_response('templates/account-add.html')

        elif self.path.startswith('/extension_actions/'):
            app_id = self.path.split('/')[-1]
            actions_data = self.get_extension_actions(app_id)
            actions_html = "".join(
                f"<tr><td>{action[1]}</td><td>{action[2]}</td><td>{action[3]}</td><td>{action[4]}</td><td>{action[5]}</td></tr>"
                for action in actions_data
            ) or "<tr><td colspan='5'>No actions found for this extension.</td></tr>"
            self.send_html_response('templates/extension_actions.html', {"{{ app_id }}": app_id, "{{ actions }}": actions_html})

        elif self.path.startswith('/create_action/'):
            app_id = self.path.split('/')[-1]
            self.send_html_response('templates/create_action.html', {"{{ app_id }}": app_id})

        elif '/install' in self.path:
            # Parse the query parameters
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            
            # Check if 'account_url' is in the parameters
            if 'account_url' in params:
                self.handle_installation(params['account_url'][0])  # Pass the first account_url
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing account_url.")

        elif self.path.startswith('/callback'):
            extension_code = self.path.split('/')[-1].split('?')[0]
            self.handle_callback(extension_code)

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
        return self.execute_db_query('SELECT extension_name, description, authorization_url, token_url, scope FROM ct_extensions')

    def get_installed_extensions(self, account_id):
        return self.execute_db_query("""
            SELECT e.extension_name, e.description, e.extension_code
            FROM ct_extension_installations ei
            JOIN ct_extensions e ON ei.extension_pk = e.pk
            JOIN ct_accounts a ON ei.account_id = a.acct_id
            WHERE ei.account_id = %s
        """, (account_id,))

    def get_available_extensions(self, account_id):
        return self.execute_db_query("""
            SELECT e.extension_name, e.description, e.extension_code
            FROM ct_extensions e
            WHERE e.pk NOT IN (
                SELECT extension_pk FROM ct_extension_installations WHERE account_id = %s
            )
        """, (account_id,))

    def execute_db_query(self, query, params=None):
        db = self.connect_db()
        if not db:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Database connection failed.")
            return
        try:
            cursor = db.cursor()
            cursor.execute(query, params or ())
            return cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
            return []
        finally:
            cursor.close()
            db.close()

    def submit_extension(self, data):
        params = urllib.parse.parse_qs(data.decode())
        extension_code = self.generate_random_code()
        db = self.connect_db()
        if not db:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Database connection failed.")
            return
        try:
            cursor = db.cursor()
            cursor.execute('''INSERT INTO ct_extensions (extension_code, extension_name, description,
                              authorization_url, token_url, client_id, client_secret, scope)
                              VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
                           (extension_code, params.get('extension_name')[0], params.get('description', [None])[0],
                            params.get('authorization_url')[0], params.get('token_url')[0],
                            params.get('client_id')[0], params.get('client_secret')[0], params.get('scope')[0]))  
            db.commit()
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
        finally:
            cursor.close()
            db.close()

    def get_accounts(self):
        return self.execute_db_query('SELECT acct_id, acct_name, acct_friendly_name, acct_url, disabled FROM ct_accounts')

    def get_account_by_id(self, account_id):
        accounts_data = self.execute_db_query('SELECT acct_name, acct_url FROM ct_accounts WHERE acct_id = %s', (account_id,))
        return accounts_data[0] if accounts_data else None

    def get_account_by_url(self, account_url):
        accounts_data = self.execute_db_query('SELECT acct_id FROM ct_accounts WHERE acct_url = %s', (account_url,))
        return accounts_data[0] if accounts_data else None
    
    def get_extension_by_code(self, extension_code):
        extensions_data = self.execute_db_query('SELECT * FROM ct_extensions WHERE extension_code = %s', (extension_code,))
        return extensions_data[0] if extensions_data else None
    
    def submit_account(self, data):
        params = urllib.parse.parse_qs(data.decode())
        db = self.connect_db()
        if not db:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Database connection failed.")
            return
        try:
            cursor = db.cursor()
            cursor.execute('''INSERT INTO ct_accounts (acct_name, acct_friendly_name, acct_url, disabled)
                              VALUES (%s, %s, %s, %s)''',
                           (params.get('acct_name')[0], params.get('acct_friendly_name')[0],
                            params.get('acct_url')[0], params.get('disabled', [0])[0]))  
            db.commit()
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
        finally:
            cursor.close()
            db.close()

    def get_extension_actions(self, app_id):
        return self.execute_db_query('SELECT * FROM ct_extension_actions WHERE extension_pk = %s', (app_id,))

    def submit_action(self, data):
        params = urllib.parse.parse_qs(data.decode())
        db = self.connect_db()
        if not db:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Database connection failed.")
            return
        try:
            cursor = db.cursor()
            cursor.execute('''INSERT INTO ct_extension_actions (extension_pk, action_name, action_url, 
                              action_method, action_description, action_payload)
                              VALUES (%s, %s, %s, %s, %s, %s)''',
                           (params.get('extension_pk')[0], params.get('action_name')[0],
                            params.get('action_url')[0], params.get('action_method')[0],
                            params.get('action_description')[0], params.get('action_payload')[0]))
            db.commit()
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
        finally:
            cursor.close()
            db.close()

    def handle_installation(self, account_url):
        # Extract the extension code from the URL
        # Assuming the code is in the second to last part of the URL
        extension_code = self.path.split('/')[-2]  
        extensions_data = self.get_extension_by_code(extension_code)
        if extensions_data:
            extension_pk = extensions_data[0]
        else: 
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Extension not found.")
            return
        
        accounts_data = self.get_account_by_url(account_url)
        if accounts_data:
            account_id = accounts_data[0]
        else: 
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Account not found.")
            return


        installation_id = self.generate_random_code()

        # Insert into the ct_extension_installations table
        db = self.connect_db()
        if not db:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Database connection failed.")
            return

        try:
            cursor = db.cursor()
            query = """
                INSERT INTO ct_extension_installations (installation_id, extension_pk, account_id)
                VALUES (%s, %s, %s)
            """
            cursor.execute(query, (installation_id, extension_pk, account_id)) 

            # Get the ID of the inserted record
            extension_installation_pk = cursor.lastrowid

            # Now insert into ct_extension_profiles
            profile_code = self.generate_random_code()
            profile_query = """
                INSERT INTO ct_extension_profiles (profile_name, profile_code, extension_installation_pk)
                VALUES (%s, %s, %s)
            """
            cursor.execute(profile_query, ('Default', profile_code, extension_installation_pk))

            # Insert into ct_ws_profiles as well
            ws_query = """
                INSERT INTO ct_ws_profiles (account_id, profile_name, extension_installation_pk)
                VALUES (%s, %s, %s)
            """
            cursor.execute(ws_query, (account_id, 'Extension_'+extension_code, extension_installation_pk))

            cursor.execute("SELECT client_id, authorization_url, scope FROM ct_extensions WHERE extension_code = %s", (extension_code,))
            extension = cursor.fetchone()

            db.commit()
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Database error.")
        finally:
            cursor.close()
            db.close()

        if extension:
            client_id = extension[0]
            authorization_url = extension[1]
            scope = extension[2]

            auth_url = f"{authorization_url}?client_id={client_id}&scope={scope}&redirect_uri={APP_URL}/callback/{extension_code}"
            self.send_response(302)
            self.send_header('Location', auth_url)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def handle_callback(self, extension_code):
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
            cursor.execute("SELECT client_id, client_secret, token_url, extension_name FROM ct_extensions WHERE extension_code = %s", (extension_code,))
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
                'redirect_uri': f"{APP_URL}/callback/{extension_code}",
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
                    self.send_response(302)
                    self.send_header('Location', '/extensions')
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
        print(f"Serving on port {PORT}")
        httpd.serve_forever()
