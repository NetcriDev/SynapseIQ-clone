from flask import Flask, render_template, jsonify, session, redirect, url_for
from authlib.integrations.flask_client import OAuth
from functools import wraps
from six.moves.urllib.parse import urlencode
import requests

app = Flask(__name__)

# Auth0 init
PROFILE_KEY = 'profile'
#
AUTH0_CLIENT_ID="RYJg443VOd2t6cX9CrtD6F0PZgqEILQX"
AUTH0_DOMAIN="rel8edto.us.auth0.com"
AUTH0_CLIENT_SECRET="HEo_aOEuEKiHHL9yKFG4F8uqL1ZvgGzW935t8Jp1J-jQ-IZLFYPeGVqI4KxAKFy6"
AUTH0_CALLBACK_URL="https://synapse.rel8ed.to/callback"

app.secret_key = 'ThisIsTheSecretKey'
oauth = OAuth(app)
auth0 = oauth.register(
    'auth0',
    client_id=AUTH0_CLIENT_ID,
    client_secret=AUTH0_CLIENT_SECRET,
    api_base_url=f'https://{AUTH0_DOMAIN}',
    access_token_url=f'https://{AUTH0_DOMAIN}/oauth/token',
    authorize_url=f'https://{AUTH0_DOMAIN}/authorize',
    server_metadata_url=f'https://{AUTH0_DOMAIN}/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid profile email',
    },
)

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if PROFILE_KEY not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

@app.route('/')
@requires_auth
def main_page():
    return render_template('main.html')

SEARCH_API_URL = "https://990c-52-116-202-144.ngrok-free.app/incident/search?page=1&page_size=200"
@app.route('/incident_search')
@requires_auth
def incident_search():
    response = requests.get(SEARCH_API_URL, headers={
        'ngrok-skip-browser-warning': 'true'
    })

    try:
        response.raise_for_status()
        return jsonify(response.json()), response.status_code
    except:
        return response.text, response.status_code

#Auth functions
@app.route('/login')
def login():
    return auth0.authorize_redirect(redirect_uri=AUTH0_CALLBACK_URL, audience='')

@app.route('/logout')
def logout():
    session.clear()
    params = {'returnTo': url_for('main_page', _external=True), 'client_id': AUTH0_CLIENT_ID}
    return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))

@app.route('/callback')
def callback_handling():
    auth0.authorize_access_token()
    resp = auth0.get('userinfo')
    userinfo = resp.json()
    session["jwt_payload"] = userinfo
    session[PROFILE_KEY] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture']
    }
    return redirect('/')

if __name__ == '__main__':
    app.run(host='localhost', port=5000, debug=True)