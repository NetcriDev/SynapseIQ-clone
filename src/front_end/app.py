from flask import Flask, render_template, jsonify, session, redirect, url_for, request
from authlib.integrations.flask_client import OAuth
from functools import wraps
from six.moves.urllib.parse import urlencode
import requests
import os

app = Flask(__name__)

AUTH0_CLIENT_ID = os.environ.get("AUTH0_CLIENT_ID", "RYJg443VOd2t6cX9CrtD6F0PZgqEILQX")
AUTH0_DOMAIN = os.environ.get("AUTH0_DOMAIN", "rel8edto.us.auth0.com")
AUTH0_CLIENT_SECRET = os.environ.get("AUTH0_CLIENT_SECRET", "HEo_aOEuEKiHHL9yKFG4F8uqL1ZvgGzW935t8Jp1J-jQ-IZLFYPeGVqI4KxAKFy6")
AUTH0_CALLBACK_URL = os.environ.get("AUTH0_CALLBACK_URL", "https://synapse.rel8ed.to/callback")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "ThisIsTheSecretKeyFallback")

PROFILE_KEY = 'profile'
JWT_PAYLOAD_KEY = 'jwt_payload'

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

EXTERNAL_SEARCH_API_BASE_URL = "https://8162-52-116-202-144.ngrok-free.app/incident/search"
EXTERNAL_MARKETER_API_URL = "https://8162-52-116-202-144.ngrok-free.app/marketer-users/"

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

def get_user_role_by_email(email):
    headers = {'ngrok-skip-browser-warning': 'true'}
    try:
        response = requests.get(EXTERNAL_MARKETER_API_URL, headers=headers)
        response.raise_for_status()
        marketers = response.json()
        for user in marketers:
            if user.get("email") == email:
                return user.get("role")
    except requests.exceptions.RequestException as e:
        print(f"Erro ao consultar role do usuário: {e}")
    return None

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
    user_role = session[JWT_PAYLOAD_KEY].get('role')

    is_admin = user_role == 'admin'

    print("Role:", user_role)
    print("User ID:", user_id)
    print("User Email:", user_email)
    print("Is Admin:", is_admin)

    return render_template('main.html', user_id=user_id, user_email=user_email, is_admin=is_admin)

@app.route('/incident_search_proxy')
@requires_auth
def incident_search_proxy():
    current_user_email = session[JWT_PAYLOAD_KEY].get('email')
    user_role = session[JWT_PAYLOAD_KEY].get('role')
    is_admin = user_role == 'admin'

    api_params = dict(request.args)
    requested_marketer_username = api_params.pop('marketer_username', None)

    if not is_admin:
        marketer_username_to_filter = _marketer_email_to_username_map.get(current_user_email)
        if marketer_username_to_filter:
            api_params['marketer_username'] = marketer_username_to_filter
            print(f"DEBUG: Não admin. Filtrando por marketer_username: {marketer_username_to_filter}")
        else:
            print(f"AVISO: Email do usuário logado ({current_user_email}) NÃO encontrado no mapeamento de marketers.")
    else:
        if requested_marketer_username:
            api_params['marketer_username'] = requested_marketer_username
            print(f"DEBUG: Admin. Filtrando por requested_marketer_username: {requested_marketer_username}")
        else:
            print("DEBUG: Admin. Sem filtro de marketer_username para ver todos os dados.")

    headers = {'ngrok-skip-browser-warning': 'true'}
    full_api_url = f"{EXTERNAL_SEARCH_API_BASE_URL}?{urlencode(api_params)}"
    print(f"DEBUG: Chamando API externa: {full_api_url}")

    response = requests.get(full_api_url, headers=headers)

    try:
        response.raise_for_status()
        all_incidents = response.json()
        if not isinstance(all_incidents, list):
            print(f"AVISO: A API externa /incident/search não retornou uma lista. Conteúdo: {all_incidents}")
            all_incidents = []
        return jsonify({'items': all_incidents}), response.status_code
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar dados da API: {e}")
        error_details = response.text if response else "Sem resposta detalhada"
        print(f"Conteúdo da Resposta da API (em erro): {error_details}")
        return jsonify({"error": str(e), "api_response": error_details}), response.status_code if response else 500

@app.route('/marketer-users')
@requires_auth
def get_marketer_users():
    headers = {'ngrok-skip-browser-warning': 'true'}
    try:
        response = requests.get(EXTERNAL_MARKETER_API_URL, headers=headers)
        response.raise_for_status()
        marketers = response.json()
        return jsonify(marketers), response.status_code
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar usuários marketers para o dropdown: {e}")
        return jsonify({"error": str(e)}), response.status_code if response else 500

@app.route('/user_is_admin')
@requires_auth
def user_is_admin():
    user_role = session[JWT_PAYLOAD_KEY].get('role')
    is_admin_status = user_role == 'admin'
    return jsonify({'is_admin': is_admin_status})

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
    user_email = userinfo.get('email')

    # Obtem a role com base na API externa
    userinfo['role'] = get_user_role_by_email(user_email)

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
