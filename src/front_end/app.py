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
    # Sua função getroles existente, ainda é útil para manter a estrutura
    # mas as roles não serão usadas para lógica de acesso neste momento.
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
    # As roles ainda são buscadas, mas a lógica 'is_admin' foi removida do template.
    user_roles = session[JWT_PAYLOAD_KEY]['roles'] # Apenas para manter a estrutura do JWT payload
    user_id = session[JWT_PAYLOAD_KEY]['sub'] 
    user_email = session[JWT_PAYLOAD_KEY].get('email')
    
    print("Roles:", user_roles)
    print("User ID:", user_id) 
    print("User Email:", user_email)

    # Note que 'is_admin' não é mais passado para o template.
    return render_template('main.html', user_id=user_id, user_email=user_email)


EXTERNAL_SEARCH_API_BASE_URL = "https://8162-52-116-202-144.ngrok-free.app/incident/search"
EXTERNAL_MARKETER_API_URL = "https://8162-52-116-202-144.ngrok-free.app/marketer-users/"

# Variável global para armazenar o mapeamento de e-mail para username
# Isso será populado na inicialização do app.
_marketer_email_to_username_map = {}

def update_marketer_email_map():
    """
    Busca usuários marketers da API externa e constrói um mapeamento
    de email para username.
    """
    global _marketer_email_to_username_map
    headers = {'ngrok-skip-browser-warning': 'true'}
    try:
        response = requests.get(EXTERNAL_MARKETER_API_URL, headers=headers)
        response.raise_for_status()
        marketers_data = response.json()
        
        # ASSUMÇÃO: Cada objeto de marketer tem um campo 'email' e 'username'.
        # AJUSTE AQUI se seus campos tiverem outros nomes (ex: 'marketer_email', 'id')
        new_map = {m.get('email'): m.get('username') for m in marketers_data if m.get('email') and m.get('username')}
        _marketer_email_to_username_map = new_map
        print(f"DEBUG: Mapeamento de email do Marketer atualizado: {_marketer_email_to_username_map}")
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar usuários marketers para o mapeamento: {e}")
        # Em caso de erro, o mapa pode ficar vazio, levando a problemas no filtro.
        # Considere uma melhor manipulação de erros aqui.

# Esta função será chamada na inicialização do aplicativo
# para carregar o mapeamento de marketers.
with app.app_context():
    update_marketer_email_map()


@app.route('/incident_search_proxy')
@requires_auth
def incident_search_proxy():
    current_user_email = session[JWT_PAYLOAD_KEY].get('email')
    
    api_params = dict(request.args) 
    
    # Remove qualquer filtro de marketer_username vindo do frontend,
    # pois sempre aplicaremos o filtro baseado no usuário logado.
    api_params.pop('marketer_username', None)

    # Encontra o username do marketer correspondente ao e-mail do usuário logado
    marketer_username_to_filter = _marketer_email_to_username_map.get(current_user_email)
    
    if marketer_username_to_filter:
        # Se encontramos um username, adicionamos ele como filtro para a API externa
        api_params['marketer_username'] = marketer_username_to_filter
        print(f"DEBUG: Filtrando por marketer_username: {marketer_username_to_filter} (para o email: {current_user_email})")
    else:
        print(f"AVISO: Email do usuário logado ({current_user_email}) NÃO encontrado no mapeamento de marketers. Nenhum filtro de marketer será aplicado.")
        # Se o email não for encontrado, a API externa pode retornar todos os dados
        # ou nenhum dado, dependendo da sua implementação.
        # Idealmente, todos os usuários que acessam esta rota devem estar mapeados como marketers.

    headers = {'ngrok-skip-browser-warning': 'true'}
    full_api_url = f"{EXTERNAL_SEARCH_API_BASE_URL}?{urlencode(api_params)}"
    print(f"DEBUG: Chamando API externa: {full_api_url}") 
    
    response = requests.get(full_api_url, headers=headers)

    try:
        response.raise_for_status() 
        all_incidents = response.json()
        
        if not isinstance(all_incidents, list):
            print(f"AVISO: A API externa não retornou uma lista. Conteúdo: {all_incidents}")
            all_incidents = [] # Garante que all_incidents seja sempre uma lista
        # ***********************
        
        return jsonify({'items': all_incidents}), response.status_code
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar dados da API: {e}")
        error_details = response.text if response else "Sem resposta detalhada"
        print(f"Conteúdo da Resposta da API (em erro): {error_details}")
        return jsonify({"error": str(e), "api_response": error_details}), response.status_code if response else 500

@app.route('/marketer-users') 
@requires_auth
def get_marketer_users():
    # Esta rota pode ser usada para popular dropdowns no futuro,
    # mas no momento não terá uso direto sem a lógica de admin.
    headers = {'ngrok-skip-browser-warning': 'true'}
    try:
        response = requests.get(EXTERNAL_MARKETER_API_URL, headers=headers)
        response.raise_for_status()
        marketers = response.json()
        return jsonify(marketers), response.status_code
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar usuários marketers: {e}")
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
    userinfo['roles'] = getroles(userid) # Roles ainda são buscadas, mas não usadas para lógica de acesso aqui
    session[JWT_PAYLOAD_KEY] = userinfo
    session[PROFILE_KEY] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture']
    }
    return redirect('/')

if __name__ == '__main__':
    # Garante que o mapeamento de marketers seja carregado na inicialização
    update_marketer_email_map() 
    app.run(host='0.0.0.0', port=5000, debug=True)