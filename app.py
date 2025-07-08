from flask import Flask, render_template, request, redirect
import psycopg2
from psycopg2 import sql
from datetime import datetime
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin, logout_user

app = Flask(__name__)

app.secret_key = 'segredo-super-seguro'
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
app.secret_key = 'alguma_chave_secreta_segura'


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

    # Cria a tabela de licenças
    c.execute('''
        CREATE TABLE IF NOT EXISTS licencas (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            vencimento DATE NOT NULL,
            dias_antes INTEGER NOT NULL
        )
    ''')

    # Cria a tabela de usuários
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()


@app.route('/')
@login_required
def home():
    conn = psycopg2.connect(**conn_params)
    c = conn.cursor()
    c.execute('SELECT id, nome, vencimento FROM licencas')
    licencas = c.fetchall()
    conn.close()

    hoje = datetime.now().date()
    a_vencer = []
    vencidas = []

    for id_, nome, vencimento in licencas:
        if vencimento >= hoje:
            a_vencer.append((id_, nome, vencimento))
        else:
            vencidas.append((id_, nome, vencimento))

    return render_template('home.html', a_vencer=a_vencer, vencidas=vencidas)


@app.route('/cadastrar', methods=['GET', 'POST'])
@login_required
def cadastrar():
    if request.method == 'POST':
        nome = request.form['nome']
        vencimento = request.form['vencimento']
        dias_antes = request.form['dias_antes']

        conn = psycopg2.connect(**conn_params)
        c = conn.cursor()
        c.execute('INSERT INTO licencas (nome, vencimento, dias_antes) VALUES (%s, %s, %s)',
                  (nome, vencimento, dias_antes))
        conn.commit()
        conn.close()

        return redirect('/')
    
    return render_template('cadastrar.html')


@app.route('/registrar', methods=['GET', 'POST'])
def registrar():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']

        conn = psycopg2.connect(**conn_params)
        c = conn.cursor()
        try:
            c.execute('INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s)', (nome, email, senha))
            conn.commit()
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            return "Este e-mail já está cadastrado."
        conn.close()

        return redirect('/')
    
    return render_template('registrar.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        conn = psycopg2.connect(**conn_params)
        c = conn.cursor()
        c.execute('SELECT id, nome, email, senha FROM usuarios WHERE email = %s', (email,))
        user = c.fetchone()
        conn.close()

        if user and user[3] == senha:
            login_user(User(*user))
            return redirect('/')
        else:
            return "Login inválido."

    return render_template('login.html')




@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar(id):
    conn = psycopg2.connect(**conn_params)
    c = conn.cursor()

    if request.method == 'POST':
        nome = request.form['nome']
        vencimento = request.form['vencimento']
        dias_antes = request.form['dias_antes']

        c.execute('''
            UPDATE licencas
            SET nome = %s, vencimento = %s, dias_antes = %s
            WHERE id = %s
        ''', (nome, vencimento, dias_antes, id))
        conn.commit()
        conn.close()
        return redirect('/')

    # Se for GET, busca os dados da licença
    c.execute('SELECT nome, vencimento, dias_antes FROM licencas WHERE id = %s', (id,))
    licenca = c.fetchone()
    conn.close()

    if licenca:
        return render_template('editar.html', id=id, nome=licenca[0], vencimento=licenca[1], dias_antes=licenca[2])
    else:
        return "Licença não encontrada"


criar_tabela()

class User(UserMixin):
    def __init__(self, id_, nome, email, senha):
        self.id = id_
        self.nome = nome
        self.email = email
        self.senha = senha

@login_manager.user_loader
def load_user(user_id):
    conn = psycopg2.connect(**conn_params)
    c = conn.cursor()
    c.execute('SELECT id, nome, email, senha FROM usuarios WHERE id = %s', (int(user_id),))
    user = c.fetchone()
    conn.close()
    if user:
        return User(*user)
    return None

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')



# Descomente se quiser rodar localmente:
# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=10000)
