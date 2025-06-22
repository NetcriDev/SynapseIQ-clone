from flask import Flask, render_template, jsonify, session, redirect, url_for, request
from authlib.integrations.flask_client import OAuth
from functools import wraps
from six.moves.urllib.parse import urlencode
import requests

app = Flask(__name__)

# Auth0 init
PROFILE_KEY = 'profile'
JWT_PAYLOAD_KEY = 'jwt_payload'
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

# Function to get roles from Auth0
def getroles(userid):
    headers = {'content-type': 'application/json'}
    data = {"client_id":AUTH0_CLIENT_ID,"client_secret":AUTH0_CLIENT_SECRET,"audience":"https://rel8edto.us.auth0.com/api/v2/","grant_type":"client_credentials"}
    response = requests.post('https://rel8edto.us.auth0.com/oauth/token', headers=headers, json=data)
    access_token = response.json().get('access_token')
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(f'https://rel8edto.us.auth0.com/api/v2/users/{userid}/roles', headers=headers)
    roles = response.json()
    return [r.get('name') for r in roles if r.get('name')]

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
    user_id = session[JWT_PAYLOAD_KEY]['sub'] 
    user_email = session[JWT_PAYLOAD_KEY].get('email')
    
    # The information about the user is already in the session
    # No need to fetch it again from the API
    
    print("User ID:", user_id) 
    print("User Email:", user_email)

    return render_template('main.html', 
                           user_id=user_id, 
                           user_email=user_email)

EXTERNAL_SEARCH_API_BASE_URL = "https://fcab11165760.ngrok.app/incident/search"
EXTERNAL_MARKETER_API_URL = "https://fcab11165760.ngrok.app/marketer-users/"

_marketer_email_to_username_map = {}

def update_marketer_email_map():
    global _marketer_email_to_username_map
    headers = {'ngrok-skip-browser-warning': 'true'}
    try:
        response = requests.get(EXTERNAL_MARKETER_API_URL, headers=headers)
        response.raise_for_status()
        marketers_data = response.json()
        
        new_map = {m.get('email'): m.get('username') for m in marketers_data if m.get('email') and m.get('username')}
        _marketer_email_to_username_map = new_map
        print(f"DEBUG: Mapeamento de email do Marketer atualizado: {_marketer_email_to_username_map}")
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar usuários marketers para o mapeamento: {e}")

with app.app_context():
    update_marketer_email_map()

