from flask import Flask, render_template, request, redirect, session, url_for, flash
import psycopg2
from psycopg2 import sql
from datetime import datetime # Certifique-se de que datetime esteja importado
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin

app = Flask(__name__)

app.secret_key = 'segredo-super-seguro' # Mantenha sua chave secreta aqui!

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Conexão com banco PostgreSQL (Supabase)
conn_params = {
    "host": "aws-0-sa-east-1.pooler.supabase.com",
    "port": 6543,
    "dbname": "postgres",
    "user": "postgres.yqwohzkwllelxptcysmn",
    "password": "2GJJMcsVVP1BPKKK",
}

def criar_tabela():
    conn = psycopg2.connect(**conn_params)
    c = conn.cursor()

    # Cria a tabela de usuários ANTES da tabela de licenças para a FK
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL
        )
    ''')

    # Cria a tabela de licenças (garantindo que usuario_id esteja presente)
    c.execute('''
        CREATE TABLE IF NOT EXISTS licencas (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            vencimento DATE NOT NULL,
            dias_antes INTEGER NOT NULL,
            usuario_id INTEGER REFERENCES usuarios(id)
        )
    ''')
    conn.commit()
    conn.close()


# Classe User para Flask-Login
class User(UserMixin):
    def __init__(self, id_, nome, email, senha):
        self.id = id_
        self.nome = nome
        self.email = email
        self.senha = senha

    def get_id(self):
        return str(self.id)


@login_manager.user_loader
def load_user(user_id):
    conn = psycopg2.connect(**conn_params)
    c = conn.cursor()
    # Certifique-se de que a ordem das colunas aqui corresponde à ordem do construtor User
    c.execute('SELECT id, nome, email, senha FROM usuarios WHERE id = %s', (int(user_id),))
    user_data = c.fetchone()
    conn.close()
    if user_data:
        return User(*user_data)
    return None

# --- Rotas ---

@app.route('/')
@login_required # Protege a rota: exige login para acessar
def home():
    usuario_id = current_user.id

    conn = psycopg2.connect(**conn_params)
    c = conn.cursor()
    c.execute('SELECT id, nome, vencimento FROM licencas WHERE usuario_id = %s', (usuario_id,))
    licencas = c.fetchall()
    conn.close()

    hoje = datetime.now().date()
    a_vencer = []
    vencidas = []

    for id_, nome, vencimento in licencas:
        data_venc = vencimento
        if data_venc >= hoje:
            a_vencer.append((id_, nome, data_venc))
        else:
            vencidas.append((id_, nome, data_venc))

    return render_template('home.html', a_vencer=a_vencer, vencidas=vencidas)


@app.route('/cadastrar', methods=['GET', 'POST'])
@login_required
def cadastrar():
    if request.method == 'POST':
        nome = request.form['nome']
        vencimento = request.form['vencimento']
        dias_antes = request.form['dias_antes']
        usuario_id = current_user.id

        conn = psycopg2.connect(**conn_params)
        c = conn.cursor()
        c.execute('INSERT INTO licencas (nome, vencimento, dias_antes, usuario_id) VALUES (%s, %s, %s, %s)',
                  (nome, vencimento, dias_antes, usuario_id))
        conn.commit()
        conn.close()

        flash('Licença cadastrada com sucesso!', 'success')
        return redirect(url_for('home'))

    # Certifique-se de que você tem um template 'cadastrar.html'
    return render_template('cadastrar.html')


@app.route('/registrar', methods=['GET', 'POST'])
# @login_required # Removi login_required. Geralmente, registrar não exige login prévio.
def registrar():
    # Se você quiser que APENAS um ADMIN (já logado) possa registrar, mantenha o @login_required acima
    # E mantenha esta verificação de email. Caso contrário, remova.
    # if current_user.is_authenticated and current_user.email != 'leonardomoreira@petroserra.com':
    #     flash('Você não tem permissão para registrar novos usuários.', 'danger')
    #     return redirect(url_for('home'))

    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']

        conn = psycopg2.connect(**conn_params)
        c = conn.cursor()
        try:
            c.execute('INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s) RETURNING id', (nome, email, senha))
            new_user_id = c.fetchone()[0] # Pega o ID do novo usuário
            conn.commit()
            flash('Usuário registrado com sucesso! Faça login para continuar.', 'success')
            # Após registrar, você pode redirecionar para a página de login
            return redirect(url_for('login'))
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            flash('Este e-mail já está cadastrado.', 'danger')
        finally:
            conn.close()

    # Certifique-se de que você tem um template 'registrar.html'
    return render_template('registrar.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        conn = psycopg2.connect(**conn_params)
        c = conn.cursor()
        c.execute('SELECT id, nome, email, senha FROM usuarios WHERE email = %s AND senha = %s', (email, senha))
        user_data = c.fetchone()
        conn.close()

        if user_data:
            user_obj = User(id_=user_data[0], nome=user_data[1], email=user_data[2], senha=user_data[3])
            login_user(user_obj)
            next_page = request.args.get('next')
            flash(f'Olá, {user_obj.nome}! Bem-vindo(a) de volta.', 'success') # Mensagem de boas-vindas
            return redirect(next_page or url_for('home'))
        else:
            flash('Usuário ou senha inválidos.', 'danger')
            # Permite renderizar o template de login novamente com a mensagem de erro
    return render_template('login.html')


@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    usuario_id = current_user.id
    conn = psycopg2.connect(**conn_params)
    c = conn.cursor()

    c.execute('SELECT nome, vencimento, dias_antes FROM licencas WHERE id = %s AND usuario_id = %s', (id, usuario_id))
    licenca = c.fetchone()

    if not licenca:
        conn.close()
        flash('Licença não encontrada ou você não tem permissão para editá-la.', 'danger')
        return redirect(url_for('home'))

    if request.method == 'POST':
        nome = request.form['nome']
        vencimento = request.form['vencimento']
        dias_antes = request.form['dias_antes']

        c.execute('''
            UPDATE licencas
            SET nome = %s, vencimento = %s, dias_antes = %s
            WHERE id = %s AND usuario_id = %s
        ''', (nome, vencimento, dias_antes, id, usuario_id))
        conn.commit()
        conn.close()
        flash('Licença atualizada com sucesso!', 'success')
        return redirect(url_for('home'))

    conn.close()
    # Certifique-se de que você tem um template 'editar.html'
    return render_template('editar.html', id=id, nome=licenca[0], vencimento=licenca[1], dias_antes=licenca[2])


@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('login')) # Redireciona para a página de login após o logout

@app.route('/suporte')
@login_required # Geralmente, a página de suporte pode não exigir login, mas como está no dropdown de logado, podemos manter.
def suporte():
    # Certifique-se de que você tem um template 'suporte.html' ou retorne uma mensagem simples
    return render_template('suporte.html')
    # Ou simplesmente: return "<h1>Página de Suporte</h1><p>Entre em contato conosco!</p>"


# Chama criar_tabela apenas uma vez, na inicialização do app
criar_tabela()

if __name__ == '__main__':
    app.run(debug=True)