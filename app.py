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
                f"<tr><td>{extension[2]}</td><td>{extension[3]}</td><td>{extension[4]}</td><td>{extension[5]}</td><td>{extension[8]}</td></tr>"
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

            acct_name, acct_url = accounts_data[1], accounts_data[3]
            installed_extensions_data = self.get_installed_extensions(acct_id)
            installed_extensions_html = "".join(
                f"<tr><td>{installed_extension[0]}</td><td>{installed_extension[1]}</td><td>"
                f"{self.get_extension_link(installed_extension)}</td></tr>"
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

        elif '/install' in self.path:
            # Parse the query parameters
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            if not 'account_url' in params:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing account_url.")
                return

            self.handle_installation(params['account_url'][0])  # Pass the first account_url

        elif self.path.startswith('/callback'):
            extension_code = self.path.split('/')[-1].split('?')[0]
            extensions_data = self.get_extension_by_code(extension_code)
            if not extensions_data:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Extension not found.")
                return
            
            self.handle_callback(extension_code)

        elif '/actions' in self.path:
            installation_id = self.path.split('/')[1]  
            extension_installations_data = self.get_extension_installation_by_id(installation_id)
            if not extension_installations_data:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Extension Installation not found.")
                return
            
            extension_installation_pk, acct_id = extension_installations_data[0], extension_installations_data[1]
            accounts_data = self.get_account_by_id(acct_id)
            if not accounts_data:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Account not found.")
                return

            acct_name, acct_url = accounts_data[0], accounts_data[1]
            actions_data = self.get_actions(extension_installation_pk)
            actions_html = "".join(
                f"<tr><td>{actions[0]}</td><td>{actions[1]}</td><td>{actions[2]}</td><td>{actions[3]}</td></tr>"
                for actions in actions_data
            ) or "<tr><td colspan='12'>No extension actions found.</td></tr>"
            self.send_html_response('templates/actions.html', {
                "{{ actions }}": actions_html,
                "{{ acct_id }}": f"{acct_id}",
                "{{ account_name }}": acct_name,
            })

        elif '/action-add' in self.path:
            installation_id = self.path.split('/')[1]  
            extension_installations_data = self.get_extension_installation_by_id(installation_id)
            if not extension_installations_data:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Extension Installation not found.")
                return
            
            self.send_html_response('templates/action-add.html', {"{{ installation_id }}": installation_id})

        elif '/ws-profile/' in self.path:
            installation_id = self.path.split('/')[1]  
            extension_installations_data = self.get_extension_installation_by_id(installation_id)
            if not extension_installations_data:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Extension Installation not found.")
                return
            
            extension_installation_pk = extension_installations_data[0]
            acct_id = extension_installations_data[1]
            extension_code = extension_installations_data[2]
            
            accounts_data = self.get_account_by_id(acct_id)
            if not accounts_data:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Account not found.")
                return

            acct_name, acct_url = accounts_data[0], accounts_data[1]

            ws_profile_data = self.get_ws_profile_by_id(extension_installation_pk)
            if not ws_profile_data:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Web Service Profile not found.")
                return

            profile_name, profile_id = ws_profile_data[0], ws_profile_data[1]

            self.send_html_response('templates/ws-profile.html', {
                "{{ acct_id }}": f"{acct_id}",
                "{{ account_name }}": acct_name,
                "{{ profile_name }}": profile_name,
                "{{ profile_id }}": f"{profile_id}",
                "{{ extension_code }}": extension_code,
                "{{ extension_installation_pk }}": f"{extension_installation_pk}"
            })

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

        elif self.path == '/update_ws_profile':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            parsed_data = urllib.parse.parse_qs(post_data.decode('utf-8'))
            acct_id = parsed_data.get('acct_id', [None])[0]

            self.update_ws_profile(post_data)

            # Construct the Location header with acct_id if it exists
            location = '/accounts/'
            if acct_id:
                location += f'{urllib.parse.quote(acct_id)}'
            
            self.send_response(303)
            self.send_header('Location', location)
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
    
    def generate_random_code(self, length=6):
        characters = 'abcdefghijklmnopqrstuvwxyz0123456789'  # lowercase letters and numbers
        return ''.join(random.choice(characters) for _ in range(length))

    def get_extensions(self):
        return self.execute_db_query('SELECT pk, extension_code, extension_name, description, authorization_url, token_url, client_id, client_secret, scope FROM ct_extensions')

    def get_installed_extensions(self, account_id):
        return self.execute_db_query("""
            SELECT e.extension_name, e.description, wsp.app_key, wsp.app_secret, ei.installation_id
            FROM ct_extension_installations ei
            JOIN ct_extensions e ON ei.extension_pk = e.pk
            JOIN ct_accounts a ON ei.account_id = a.acct_id
            JOIN ct_ws_profiles wsp ON ei.pk = wsp.extension_installation_pk
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
    
    def get_extension_link(self, installed_extension):
        installation_id = installed_extension[4]
        if installed_extension[2] and installed_extension[3]:
            return f'<a href="/{installation_id}/actions/">View Extension Actions</a>'
        else:
            return f'<a href="/{installation_id}/ws-profile/">Update WS Profile</a>'

    def get_extension_by_code(self, extension_code):
        extensions_data = self.execute_db_query('SELECT pk, extension_code, extension_name, description, authorization_url, token_url, client_id, client_secret, scope FROM ct_extensions WHERE extension_code = %s', (extension_code,))
        return extensions_data[0] if extensions_data else None

    def get_extension_installation_by_id(self, installation_id):
        extension_installations_data = self.execute_db_query('SELECT ei.pk, ei.account_id, e.extension_code FROM ct_extension_installations ei JOIN ct_extensions e ON ei.extension_pk = e.pk WHERE installation_id = %s', (installation_id,))
        return extension_installations_data[0] if extension_installations_data else None

    def get_latest_extension_installation(self):
        extension_installations_data = self.execute_db_query('SELECT pk, account_id FROM ct_extension_installations ORDER BY pk DESC LIMIT 1')
        return extension_installations_data[0] if extension_installations_data else None  
    
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
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Database error occurred.")
        finally:
            cursor.close()
            db.close()

    def get_accounts(self):
        return self.execute_db_query('SELECT acct_id, acct_name, acct_friendly_name, acct_url, disabled FROM ct_accounts')

    def get_account_by_id(self, account_id):
        accounts_data = self.execute_db_query('SELECT acct_id, acct_name, acct_friendly_name, acct_url, disabled FROM ct_accounts WHERE acct_id = %s', (account_id,))
        return accounts_data[0] if accounts_data else None

    def get_account_by_url(self, account_url):
        accounts_data = self.execute_db_query('SELECT acct_id, acct_name, acct_friendly_name, acct_url, disabled FROM ct_accounts WHERE acct_url = %s', (account_url,))
        return accounts_data[0] if accounts_data else None
    
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
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Database error occurred.")
        finally:
            cursor.close()
            db.close()
    
    def handle_installation(self, account_url):
        # Extract the extension code from the URL
        # Assuming the code is in the second to last part of the URL
        extension_code = self.path.split('/')[-2]  
        extensions_data = self.get_extension_by_code(extension_code)
        if not extensions_data:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Extension not found.")
            return
        
        extension_pk, authorization_url, client_id, scope = extensions_data[0], extensions_data[4], extensions_data[6], extensions_data[8]
        accounts_data = self.get_account_by_url(account_url)
        if not accounts_data:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Account not found.")
            return
        
        account_id = accounts_data[0]
        db = self.connect_db()
        if not db:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Database connection failed.")
            return
        try:
            cursor = db.cursor()

            installation_id = self.generate_random_code()
            query = """
                INSERT INTO ct_extension_installations (installation_id, extension_pk, account_id)
                VALUES (%s, %s, %s)
            """
            cursor.execute(query, (installation_id, extension_pk, account_id)) 

            # Get the ID of the inserted record
            extension_installation_pk = cursor.lastrowid
            profile_code = self.generate_random_code()
            profile_query = """
                INSERT INTO ct_extension_profiles (profile_name, profile_code, extension_installation_pk)
                VALUES (%s, %s, %s)
            """
            cursor.execute(profile_query, ('Default', profile_code, extension_installation_pk))

            ws_query = """
                INSERT INTO ct_ws_profiles (account_id, profile_name, extension_installation_pk)
                VALUES (%s, %s, %s)
            """
            cursor.execute(ws_query, (account_id, 'Extension_'+extension_code, extension_installation_pk))

            db.commit()
        except mysql.connector.Error as err:
            db.rollback()
            print(f"Database error: {err}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Database error occurred.")
        finally:
            cursor.close()
            db.close()

        auth_url = f"{authorization_url}?client_id={client_id}&scope={scope}&redirect_uri={APP_URL}/callback/{extension_code}"
        self.send_response(302)
        self.send_header('Location', auth_url)
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

        extensions_data = self.get_extension_by_code(extension_code)
        if not extensions_data:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Extension not found.")
            return
 
        token_url, client_id, client_secret = extensions_data[5], extensions_data[6], extensions_data[7]
        token_data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'code': authorization_code[0],
            'redirect_uri': f"{APP_URL}/callback/{extension_code}",
            'grant_type': 'authorization_code'
        }

        response = requests.post(token_url, data=token_data)
        token_response = response.json()
        if not token_response.get("ok"):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(f"Error exchanging authorization code for access token: {token_response.get('error')}".encode())
            return

        access_token = token_response.get('access_token')
        if not access_token:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Access token not found in response.")
            return

        db = self.connect_db()
        if not db:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Database connection failed.")
            return
        try:
            cursor = db.cursor()

            extension_installation_data = self.get_latest_extension_installation()
            if not extension_installation_data:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Extension not found.")
                return
            
            extension_installation_pk, account_id = extension_installation_data[0], extension_installation_data[1]
            cursor.execute(
                "UPDATE ct_extension_installations SET token = %s WHERE pk = %s",
                (access_token, extension_installation_pk)
            )
                
            db.commit()
        except mysql.connector.Error as err:
            db.rollback()
            print(f"Database error: {err}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Database error occurred.")
            return
        finally:
            cursor.close()
            db.close()
    
        acct_ext_url = f"/accounts/{account_id}"
        self.send_response(302)
        self.send_header('Location', acct_ext_url)
        self.end_headers()

    def get_actions(self, extension_installation_pk):
        return self.execute_db_query('SELECT ea.action_name, ea.table_source, ea.event_type, ea.action_code FROM ct_extension_actions ea JOIN ct_extension_installations ei ON ea.extension_installation_pk = ei.pk WHERE ea.extension_installation_pk = %s', (extension_installation_pk,))
    
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
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Database error occurred.")
        finally:
            cursor.close()
            db.close()

    def get_ws_profile_by_id(self, extension_installation_pk):
        ws_profile_data = self.execute_db_query('SELECT wsp.profile_id, wsp.account_id, wsp.profile_name, wsp.app_key, wsp.app_secret, wsp.token_url, wsp.extension_installation_pk FROM ct_ws_profiles wsp JOIN ct_extension_installations ei ON wsp.extension_installation_pk = ei.pk WHERE wsp.extension_installation_pk = %s', (extension_installation_pk,))
        return ws_profile_data[0] if ws_profile_data else None    

    def update_ws_profile(self, data):
        params = urllib.parse.parse_qs(data.decode())
        db = self.connect_db()
        if not db:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Database connection failed.")
            return
        try:
            cursor = db.cursor()
            token_url = params.get('token_url', [None])[0]
            client_id = params.get('app_key', [None])[0]
            client_secret = params.get('app_secret', [None])[0]
            profile_id = params.get('profile_id', [None])[0]
            name = params.get('profile_name', [None])[0]
            extension_code = params.get('extension_code', [None])[0]
            extension_installation_pk = params.get('extension_installation_pk', [None])[0]

            # Validate required parameters
            if not all([token_url, client_id, client_secret, profile_id, name, extension_code]):
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"All parameters are required.")
                return

            query = '''UPDATE ct_ws_profiles 
                    SET app_key = %s, app_secret = %s, token_url = %s 
                    WHERE profile_id = %s'''
            cursor.execute(query, (client_id, client_secret, token_url, profile_id))

            if cursor.rowcount == 0:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Profile ID not found.")
                return

            base_url = f"{urllib.parse.urlparse(token_url).scheme}://{urllib.parse.urlparse(token_url).netloc}/"

            # Get authentication token
            auth_response = requests.post(token_url, data={
                'grant_type': 'client_credentials', 
                'client_id': client_id,
                'client_secret': client_secret
            })

            if auth_response.status_code != 200:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Failed to authenticate.")
                return

            token = auth_response.json().get('access_token')
            if not token:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Access token not found in response.")
                return

            outgoing_url = f"{APP_URL}/{extension_code}/handleAsync"
            specific_api_url = f"{base_url}rest/v2/outgoingWebhooks"

            webhook_data = {
                "Name": name,
                "OutgoingUrls": [outgoing_url]
            }

            # Call the specific POST API with the token
            api_response = requests.post(specific_api_url, json=webhook_data, headers={'Authorization': f'Bearer {token}'})
            
            if api_response.status_code != 201:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Failed to call specific API.")
                return

            # Save the API response to the ct_webhooks table
            webhook_response = api_response.json()
            webhook_code = webhook_response.get('ID')
            secret = webhook_response.get('Secret')

            insert_query = '''INSERT INTO ct_webhooks (webhook_code, webhook_name, secret, extension_installation_pk)
                            VALUES (%s, %s, %s, %s)'''
            
            cursor.execute(insert_query, (webhook_code, name, secret, extension_installation_pk))

            webhook_id = cursor.lastrowid
            insert_url_query = '''INSERT INTO ct_webhook_urls (url, webhook_id)
                                VALUES (%s, %s)'''
            
            cursor.execute(insert_url_query, (outgoing_url, webhook_id))
            db.commit()
        except mysql.connector.Error as err:
            db.rollback()
            print(f"Database error: {err}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Database error occurred.")
        except requests.RequestException as err:
            print(f"API request error: {err}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"API request error occurred.")
        finally:
            cursor.close()
            db.close()
        
if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
        print(f"Serving on port {PORT}")
        httpd.serve_forever()
