# app.py

from flask import Flask, render_template, request, redirect, session, url_for, flash
import psycopg2
from psycopg2 import sql, errors # Importar errors para tratar exceções específicas
from datetime import datetime
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash # Importar para hashing de senha

# Importe APENAS as funções de rota do seu arquivo senha.py
# O mock users_db_mock não é mais necessário aqui, pois usaremos o DB real.
from senha import (
    forgot_password_route,
    reset_password_route,
    change_password_route
)


app = Flask(__name__)

# --- Configurações da Aplicação ---
app.config['SECRET_KEY'] = 'SUA_CHAVE_SECRETA_MUITO_LONGA_E_ALEATORIA_E_UNICA' # Mude para um valor forte
app.config['SECURITY_PASSWORD_SALT'] = 'UM_SALT_MUITO_SEGURO_PARA_SENHAS_E_TOKENS' # Mude para um valor forte e diferente do SECRET_KEY
app.config['SESSION_COOKIE_SECURE'] = True # Recomenda-se True em produção (HTTPS)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Configurações do Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'leonardomoreira@petroserra.com' # SUBSTITUA PELO SEU EMAIL REAL!
app.config['MAIL_PASSWORD'] = 'obdf ilkz cpcj hbfn' # SUBSTITUA PELA SUA SENHA DE APP REAL!
app.config['MAIL_DEFAULT_SENDER'] = 'leonardomoreira@petroserra.com' # SUBSTITUA PELO SEU EMAIL REAL!

mail = Mail(app)
app.mail = mail # Facilita o acesso ao objeto mail em outras funções

# Configurações de Conexão com Banco PostgreSQL (Supabase)
# É uma boa prática armazenar isso em uma variável de ambiente ou arquivo de configuração
# e não diretamente no código. Para fins de exemplo, mantenho aqui.
app.config['DB_CONN_PARAMS'] = {
    "host": "aws-0-sa-east-1.pooler.supabase.com",
    "port": 6543,
    "dbname": "postgres",
    "user": "postgres.yqwohzkwllelxptcysmn",
    "password": "2GJJMcsVVP1BPKKK",
}

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Please log in to access this page."


# --- Funções de Banco de Dados ---
def get_db_connection():
    return psycopg2.connect(**app.config['DB_CONN_PARAMS'])

