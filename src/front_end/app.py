from flask import Flask, jsonify, request, session, redirect, url_for
import requests # Importa a biblioteca para fazer requisições HTTP
import os

app = Flask(__name__)
app.secret_key = os.urandom(24) # Chave secreta para sessões

# URL base do seu serviço de usuários externo
EXTERNAL_USERS_API_URL = "http://8162-52-116-202-144.ngrok-free.app"

# Rota de login (exemplo básico, adapte ao seu sistema de autenticação)
@app.route('/login', methods=['POST'])
def login():
    # Isso é um exemplo muito básico de login.
    # Na vida real, você faria uma autenticação mais robusta,
    # provavelmente contra um banco de dados ou um serviço de autenticação.
    # Para este exemplo, vamos simular um login simples:
    username = request.form.get('username')
    password = request.form.get('password') # Senha não é usada aqui, apenas para exemplo
    
    if username: # Apenas para simular que o usuário está "logado"
        session['logged_in_username'] = username
        return redirect(url_for('main_page'))
    return "Login falhou", 401


# Rota para deslogar
@app.route('/logout')
def logout():
    session.pop('logged_in_username', None)
    return redirect(url_for('login_page')) # Redireciona para sua página de login

# Rota para a página principal (onde seu main.html será renderizado)
@app.route('/')
def main_page():
    # Renderize seu main.html aqui
    # Você pode passar o status de admin diretamente para o template se preferir,
    # mas a abordagem com /user_is_admin é mais limpa para o JS
    return app.send_static_file('main.html') # Assumindo que main.html está na pasta 'static'

# Endpoint que o JavaScript chama para verificar o status de admin
@app.route('/user_is_admin')
def user_is_admin():
    logged_in_username = session.get('logged_in_username')

    if not logged_in_username:
        # Se não há usuário logado, não é admin
        return jsonify({'is_admin': False}), 200

    try:
        # Faz uma requisição ao serviço externo para obter todos os usuários
        response = requests.get(f"{EXTERNAL_USERS_API_URL}/marketer-users/")
        response.raise_for_status()  # Levanta um erro para status de erro HTTP
        
        all_users_data = response.json()

        # Procura o usuário logado na lista e verifica sua role
        is_admin = False
        for user in all_users_data:
            if user.get('username') == logged_in_username:
                if user.get('role') == 'admin':
                    is_admin = True
                break # Encontrou o usuário, pode parar de procurar

        return jsonify({'is_admin': is_admin}), 200

    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar roles de usuários externos: {e}")
        # Em caso de erro na comunicação com a API externa, assuma que não é admin
        return jsonify({'is_admin': False, 'error': 'Failed to fetch user roles'}), 500

# Proxy para a busca de incidentes, agora pode filtrar por marketer_username
@app.route('/incident_search_proxy', methods=['GET'])
def incident_search_proxy():
    logged_in_username = session.get('logged_in_username')
    if not logged_in_username:
        # Se não logado, talvez redirecionar ou retornar erro
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # Primeiro, determine a role do usuário logado
        user_is_admin_response = requests.get(url_for('user_is_admin', _external=True))
        user_is_admin_response.raise_for_status()
        is_admin_data = user_is_admin_response.json()
        is_current_user_admin = is_admin_data.get('is_admin', False)

        # Constrói a URL para a API externa de incidentes
        external_api_url = "http://8162-52-116-202-144.ngrok-free.app/incident"
        params = request.args.to_dict()

        # Lógica de filtro por marketer:
        # Se for admin, o frontend pode enviar o marketer_username. Use-o.
        # Se não for admin, force o filtro para o username do próprio usuário logado.
        if not is_current_user_admin:
            params['marketer_username'] = logged_in_username
        elif 'marketer_username' in params and params['marketer_username'] == '':
            # Se admin e 'marketer_username' é vazio, significa "todos os marketers",
            # então remove o parâmetro para a API externa (se a API externa entender isso)
            params.pop('marketer_username')

        # Realiza a requisição GET para a API externa
        response = requests.get(external_api_url, params=params)
        response.raise_for_status()  # Levanta um erro para status de erro HTTP

        return jsonify(response.json()), response.status_code

    except requests.exceptions.RequestException as e:
        print(f"Erro ao chamar API externa de incidentes: {e}")
        return jsonify({'error': 'Erro ao buscar dados de incidentes'}), 500


# Proxy para buscar a lista de usuários marketers (apenas para admins)
@app.route('/marketer-users', methods=['GET'])
def marketer_users_proxy():
    logged_in_username = session.get('logged_in_username')
    if not logged_in_username:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # Verifica se o usuário logado é admin
        user_is_admin_response = requests.get(url_for('user_is_admin', _external=True))
        user_is_admin_response.raise_for_status()
        is_admin_data = user_is_admin_response.json()
        
        if not is_admin_data.get('is_admin'):
            return jsonify({'error': 'Forbidden: Only administrators can access this resource'}), 403

        # Se for admin, busca a lista completa de usuários do serviço externo
        response = requests.get(f"{EXTERNAL_USERS_API_URL}/marketer-users/")
        response.raise_for_status()
        return jsonify(response.json()), response.status_code

    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar usuários marketer externos: {e}")
        return jsonify({'error': 'Erro ao carregar lista de marketers'}), 500


# Endpoint para atribuir leads
@app.route('/assign_leads', methods=['POST'])
def assign_leads():
    logged_in_username = session.get('logged_in_username')
    if not logged_in_username:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # Verifica se o usuário logado é admin
        user_is_admin_response = requests.get(url_for('user_is_admin', _external=True))
        user_is_admin_response.raise_for_status()
        is_admin_data = user_is_admin_response.json()
        
        if not is_admin_data.get('is_admin'):
            return jsonify({'error': 'Forbidden: Only administrators can assign leads'}), 403

        data = request.get_json()
        incident_ids = data.get('incident_ids')
        assign_to_marketer_username = data.get('assign_to_marketer_username')

        if not incident_ids or not assign_to_marketer_username:
            return jsonify({'error': 'Incident IDs and marketer username are required'}), 400

        # Mapeia os IDs dos incidentes para o formato esperado pela API externa
        # Isso pode precisar de ajuste dependendo de como sua API externa espera os IDs
        payload = {
            "incident_ids": incident_ids,
            "assign_to": assign_to_marketer_username
        }

        # Envia a requisição para a API externa
        assign_response = requests.post(
            f"{EXTERNAL_USERS_API_URL}/assign", # Substitua por seu endpoint real de atribuição
            json=payload
        )
        assign_response.raise_for_status()

        return jsonify(assign_response.json()), assign_response.status_code

    except requests.exceptions.RequestException as e:
        print(f"Erro ao atribuir leads via API externa: {e}")
        return jsonify({'error': 'Erro ao atribuir leads'}), 500


# Rota para a página de login (apenas para exemplo)
@app.route('/login_page')
def login_page():
    return """
    <h1>Login</h1>
    <form action="/login" method="post">
        Username: <input type="text" name="username"><br>
        Password: <input type="password" name="password"><br>
        <input type="submit" value="Login">
    </form>
    """

if __name__ == '__main__':
    app.run(debug=True)