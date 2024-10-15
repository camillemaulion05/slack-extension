import os
import http.server
import socketserver
import urllib.parse
import mysql.connector
import requests
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

        if self.path.startswith('/assets'):
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            services_data = self.get_services()
            services_html = ""

            if services_data:
                for service in services_data:
                    if service[2] == 1:
                        services_html += f"<tr><td>{service[1]}</td><td>Extension is already installed. <a href='/extension_actions/{service[0]}'>View Actions</a></td></tr>"
                    else:
                        services_html += f"<tr><td>{service[1]}</td><td><a href='/login/{service[0]}'>Install</a></td></tr>"
            else:
                services_html = "<tr><td colspan='2'>No extensions found.</td></tr>"

            try:
                with open('templates/index.html', 'r') as file:
                    template = file.read()
                    response_html = template.replace("{{ services }}", services_html)
                    self.wfile.write(response_html.encode())
            except FileNotFoundError:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Error: Template file not found.")
                return

        elif self.path.startswith('/extension_actions'):
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

        elif self.path.startswith('/create_action'):
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

        elif self.path.startswith('/create_extension'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            try:
                with open('templates/create_extension.html', 'r') as file:
                    self.wfile.write(file.read().encode())
            except FileNotFoundError:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Error: Template file not found.")
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
        if self.path == '/submit_action':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            self.submit_action(post_data)
            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()

        elif self.path == '/submit_extension':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            self.submit_extension(post_data)
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

    def get_services(self):
        db = self.connect_db()
        if not db:
            return []
        try:
            cursor = db.cursor()
            cursor.execute('SELECT pk, extension_name, is_installed FROM ct_extensions')
            services = cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"Database error: {err}")
            return []
        finally:
            cursor.close()
            db.close()
        return services

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

    def submit_extension(self, data):
        params = urllib.parse.parse_qs(data.decode())
        extension_name = params.get('extension_name')[0]
        extension_icon = params.get('extension_icon', [None])[0]
        description = params.get('description', [None])[0]
        authorization_url = params.get('authorization_url')[0]
        token_url = params.get('token_url')[0]
        client_id = params.get('client_id')[0]
        client_secret = params.get('client_secret')[0]
        scope = params.get('scope', [None])[0]

        db = self.connect_db()
        if not db:
            return
        try:
            cursor = db.cursor()
            cursor.execute('''INSERT INTO ct_extensions (extension_name, extension_icon, description,
                              authorization_url, token_url, client_id, client_secret, scope)
                              VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
                           (extension_name, extension_icon, description, 
                            authorization_url, token_url, client_id, client_secret, scope))  
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