def criar_tabela():
    conn = get_db_connection()
    c = conn.cursor()

    # Cria a tabela de usuários ANTES da tabela de licenças para a FK
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL -- Armazenará o HASH da senha
        )
    ''')

    # Cria a tabela de licenças (garantindo que usuario_id esteja presente)
    c.execute('''
        CREATE TABLE IF NOT EXISTS licencas (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            vencimento DATE NOT NULL,
            dias_antes INTEGER NOT NULL,
            usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE -- Adicionado ON DELETE CASCADE
        )
    ''')
    conn.commit()
    conn.close()


# --- Classe User para Flask-Login (UMA ÚNICA DEFINIÇÃO) ---
class User(UserMixin):
    def __init__(self, id_, nome, email, senha_hash): # Renomeado 'senha' para 'senha_hash' para clareza
        self.id = id_
        self.nome = nome
        self.email = email
        self.senha_hash = senha_hash # Armazenamos o hash

    def get_id(self):
        return str(self.id)


@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    # Certifique-se de que a ordem das colunas aqui corresponde à ordem do construtor User
    c.execute('SELECT id, nome, email, senha FROM usuarios WHERE id = %s', (int(user_id),))
    user_data = c.fetchone()
    conn.close()
    if user_data:
        return User(*user_data) # Desempacota a tupla diretamente
    return None

# --- Rotas do Aplicativo Principal ---

@app.route('/')
@login_required # Protege a rota: exige login para acessar
def home():
    usuario_id = current_user.id

    conn = get_db_connection()
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

        conn = get_db_connection()
        c = conn.cursor()
        c.execute('INSERT INTO licencas (nome, vencimento, dias_antes, usuario_id) VALUES (%s, %s, %s, %s)',
                  (nome, vencimento, dias_antes, usuario_id))
        conn.commit()
        conn.close()

        flash('Licença cadastrada com sucesso!', 'success')
        return redirect(url_for('home'))

    return render_template('cadastrar.html')


@app.route('/registrar', methods=['GET', 'POST'])
def registrar():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']

        # CRÍTICO: HASH DA SENHA ANTES DE ARMAZENAR
        hashed_password = generate_password_hash(senha)

        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute('INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s) RETURNING id',
                      (nome, email, hashed_password)) # Armazena o hash
            new_user_id = c.fetchone()[0]
            conn.commit()
            flash('Usuário registrado com sucesso! Faça login para continuar.', 'success')
            return redirect(url_for('login'))
        except errors.UniqueViolation: # Use errors.UniqueViolation
            conn.rollback()
            flash('Este e-mail já está cadastrado.', 'danger')
        finally:
            conn.close()

    return render_template('registrar.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['senha'] # Nome do campo no formulário

        conn = get_db_connection()
        c = conn.cursor()
        # Busque a senha HASHED do banco de dados
        c.execute('SELECT id, nome, email, senha FROM usuarios WHERE email = %s', (email,))
        user_data = c.fetchone()
        conn.close()

        if user_data:
            # CRÍTICO: VERIFIQUE A SENHA USANDO O HASH
            stored_password_hash = user_data[3]
            if check_password_hash(stored_password_hash, password):
                user_obj = User(id_=user_data[0], nome=user_data[1], email=user_data[2], senha_hash=user_data[3])
                login_user(user_obj)
                next_page = request.args.get('next')
                flash(f'Olá, {user_obj.nome}! Bem-vindo(a) de volta.', 'success')
                return redirect(next_page or url_for('home'))
            else:
                flash('Email ou senha inválidos.', 'danger')
        else:
            flash('Email ou senha inválidos.', 'danger')

    return render_template('login.html')


@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    usuario_id = current_user.id
    conn = get_db_connection()
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
    return render_template('editar.html', id=id, nome=licenca[0], vencimento=licenca[1], dias_antes=licenca[2])


@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear() # Limpa a sessão
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('login'))


@app.route('/suporte', methods=['GET', 'POST']) # Adicione 'POST' aqui
@login_required
def suporte():
    if request.method == 'POST':
        assunto = request.form['assunto']
        mensagem_usuario = request.form['mensagem']
        
        # Obtenha o email do usuário logado para referência
        remetente_email = current_user.email
        remetente_nome = current_user.nome # Se você quiser incluir o nome também

        # Email de destino (o seu, como desenvolvedor)
        destinatario_suporte = 'leonardomoreira@petroserra.com'
        
        try:
            msg = Message(
                subject=f"Suporte Notify - {assunto} (de {remetente_nome} - {remetente_email})",
                sender=app.config['MAIL_DEFAULT_SENDER'], # Seu email de envio
                recipients=[destinatario_suporte]
            )
            msg.body = f"""
Mensagem de suporte de: {remetente_nome} ({remetente_email})

Assunto: {assunto}

Mensagem:
{mensagem_usuario}

---
Enviado via formulário de suporte do Notify.
            """
            app.mail.send(msg)
            flash('Sua demanda de suporte foi enviada com sucesso! Em breve entraremos em contato.', 'success')
            return redirect(url_for('home')) # Ou para uma página de confirmação
        except Exception as e:
            app.logger.error(f"Erro ao enviar demanda de suporte de {remetente_email}: {e}")
            flash('Ocorreu um erro ao enviar sua demanda de suporte. Por favor, tente novamente mais tarde.', 'danger')
            # Permite que o formulário seja renderizado novamente com os dados, se desejar
            return render_template('suporte.html',
                                   assunto_preenchido=assunto,
                                   mensagem_preenchida=mensagem_usuario)

    # Para requisições GET
    return render_template('suporte.html')

# --- Registro das Rotas de Senha do 'senha.py' ---
app.add_url_rule('/forgot_password', 'forgot_password', forgot_password_route, methods=['GET', 'POST'])
app.add_url_rule('/reset_password/<token>', 'reset_password', reset_password_route, methods=['GET', 'POST'])
app.add_url_rule('/change_password', 'change_password', change_password_route, methods=['GET', 'POST'])


# Garante que as tabelas sejam criadas ao iniciar o aplicativo
with app.app_context():
    criar_tabela()


if __name__ == '__main__':
    app.run(debug=True)