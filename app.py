from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime


app = Flask(__name__)

def criar_tabela():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Cria a tabela de licenças
    c.execute('''
        CREATE TABLE IF NOT EXISTS licencas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            vencimento DATE NOT NULL,
            dias_antes INTEGER NOT NULL
        )
    ''')

    # Verifica e cria a coluna 'ultimo_envio' se necessário
    c.execute("PRAGMA table_info(licencas)")
    colunas = [coluna[1] for coluna in c.fetchall()]
    if 'ultimo_envio' not in colunas:
        try:
            c.execute("ALTER TABLE licencas ADD COLUMN ultimo_envio DATE")
        except Exception as e:
            print("Erro ao adicionar coluna:", e)

    # Cria a tabela de usuários
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senha TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()



@app.route('/')
def home():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT id, nome, vencimento FROM licencas')
    licencas = c.fetchall()
    conn.close()

    hoje = datetime.now().date()
    a_vencer = []
    vencidas = []

    for id_,nome, vencimento in licencas:
        data_venc = datetime.strptime(vencimento, '%Y-%m-%d').date()
        if data_venc >= hoje:
            a_vencer.append((id_,nome, data_venc))
        else:
            vencidas.append((id_,nome, data_venc))

    return render_template('home.html', a_vencer=a_vencer, vencidas=vencidas)



@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if request.method == 'POST':
        nome = request.form['nome']
        vencimento = request.form['vencimento']
        dias_antes = request.form['dias_antes']

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('INSERT INTO licencas (nome, vencimento, dias_antes) VALUES (?, ?, ?)',
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

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        try:
            c.execute('INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)', (nome, email, senha))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "Este e-mail já está cadastrado."
        conn.close()

        return redirect('/')
    
    return render_template('registrar.html')


@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    if request.method == 'POST':
        nome = request.form['nome']
        vencimento = request.form['vencimento']
        dias_antes = request.form['dias_antes']

        c.execute('''
            UPDATE licencas
            SET nome = ?, vencimento = ?, dias_antes = ?
            WHERE id = ?
        ''', (nome, vencimento, dias_antes, id))
        conn.commit()
        conn.close()
        return redirect('/')

    # Se for GET, busca os dados da licença
    c.execute('SELECT nome, vencimento, dias_antes FROM licencas WHERE id = ?', (id,))
    licenca = c.fetchone()
    conn.close()

    if licenca:
        return render_template('editar.html', id=id, nome=licenca[0], vencimento=licenca[1], dias_antes=licenca[2])
    else:
        return "Licença não encontrada"


criar_tabela()

#if __name__ == '__main__':
    #app.run(host='0.0.0.0', port=10000)

