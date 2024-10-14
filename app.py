from flask import Flask, redirect, request, session, url_for, render_template_string
import requests
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Replace these with your app's credentials
SLACK_CLIENT_ID = 'your_client_id'
SLACK_CLIENT_SECRET = 'your_client_secret'
SLACK_REDIRECT_URI = 'http://localhost:5000/slack/callback'

HTML_TEMPLATE = """
<!doctype html>
<title>Install Slack App</title>
<h1>Install Slack App</h1>
<a href="{{ url_for('install') }}">Install Slack App</a>
{% if access_token %}
<h2>Access Token</h2>
<p>{{ access_token }}</p>
<p>You can now use this token to send messages.</p>
<form method="post" action="{{ url_for('send_message') }}">
    <textarea name="message" placeholder="Type your message here"></textarea>
    <button type="submit">Send Message</button>
</form>
{% endif %}
"""

@app.route('/')
def index():
    access_token = session.get('access_token')
    return render_template_string(HTML_TEMPLATE, access_token=access_token)

@app.route('/slack/install')
def install():
    return redirect(
        f'https://slack.com/oauth/v2/authorize?client_id={SLACK_CLIENT_ID}&scope=chat:write&redirect_uri={SLACK_REDIRECT_URI}'
    )

@app.route('/slack/callback')
def callback():
    code = request.args.get('code')
    
    response = requests.post('https://slack.com/api/oauth.v2.access', data={
        'client_id': SLACK_CLIENT_ID,
        'client_secret': SLACK_CLIENT_SECRET,
        'code': code,
        'redirect_uri': SLACK_REDIRECT_URI
    })

    data = response.json()
    
    if response.status_code != 200 or not data.get('ok'):
        return f"Error: {data.get('error')}", 400

    access_token = data['access_token']
    session['access_token'] = access_token
    return redirect(url_for('index'))

@app.route('/send_message', methods=['POST'])
def send_message():
    access_token = session.get('access_token')
    message = request.form['message']

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }

    payload = {
        'channel': '#your-channel',  # Set your channel here
        'text': message
    }

    response = requests.post('https://slack.com/api/chat.postMessage', headers=headers, json=payload)
    data = response.json()

    if response.status_code != 200 or not data.get('ok'):
        return f"Error: {data.get('error')}", 400

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(port=5000)