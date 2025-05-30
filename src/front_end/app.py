from flask import Flask, render_template, jsonify, session, redirect, url_for, request
from authlib.integrations.flask_client import OAuth
from functools import wraps
from six.moves.urllib.parse import urlencode
import requests
import os # Importar para usar variáveis de ambiente

app = Flask(__name__)

# Configurações Auth0 (pode ser carregadas de variáveis de ambiente para segurança)
# É altamente recomendado usar variáveis de ambiente para credenciais em produção!
AUTH0_CLIENT_ID = os.environ.get("AUTH0_CLIENT_ID", "RYJg443VOd2t6cX9CrtD6F0PZgqEILQX")
AUTH0_DOMAIN = os.environ.get("AUTH0_DOMAIN", "rel8edto.us.auth0.com")
AUTH0_CLIENT_SECRET = os.environ.get("AUTH0_CLIENT_SECRET", "HEo_aOEuEKiHHL9yKFG4F8uqL1ZvgGzW935t8Jp1J-jQ-IZLFYPeGVqI4KxAKFy6")
AUTH0_CALLBACK_URL = os.environ.get("AUTH0_CALLBACK_URL", "https://synapse.rel8ed.to/callback") # Seu ngrok ou domínio público
# A chave secreta do Flask TAMBÉM deve ser uma variável de ambiente em produção
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

def getroles(userid):
    # Sua função getroles existente
    headers = {'content-type': 'application/json'}
    data = {"client_id":AUTH0_CLIENT_ID,"client_secret":AUTH0_CLIENT_SECRET,"audience":"https://rel8edto.us.auth0.com/api/v2/","grant_type":"client_credentials"}
    response = requests.post(f'https://{AUTH0_DOMAIN}/oauth/token', headers=headers, json=data)
    access_token = response.json().get('access_token')
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(f'https://{AUTH0_DOMAIN}/api/v2/users/{userid}/roles', headers=headers)
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
    user_email = session[JWT_PAYLOAD_KEY].get('email')
    
    is_admin = 'admin' in user_roles # Verifica se o usuário tem a role 'admin'
    
    print("Roles:", user_roles)
    print("User ID:", user_id) 
    print("User Email:", user_email)
    print("Is Admin:", is_admin)

    # Passa 'is_admin' para o template HTML
    return render_template('main.html', user_id=user_id, user_email=user_email, is_admin=is_admin)


EXTERNAL_SEARCH_API_BASE_URL = "https://8162-52-116-202-144.ngrok-free.app/incident/search"
EXTERNAL_MARKETER_API_URL = "https://8162-52-116-202-144.ngrok-free.app/marketer-users/"

_marketer_email_to_username_map = {}

def update_marketer_email_map():
    global _marketer_email_to_username_map
    headers = {'ngrok-skip-browser-warning': 'true'}
    try:
        response = requests.get(EXTERNAL_MARKETER_API_URL, headers=headers)
        response.raise_for_status()
        marketers_data = response.json() # Assume que retorna uma lista de objetos marketer
        
        # AJUSTE AQUI: Confirme se os campos são 'email' e 'username' na sua API
        # ou se são outros (ex: 'marketer_email', 'id_marketer')
        new_map = {m.get('email'): m.get('username') for m in marketers_data if m.get('email') and m.get('username')}
        _marketer_email_to_username_map = new_map
        print(f"DEBUG: Mapeamento de email do Marketer atualizado: {_marketer_email_to_username_map}")
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar usuários marketers para o mapeamento: {e}")
        # Considere uma melhor manipulação de erros aqui para evitar que o mapa fique vazio.

# Carrega o mapeamento na inicialização do app
with app.app_context():
    update_marketer_email_map()


@app.route('/incident_search_proxy')
@requires_auth
def incident_search_proxy():
    current_user_email = session[JWT_PAYLOAD_KEY].get('email')
    user_roles = session[JWT_PAYLOAD_KEY]['roles'] 
    is_admin = 'admin' in user_roles # Verifica role de admin novamente aqui para segurança

    api_params = dict(request.args) 
    
    # Pega o 'marketer_username' que pode ter vindo do frontend (se o admin usou o dropdown)
    requested_marketer_username = api_params.pop('marketer_username', None)

    if not is_admin:
        # Se não for admin, SEMPRE filtra pelo username do usuário logado
        marketer_username_to_filter = _marketer_email_to_username_map.get(current_user_email)
        
        if marketer_username_to_filter:
            api_params['marketer_username'] = marketer_username_to_filter
            print(f"DEBUG: Não admin. Filtrando por marketer_username: {marketer_username_to_filter}")
        else:
            print(f"AVISO: Email do usuário logado ({current_user_email}) NÃO encontrado no mapeamento de marketers. Não será aplicado filtro de marketer.")
            # Nenhuma ação adicional, a API externa pode retornar vazio ou tudo dependendo da sua regra default.
    else: # É admin
        if requested_marketer_username:
            # Se o admin selecionou um marketer específico no dropdown, usa o username dele
            api_params['marketer_username'] = requested_marketer_username 
            print(f"DEBUG: Admin. Filtrando por requested_marketer_username: {requested_marketer_username}")
        else:
            # Se o admin NÃO selecionou um marketer específico (dropdown "Todos os Marketers"),
            # NÃO adicione o filtro de 'marketer_username' para que a API retorne TODOS.
            print("DEBUG: Admin. Sem filtro de marketer_username para ver todos os dados.")
            pass # Não adiciona o filtro 'marketer_username'

    headers = {'ngrok-skip-browser-warning': 'true'}
    full_api_url = f"{EXTERNAL_SEARCH_API_BASE_URL}?{urlencode(api_params)}"
    print(f"DEBUG: Chamando API externa: {full_api_url}") 
    
    response = requests.get(full_api_url, headers=headers)

    try:
        response.raise_for_status() 
        all_incidents = response.json() # Corrigido para esperar uma lista diretamente
        
        if not isinstance(all_incidents, list):
            print(f"AVISO: A API externa /incident/search não retornou uma lista. Conteúdo: {all_incidents}")
            all_incidents = [] # Garante que seja uma lista para evitar erros no frontend
        
        return jsonify({'items': all_incidents}), response.status_code
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar dados da API: {e}")
        error_details = response.text if response else "Sem resposta detalhada"
        print(f"Conteúdo da Resposta da API (em erro): {error_details}")
        return jsonify({"error": str(e), "api_response": error_details}), response.status_code if response else 500

@app.route('/marketer-users') 
@requires_auth
def get_marketer_users():
    # Esta rota é chamada pelo frontend para popular o dropdown de marketers (apenas para admins)
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
    """
    Retorna um JSON indicando se o usuário logado possui a role 'admin'.
    """
    user_roles = session[JWT_PAYLOAD_KEY]['roles']
    is_admin_status = 'admin' in user_roles
    return jsonify({'is_admin': is_admin_status})


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
    # Garante que o mapeamento de marketers seja carregado na inicialização
    update_marketer_email_map() 
    app.run(host='0.0.0.0', port=5000, debug=True)