import os
import requests
from flask import Flask, redirect, request, session, url_for, render_template

app = Flask(__name__)
app.secret_key = os.urandom(24)

SLACK_CLIENT_ID = os.getenv("SLACK_CLIENT_ID")
SLACK_CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET")
SLACK_REDIRECT_URI = os.getenv("SLACK_REDIRECT_URI", "https://your-heroku-app.herokuapp.com/callback")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return redirect(f"https://slack.com/oauth/v2/authorize?client_id={SLACK_CLIENT_ID}&scope=chat:write&redirect_uri={SLACK_REDIRECT_URI}")

@app.route('/callback')
def callback():
    code = request.args.get('code')
    response = requests.post('https://slack.com/api/oauth.v2.access', data={
        'client_id': SLACK_CLIENT_ID,
        'client_secret': SLACK_CLIENT_SECRET,
        'code': code,
        'redirect_uri': SLACK_REDIRECT_URI
    })
    data = response.json()
    session['webhook_url'] = data.get('incoming_webhook', {}).get('url')
    return redirect(url_for('success'))

@app.route('/success')
def success():
    return f"Webhook URL: {session.get('webhook_url', 'No webhook URL found')}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
