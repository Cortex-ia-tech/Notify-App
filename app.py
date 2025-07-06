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
    c.execute('SELECT nome, vencimento FROM licencas')
    licencas = c.fetchall()
    conn.close()

    hoje = datetime.now().date()
    a_vencer = []
    vencidas = []

    for nome, vencimento in licencas:
        data_venc = datetime.strptime(vencimento, '%Y-%m-%d').date()
        if data_venc >= hoje:
            a_vencer.append((nome, data_venc))
        else:
            vencidas.append((nome, data_venc))

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


#if __name__ == '__main__':
    #app.run(host='0.0.0.0', port=10000)

