from flask import Flask, render_template, jsonify, session, redirect, url_for, request
from authlib.integrations.flask_client import OAuth
from functools import wraps
from six.moves.urllib.parse import urlencode
import requests

app = Flask(__name__)

# Auth0 init
PROFILE_KEY = 'profile'
JWT_PAYLOAD_KEY = 'jwt_payload'
AUTH0_CLIENT_ID = "RYJg443VOd2t6cX9CrtD6F0PZgqEILQX"
AUTH0_DOMAIN = "rel8edto.us.auth0.com"
AUTH0_CLIENT_SECRET = "HEo_aOEuEKiHHL9yKFG4F8uqL1ZvgGzW935t8Jp1J-jQ-IZLFYPeGVqI4KxAKFy6"
AUTH0_CALLBACK_URL = "http://localhost:5000/callback"

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
    client_kwargs={'scope': 'openid profile email'},
)

EXTERNAL_SEARCH_API_BASE_URL = "http://localhost:5000/mock-incident-search"
EXTERNAL_MARKETER_API_URL = "http://localhost:5000/mock-marketer-users"

def getroles(userid):
    headers = {'content-type': 'application/json'}
    data = {
        "client_id": AUTH0_CLIENT_ID,
        "client_secret": AUTH0_CLIENT_SECRET,
        "audience": f"https://{AUTH0_DOMAIN}/api/v2/",
        "grant_type": "client_credentials"
    }
    response = requests.post(f"https://{AUTH0_DOMAIN}/oauth/token", headers=headers, json=data)
    access_token = response.json().get('access_token')
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(f"https://{AUTH0_DOMAIN}/api/v2/users/{userid}/roles", headers=headers)
    roles = response.json()
    return [r.get('name') for r in roles if r.get('name')]

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if PROFILE_KEY not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

def fetch_marketers():
    mock_data = [
        {"email": "marketing@example.com", "username": "marketer1", "role": "marketing"},
        {"email": "plus@example.com", "username": "plususer", "role": "marketing_plus"},
        {"email": "admin@example.com", "username": "adminuser", "role": "admin"}
    ]
    return mock_data

def fetch_incidents(filtered_params):
    return [{"case_number": "ABC123", "description": "Test incident"}]

@app.route('/')
@requires_auth
def main_page():
    user_id = session[JWT_PAYLOAD_KEY]['sub']
    user_email = session[JWT_PAYLOAD_KEY].get('email')
    return render_template('main.html', user_id=user_id, user_email=user_email)

@app.route('/marketer-users')
@requires_auth
def get_marketer_users():
    marketers = fetch_marketers()
    non_admin_marketers = [m for m in marketers if m.get('role') != 'admin']
    return jsonify(non_admin_marketers)

@app.route('/incident_search_proxy')
@requires_auth
def incident_search_proxy():
    current_user_email = session[JWT_PAYLOAD_KEY].get('email')
    api_params = dict(request.args)

    marketers = fetch_marketers()
    user_info = next((m for m in marketers if m.get('email') == current_user_email), None)

    if not user_info:
        return jsonify({
            "error": "Unauthorized user",
            "message": "Please request access to bpessoa@rel8ed.to"
        }), 403

    role = user_info.get('role')
    username = user_info.get('username')

    if role == "marketing":
        api_params['marketer_username'] = username
    elif role == "marketing_plus":
        if 'marketer_username' not in api_params or not api_params['marketer_username']:
            api_params['marketer_username'] = username
    elif role == "admin":
        if 'marketer_username' in api_params and api_params['marketer_username'] == '':
            api_params.pop('marketer_username')
    else:
        return jsonify({
            "error": "Unauthorized role",
            "message": "Your role is not recognized. Please contact support."
        }), 403

    incidents = fetch_incidents(api_params)
    return jsonify({'items': incidents})

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
    userid = userinfo['sub']
    userinfo['roles'] = getroles(userid)
    session[JWT_PAYLOAD_KEY] = userinfo
    session[PROFILE_KEY] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture']
    }
    return redirect('/')

@app.route('/mock-incident-search')
def mock_incident_search():
    return jsonify([{"case_number": "MOCK001", "description": "Mock incident 1"}])

@app.route('/mock-marketer-users')
def mock_marketer_users():
    return jsonify(fetch_marketers())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
