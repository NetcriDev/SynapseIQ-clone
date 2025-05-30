from flask import Flask, render_template, jsonify, session, redirect, url_for, request # Importe 'request'
from authlib.integrations.flask_client import OAuth
from functools import wraps
from six.moves.urllib.parse import urlencode
import requests

app = Flask(__name__)

# Auth0 init
PROFILE_KEY = 'profile'
JWT_PAYLOAD_KEY = 'jwt_payload'
#
AUTH0_CLIENT_ID="RYJg443VOd2t6cX9CrtD6F0PZgqEILQX"
AUTH0_DOMAIN="rel8edto.us.auth0.com"
AUTH0_CLIENT_SECRET="HEo_aOEuEKiHHL9yKFG4F8uqL1ZvgGzW935t8Jp1J-jQ-IZLFYPeGVqI4KxAKFy6"
AUTH0_CALLBACK_URL="https://synapse.rel8ed.to/callback" # Mantenha seu URL de callback

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
    # Sua função getroles existente
    import requests
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
    user_roles = session[JWT_PAYLOAD_KEY]['roles']
    user_id = session[JWT_PAYLOAD_KEY]['sub'] 
    user_email = session[JWT_PAYLOAD_KEY].get('email') # Obter o email do usuário logado
    print("Roles:", user_roles)
    print("User ID:", user_id) 
    print("User Email:", user_email) # Adicionado para debug
    # Passar o email para o template, se necessário para exibição
    return render_template('main.html', user_id=user_id, user_email=user_email)


# Endpoint da sua API externa
EXTERNAL_SEARCH_API_BASE_URL = "https://8162-52-116-202-144.ngrok-free.app/incident/search"
EXTERNAL_MARKETER_API_URL = "https://8162-52-116-202-144.ngrok-free.app/marketer-users/"

@app.route('/incident_search_proxy') # Renomeado para evitar conflito e clareza
@requires_auth
def incident_search_proxy():
    # O email do usuário logado, que será usado para filtrar os resultados da API externa
    current_user_email = session[JWT_PAYLOAD_KEY].get('email')
    
    # Construir os parâmetros para a API externa a partir dos parâmetros de query do frontend
    # Use request.args para obter todos os parâmetros de query do request do frontend
    api_params = dict(request.args) 
    
    # Remover o marketerId enviado pelo frontend se ele existir, pois o filtro principal será pelo email
    # A menos que você tenha um cenário onde admins possam ver todos, ignore este passo
    if 'marketer_username' in api_params:
        del api_params['marketer_username']

    # Adicionar o filtro do email do usuário logado nos parâmetros da API externa
    # ATENÇÃO: Confirme com sua API externa se o parâmetro para filtrar por email do marketer é 'marketer_email'
    # ou 'marketer_user_email' ou similar. Estou assumindo 'marketer_user_email' com base no seu exemplo.
    api_params['marketer_user_email'] = current_user_email

    # Adicionar ngrok-skip-browser-warning para a requisição à API externa
    headers = {'ngrok-skip-browser-warning': 'true'}

    # Montar a URL completa para a API externa
    # urlencode transforma o dicionário de parâmetros em string de query (ex: param1=val1&param2=val2)
    full_api_url = f"{EXTERNAL_SEARCH_API_BASE_URL}?{urlencode(api_params)}"
    print(f"Calling external API: {full_api_url}") # Para debug
    
    response = requests.get(full_api_url, headers=headers)

    try:
        response.raise_for_status() # Lança um erro para status de erro HTTP (4xx ou 5xx)
        all_incidents = response.json().get('items', []) # Supondo que a resposta tem uma chave 'items'
        
        # A lógica de filtragem adicional em Python aqui seria redundante se a API externa já filtra por marketer_user_email
        # e é a forma mais segura. Se a API externa NÃO PUDER filtrar por marketer_user_email,
        # você teria que aplicar a lógica de filtragem que você tinha aqui, mas seria menos eficiente.
        # Por enquanto, vou assumir que a API externa suporta o filtro 'marketer_user_email'.
        
        return jsonify({'items': all_incidents}), response.status_code
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from API: {e}")
        # Retorna um erro JSON para que o frontend possa lidar com ele
        return jsonify({"error": str(e)}), response.status_code if response else 500

@app.route('/marketer-users') # Endpoint para buscar lista de marketers (para dropdown)
@requires_auth
def get_marketer_users():
    headers = {'ngrok-skip-browser-warning': 'true'}
    try:
        response = requests.get(EXTERNAL_MARKETER_API_URL, headers=headers)
        response.raise_for_status()
        marketers = response.json()
        return jsonify(marketers), response.status_code
    except requests.exceptions.RequestException as e:
        print(f"Error fetching marketer users: {e}")
        return jsonify({"error": str(e)}), response.status_code if response else 500


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
    app.run(host='0.0.0.0', port=5000, debug=True)