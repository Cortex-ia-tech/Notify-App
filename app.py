from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime


app = Flask(__name__)

def criar_tabela():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS licencas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            vencimento DATE NOT NULL,
            dias_antes INTEGER NOT NULL,
            ultimo_envio DATE
        )
    ''')
    conn.commit()
    conn.close()

criar_tabela()


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

@app.route('/listar')
def listar_licencas():
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT id, nome, vencimento, dias_antes, COALESCE(ultimo_envio, '-') FROM licencas")
        licencas = c.fetchall()
        conn.close()

        html = "<h2>Licenças Cadastradas</h2><ul>"
        for lic in licencas:
            html += f"<li>ID: {lic[0]} | Nome: {lic[1]} | Vencimento: {lic[2]} | Dias antes: {lic[3]} | Último envio: {lic[4]}</li>"
        html += "</ul>"
        return html
    
    except Exception as e:
        return f"<h2>Erro interno</h2><p>{str(e)}</p>"

#if __name__ == '__main__':
    #app.run(host='0.0.0.0', port=10000)

