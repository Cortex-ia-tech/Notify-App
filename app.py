from flask import Flask, render_template, request, redirect
import psycopg2
from psycopg2 import sql
from datetime import datetime

app = Flask(__name__)

# Conexão com banco PostgreSQL (Supabase)
conn_params = {
    "host": "aws-0-sa-east-1.pooler.supabase.com",
    "port": 6543,
    "dbname": "postgres",
    "user": "postgres.yqwohzkwllelxptcysmn",
    "password": "PdSE1xyxPqTT5fYO",
    "sslmode": "require"
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


@app.route('/editar/<int:id>', methods=['GET', 'POST'])
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

# Descomente se quiser rodar localmente:
# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=10000)