# Path to the incident search proxy
@app.route('/incident_search_proxy')
@requires_auth
def incident_search_proxy():
    current_user_email = session[JWT_PAYLOAD_KEY].get('email')
    api_params = dict(request.args) # Get all query parameters as a dictionary

    headers = {'ngrok-skip-browser-warning': 'true'}
    print(f"DEBUG: Usuário autenticado: {current_user_email}")

    try:
        marketers_response = requests.get(EXTERNAL_MARKETER_API_URL, headers=headers)
        marketers_response.raise_for_status()
        marketers = marketers_response.json()

        user_info = next((m for m in marketers if m.get('email') == current_user_email), None)
        
        if user_info:
            role = user_info.get('role')
            username = user_info.get('username')
            print(f"DEBUG: Usuário '{current_user_email}' tem role '{role}'")

            # Filtered parameters for the external API
            if role == "marketing":
                # Marketing users can ONLY see their own leads.
                # Remove any marketer_username that came from the frontend to ensure this.
                api_params['marketer_username'] = username
                print(f"DEBUG: Usuário marketing. Aplicando filtro forçado de marketer_username: {username}")
            elif role == "admin":
                # Admin users can use the dropdown filter.
                # If 'marketer_username' was sent from the frontend (dropdown), it is already in api_params.
                # We do nothing if the value is empty, because "All Marketers" means do not filter by marketer.
                if 'marketer_username' in api_params and api_params['marketer_username'] == '':
                    api_params.pop('marketer_username') # Remove se for vazio (All Marketers)
                print(f"DEBUG: Usuário é admin. Filtro de marketer_username: {api_params.get('marketer_username', 'Nenhum')}")
            elif role == "marketing_plus":
                # Se frontend passou marketer_username (filtro), usa o que veio
                # Se não passou nada, força o próprio
                if 'marketer_username' not in api_params or not api_params['marketer_username']:
                    api_params['marketer_username'] = username
                    print(f"DEBUG: marketing_plus: sem filtro, aplicando próprio username: {username}")
                else:
                    print(f"DEBUG: marketing_plus: aplicando filtro de marketer_username: {api_params['marketer_username']}")
            else:
                print(f"DEBUG: Role '{role}' não reconhecida. Nenhum filtro aplicado, mas deve ser tratado no frontend.")
                # Consider returning a 403 error here if unrecognized roles should not see data
                return jsonify({
                    "error": "Unauthorized role",
                    "message": "Your role is not recognized. Please contact support."
                }), 403
        else:
            print(f"WARNING: User {current_user_email} not found on marketers list.")
            return jsonify({
                "error": "Unauthorized user",
                "message": "Please request access to bpessoa@rel8ed.to"
            }), 403
    except requests.exceptions.RequestException as e:
        print(f"Error getting data for: {e}")
        return jsonify({"error": str(e)}), 500

    # Builds the final URL with the parameters applied
    # `urlencode` already handles empty parameters and encoding
    full_api_url = f"{EXTERNAL_SEARCH_API_BASE_URL}?{urlencode(api_params)}"
    print(f"DEBUG: Calling external API: {full_api_url}") 
    
    try:
        response = requests.get(full_api_url, headers=headers)
        response.raise_for_status()
        all_incidents = response.json()
        if not isinstance(all_incidents, list):
            print(f"WARNING: External API did not return a list. Contents: {all_incidents}")
            all_incidents = []
        return jsonify({'items': all_incidents}), response.status_code
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from API: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/marketer-users')
@requires_auth
def get_marketer_users():
    """
    This route returns the list of marketers (excluding admins)
    to populate the dropdown on the frontend.
    """
    headers = {'ngrok-skip-browser-warning': 'true'}
    try:
        response = requests.get(EXTERNAL_MARKETER_API_URL, headers=headers)
        response.raise_for_status()
        all_marketers = response.json()

        # Filter out users with the role 'admin'
        # Assuming your EXTERNAL_MARKETER_API_URL returns a 'role' key for each user
        non_admin_marketers = [
            marketer for marketer in all_marketers
            if marketer.get('role') != 'admin'
        ]

        return jsonify(non_admin_marketers), response.status_code
    except requests.exceptions.RequestException as e:
        print(f"Error fetching marketer users: {e}")
        return jsonify({"error": str(e)}), response.status_code if response else 500

# Endpoint to get user information    
@app.route('/user-info')
@requires_auth
def get_user_info():
    """
    Returns the logged in user information (username and admin status)
    as JSON to the frontend.
    """
    current_user_email = session[JWT_PAYLOAD_KEY].get('email')
    
    current_user_username = None
    is_admin_user = False

    try:
        headers = {'ngrok-skip-browser-warning': 'true'}
        marketers_response = requests.get(EXTERNAL_MARKETER_API_URL, headers=headers)
        marketers_response.raise_for_status()
        marketers = marketers_response.json()
        user_info = next((m for m in marketers if m.get('email') == current_user_email), None)
        
        if user_info:
            current_user_username = user_info.get('username')
            if user_info.get('role') == 'admin':
                is_admin_user = True
        else:
            print(f"NOTICE: User {current_user_email} not found in marketers list when searching for user-info.")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching marketers user data for /user-info: {e}")
        # For simplicity, we will return None/False in case of an error in the Marketers API.

    is_marketing_plus_user = False
    if user_info:
        if user_info.get('role') == 'marketing_plus':
            is_marketing_plus_user = True

    return jsonify({
        'current_user_username': current_user_username,
        'is_admin_user': is_admin_user,
        'is_marketing_plus_user': is_marketing_plus_user
    })



# Auth functions
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

if __name__ == '__main__':
    update_marketer_email_map() 
    app.run(host='0.0.0.0', port=5000, debug=True)