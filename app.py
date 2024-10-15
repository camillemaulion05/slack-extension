import os
import http.server
import socketserver
import urllib.parse
import mysql.connector
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

PORT = int(os.environ.get('PORT', 8000))
APP_URL = os.getenv("APP_URL")

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open('templates/index.html', 'r') as file:
                self.wfile.write(file.read().encode())

        elif self.path.startswith('/services'):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            services_data = self.get_services()
            response_html = "<h1>Available Services</h1><ul>"
            for service in services_data:
                response_html += f"<li>{service[1]} - <a href='/login/{service[0]}'>Install</a></li>"
            response_html += "</ul>"
            self.wfile.write(response_html.encode())

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
        if self.path == '/add_service':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            self.add_service(post_data)
            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()

    def get_services(self):
        db = self.connect_db()
        cursor = db.cursor()
        cursor.execute('SELECT pk, extension_name FROM ct_extensions')
        services = cursor.fetchall()
        cursor.close()
        db.close()
        return services

    def add_service(self, data):
        params = urllib.parse.parse_qs(data.decode())
        print("Received parameters:", params)

        extension_name = params.get('extension_name')
        if not extension_name:
            print("Extension name not provided.")
            return

        extension_icon = params.get('extension_icon', [None])[0]
        extension_name = extension_name[0]
        description = params.get('description', [None])[0]
        authorization_url = params.get('authorization_url', [None])[0]
        token_url = params.get('token_url', [None])[0]
        client_id = params.get('client_id', [None])[0]
        client_secret = params.get('client_secret', [None])[0]
        scope = params.get('scope', [None])[0]

        if not all([client_id, client_secret, authorization_url, token_url]):
            print("Some required fields are missing.")
            return

        db = self.connect_db()
        cursor = db.cursor()
        cursor.execute('''INSERT INTO ct_extensions (extension_name, extension_icon, description,
                       authorization_url, token_url, client_id, client_secret, scope)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
                      (extension_name, extension_icon, description, 
                       authorization_url, token_url, client_id, client_secret, scope))  
        db.commit()
        cursor.close()
        db.close()

    def handle_login(self, app_id):
        db = self.connect_db()
        cursor = db.cursor()
        cursor.execute("SELECT client_id, authorization_url, scope FROM ct_extensions WHERE pk = %s", (app_id,))
        service = cursor.fetchone()
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
        cursor = db.cursor()
        cursor.execute("SELECT client_id, client_secret, token_url, extension_name FROM ct_extensions WHERE pk = %s", (app_id,))
        service = cursor.fetchone()
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
                'code': authorization_code[0],  # Ensure this is the first item in the list
                'redirect_uri': f"{APP_URL}/callback/{app_id}",
                'grant_type': 'authorization_code'  # This can be necessary for some APIs
            }

            print("Access Token Request:", token_data)

            # Post request to Slack to exchange the authorization code for an access token
            response = requests.post(token_url, data=token_data)
            token_response = response.json()

            # Print the entire token response for debugging
            print("Access Token Response:", token_response)

            if token_response.get("ok"):
                access_token = token_response.get('access_token')

                incoming_webhook_url = None
                if extension_name == "Slack":
                    incoming_webhook_url = token_response.get('incoming_webhook', {}).get('url')

                if access_token:
                    db = self.connect_db()
                    cursor = db.cursor()
                    if incoming_webhook_url:
                        cursor.execute(
                            "UPDATE ct_extensions SET token = %s, incoming_webhook_url = %s WHERE pk = %s",
                            (access_token, incoming_webhook_url, app_id)
                        )
                    else:
                        cursor.execute(
                            "UPDATE ct_extensions SET token = %s WHERE pk = %s",
                            (access_token, app_id)
                        )

                    db.commit()
                    cursor.close()
                    db.close()

                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(f"<h1>Callback received and token processed for App ID: {app_id}</h1>".encode())
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

    def connect_db(self):
        return mysql.connector.connect(
            host=os.getenv('MYSQL_HOST'),
            user=os.getenv('MYSQL_USER'),
            password=os.getenv('MYSQL_PASSWORD'),
            database=os.getenv('MYSQL_DB')
        )

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
        print(f"Serving at port {PORT}")
        httpd.serve_forever()
