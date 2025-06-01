from flask import Flask, render_template, jsonify, session, redirect, url_for, request
from authlib.integrations.flask_client import OAuth
from functools import wraps
from six.moves.urllib.parse import urlencode
import requests

app = Flask(__name__)

# Auth0 init (mantido como está)
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
    
    # As informações do usuário agora serão buscadas pelo JavaScript via /user-info
    # Não precisa mais passar current_user_username e is_admin_user aqui
    
    print("User ID:", user_id) 
    print("User Email:", user_email)

    return render_template('main.html', 
                           user_id=user_id, 
                           user_email=user_email)

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

with app.app_context():
    update_marketer_email_map()

@app.route('/incident_search_proxy')
@requires_auth
def incident_search_proxy():
    current_user_email = session[JWT_PAYLOAD_KEY].get('email')
    api_params = dict(request.args) # Obtém todos os parâmetros da URL do frontend

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

            # LÓGICA DE FILTRAGEM DE MARKETER REVISADA
            if role == "marketing":
                # Usuários de marketing SÓ podem ver seus próprios leads.
                # Remove qualquer marketer_username que veio do frontend para garantir isso.
                api_params['marketer_username'] = username
                print(f"DEBUG: Usuário marketing. Aplicando filtro forçado de marketer_username: {username}")
            elif role == "admin":
                # Usuários admin podem usar o filtro do dropdown.
                # Se 'marketer_username' foi enviado pelo frontend (dropdown), ele já está em api_params.
                # Não fazemos nada se o valor é vazio, pois "All Marketers" significa não filtrar por marketer.
                if 'marketer_username' in api_params and api_params['marketer_username'] == '':
                    api_params.pop('marketer_username') # Remove se for vazio (All Marketers)
                print(f"DEBUG: Usuário é admin. Filtro de marketer_username: {api_params.get('marketer_username', 'Nenhum')}")
            else:
                print(f"DEBUG: Role '{role}' não reconhecida. Nenhum filtro aplicado, mas deve ser tratado no frontend.")
                # Considerar retornar um erro 403 aqui se roles não reconhecidas não devem ver dados
                return jsonify({
                    "error": "Unauthorized role",
                    "message": "Your role is not recognized. Please contact support."
                }), 403
        else:
            print(f"AVISO: Usuário {current_user_email} não encontrado na lista de marketers.")
            return jsonify({
                "error": "Unauthorized user",
                "message": "Please request access to bpessoa@rel8ed.to"
            }), 403
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar dados de usuários marketers: {e}")
        return jsonify({"error": str(e)}), 500

    # Monta a URL final com os parâmetros aplicados
    # `urlencode` já lida com parâmetros vazios e encodamento
    full_api_url = f"{EXTERNAL_SEARCH_API_BASE_URL}?{urlencode(api_params)}"
    print(f"DEBUG: Chamando API externa: {full_api_url}") 
    
    try:
        response = requests.get(full_api_url, headers=headers)
        response.raise_for_status()
        all_incidents = response.json()
        if not isinstance(all_incidents, list):
            print(f"AVISO: A API externa não retornou uma lista. Conteúdo: {all_incidents}")
            all_incidents = []
        return jsonify({'items': all_incidents}), response.status_code
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar dados da API: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/marketer-users') 
@requires_auth
def get_marketer_users():
    # Essa rota já está correta para retornar a lista completa de marketers
    # para popular o dropdown no frontend.
    headers = {'ngrok-skip-browser-warning': 'true'}
    try:
        response = requests.get(EXTERNAL_MARKETER_API_URL, headers=headers)
        response.raise_for_status()
        marketers = response.json()
        return jsonify(marketers), response.status_code
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar usuários marketers: {e}")
        return jsonify({"error": str(e)}), response.status_code if response else 500
    
@app.route('/user-info')
@requires_auth
def get_user_info():
    """
    Retorna as informações do usuário logado (username e status de admin)
    como JSON para o frontend.
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
            print(f"AVISO: Usuário {current_user_email} não encontrado na lista de marketers ao buscar user-info.")

    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar dados de usuários marketers para /user-info: {e}")
        # Decida como lidar com isso: pode retornar False/None ou um erro HTTP.
        # Por simplicidade, vamos retornar None/False em caso de erro na API de marketers.

    return jsonify({
        'current_user_username': current_user_username,
        'is_admin_user': is_admin_user
    })

# Auth functions (mantidas como estão)
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