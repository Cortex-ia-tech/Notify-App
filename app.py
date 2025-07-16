# app.py
from persist.cache import ler_lembretes_cache, editar_lembrete_cache, sincronizar_cache_com_postgre, inserir_lembrete_cache, inicializar_cache_sqlite
from flask import jsonify
from random import randint
from flask import Flask, render_template, request, redirect, session, url_for, flash
import psycopg2
from psycopg2 import sql, errors
from datetime import datetime
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash

# Importe APENAS as funções de rota do seu arquivo senha.py
from senha import (
    forgot_password_route,
    reset_password_route,
    change_password_route
)


app = Flask(__name__)

# --- Configurações da Aplicação ---
app.config['SECRET_KEY'] = 'SUA_CHAVE_SECRETA_MUITO_LONGA_E_ALEATORIA_E_UNICA'
app.config['SECURITY_PASSWORD_SALT'] = 'UM_SALT_MUITO_SEGURO_PARA_SENHAS_E_TOKENS'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Configurações do Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'leonardomoreira@petroserra.com'
app.config['MAIL_PASSWORD'] = 'obdf ilkz cpcj hbfn'
app.config['MAIL_DEFAULT_SENDER'] = 'leonardomoreira@petroserra.com'

mail = Mail(app)
app.mail = mail

# Configurações de Conexão com Banco PostgreSQL (Supabase)
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
            senha TEXT NOT NULL
        )
    ''')

    # Altere a tabela de licencas para adicionar a nova coluna 'marcador'
    # Esta abordagem é para quando você NÃO USA Flask-Migrate (Alembic)
    # Ela tenta adicionar a coluna, e se ela já existe (erro de "duplicate column"), ignora.
    try:
        c.execute('''
            ALTER TABLE licencas
            ADD COLUMN IF NOT EXISTS marcador TEXT NOT NULL DEFAULT 'Geral';
        ''')
        # A nova coluna deve ser NOT NULL, então definimos um DEFAULT para preencher
        # os registros existentes e futuros que não especificarem um marcador.
    except errors.DuplicateColumn:
        # Se a coluna já existe, apenas ignore o erro
        conn.rollback() # Garante que a transação seja desfeita para que outras operações possam continuar
        print("Coluna 'marcador' já existe na tabela 'licencas'.")
    except Exception as e:
        conn.rollback()
        print(f"Erro ao adicionar coluna 'marcador': {e}")


    # Cria a tabela de licenças (garantindo que usuario_id esteja presente)
    # Mantemos o IF NOT EXISTS aqui, mas o foco é o ALTER TABLE acima para adicionar a coluna
    c.execute('''
        CREATE TABLE IF NOT EXISTS licencas (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            vencimento DATE NOT NULL,
            dias_antes INTEGER NOT NULL,
            usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
            marcador TEXT NOT NULL DEFAULT 'Geral' -- Garante que a coluna esteja aqui se a tabela for criada do zero
        )
    ''')

    conn.commit()
    conn.close()


# --- Classe User para Flask-Login (UMA ÚNICA DEFINIÇÃO) ---
class User(UserMixin):
    def __init__(self, id_, nome, email, senha_hash):
        self.id = id_
        self.nome = nome
        self.email = email
        self.senha_hash = senha_hash

    def get_id(self):
        return str(self.id)


@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, nome, email, senha FROM usuarios WHERE id = %s', (int(user_id),))
    user_data = c.fetchone()
    conn.close()
    if user_data:
        return User(*user_data)
    return None

# --- Rotas do Aplicativo Principal ---

@app.route('/')
    
#@login_required
def home():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    
    usuario_id = current_user.id

    active_tag = request.args.get('tag')
    hoje = datetime.now().date()

    # ⚡️ Lê os lembretes do cache local, não do Postgre
    lembretes = ler_lembretes_cache(usuario_id)

    a_vencer = []
    vencidas = []
    marcadores_unicos = set()

    for id_, nome, vencimento_str, dias_antes, marcador in lembretes:
        vencimento = datetime.strptime(vencimento_str, '%Y-%m-%d').date()
        if active_tag and marcador != active_tag:
            continue

        marcadores_unicos.add(marcador)

        if vencimento >= hoje:
            a_vencer.append((id_, nome, vencimento, marcador))
        else:
            vencidas.append((id_, nome, vencimento, marcador))

    return render_template(
        'home.html',
        a_vencer=a_vencer,
        vencidas=vencidas,
        marcadores=sorted(marcadores_unicos),
        active_tag=active_tag
    )


@app.route('/excluir/<int:id>', methods=['POST'])
def excluir(id):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    usuario_id = current_user.id

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Verifica se o lembrete pertence ao usuário logado
        cur.execute('SELECT id FROM lembretes WHERE id = %s AND usuario_id = %s', (id, usuario_id))
        lembrete = cur.fetchone()

        if not lembrete:
            return redirect(url_for('home'))

        # Executa exclusão
        cur.execute('DELETE FROM lembretes WHERE id = %s', (id,))
        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        print(f"Erro ao excluir lembrete: {e}")

    return redirect(url_for('home'))



@app.route('/cadastrar', methods=['GET', 'POST'])
#@login_required

def cadastrar():

    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    usuario_id = current_user.id
    #conn = get_db_connection()
    #c = conn.cursor()

    lembretes = ler_lembretes_cache(usuario_id)
    marcadores_existentes = sorted(set(l[4] for l in lembretes))
    # <<< FIM DO BLOCO ADICIONADO >>>

    if request.method == 'POST':
        # Reabra a conexão para a operação POST
        conn = get_db_connection()
        c = conn.cursor()

        nome = request.form['nome']
        vencimento = request.form['vencimento']
        dias_antes = request.form['dias_antes']
        
        # Pega o marcador do campo select
        marcador_selecionado = request.form.get('marcador_existente')
        # Pega o novo marcador do campo de texto (se 'novo_marcador' for a opção selecionada)
        novo_marcador = request.form.get('novo_marcador_input')

        # Lógica para determinar qual marcador usar
        if marcador_selecionado == 'novo_marcador' and novo_marcador:
            marcador_final = novo_marcador.strip() # Remove espaços em branco extras
            if not marcador_final: # Se o novo marcador estiver vazio após strip
                flash('O nome do novo marcador não pode ser vazio.', 'danger')
                conn.close()
                # Retorna ao template com os dados e marcadores para manter o estado
                return render_template(
                    'cadastrar.html',
                    nome_licenca=nome, # Para preencher o campo nome no erro
                    data_vencimento=vencimento, # Para preencher o campo data no erro
                    dias_antes=dias_antes, # Para preencher o campo dias_antes no erro
                    marcador_selecionado=marcador_selecionado, # Manter a opção selecionada
                    novo_marcador_input=novo_marcador, # Manter o texto do novo marcador
                    marcadores_existentes=marcadores_existentes # Para popular o select
                )
        elif marcador_selecionado and marcador_selecionado != 'novo_marcador':
            marcador_final = marcador_selecionado.strip()
        else:
            # Caso não tenha selecionado nem existente nem novo (ex: 'Selecione um marcador')
            # Ou se a opção 'novo_marcador' foi selecionada mas o input ficou vazio.
            flash('Por favor, selecione um marcador ou digite um novo.', 'danger')
            conn.close()
            # Retorna ao template com os dados e marcadores para manter o estado
            return render_template(
                'cadastrar.html',
                nome_licenca=nome,
                data_vencimento=vencimento,
                dias_antes=dias_antes,
                marcador_selecionado=marcador_selecionado,
                novo_marcador_input=novo_marcador,
                marcadores_existentes=marcadores_existentes
            )

        try:
    # Criamos um ID temporário negativo para garantir unicidade até sincronizar com o Postgre
            id_temp = -randint(100000, 999999)

            lembrete = (id_temp, nome, vencimento, int(dias_antes), marcador_final)
            inserir_lembrete_cache(usuario_id, lembrete)

            flash('Lembrete salvo localmente! Será sincronizado mais tarde.', 'success')
            return redirect(url_for('home'))
        except Exception as e:
            flash(f'Erro ao salvar lembrete localmente: {e}', 'danger')
            
        finally:
            conn.close()

    # Para requisições GET (ou se o POST falhar e renderizar novamente o formulário)
    return render_template('cadastrar.html', marcadores_existentes=marcadores_existentes)


@app.route('/registrar', methods=['GET', 'POST'])
def registrar():

    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    
    usuario_id = current_user.id

    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']

        hashed_password = generate_password_hash(senha)

        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute('INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s) RETURNING id',
                      (nome, email, hashed_password))
            new_user_id = c.fetchone()[0]
            conn.commit()
            flash('Usuário registrado com sucesso! Faça login para continuar.', 'success')
            return redirect(url_for('login'))
        except errors.UniqueViolation:
            conn.rollback()
            flash('Este e-mail já está cadastrado.', 'danger')
        finally:
            conn.close()

    return render_template('registrar.html')


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['senha']

        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT id, nome, email, senha FROM usuarios WHERE email = %s', (email,))
        user_data = c.fetchone()
        conn.close()

        if user_data:
            stored_password_hash = user_data[3]
            if check_password_hash(stored_password_hash, password):
                user_obj = User(id_=user_data[0], nome=user_data[1], email=user_data[2], senha_hash=user_data[3])
                login_user(user_obj)
                conn = get_db_connection()
                c = conn.cursor()
                c.execute('SELECT id, nome, vencimento, dias_antes, marcador FROM licencas WHERE usuario_id = %s', (user_obj.id,))
                lembretes = c.fetchall()
                conn.close()

                inicializar_cache_sqlite(user_obj.id, lembretes)
                
                next_page = request.args.get('next')
                flash(f'Olá, {user_obj.nome}! Bem-vindo(a) de volta.', 'success')
                return redirect(next_page or url_for('home'))
            else:
                flash('Email ou senha inválidos.', 'danger')
        else:
            flash('Email ou senha inválidos.', 'danger')

    return render_template('login.html')


@app.route('/editar/<int:id>', methods=['GET', 'POST'])
#@login_required
def editar(id):

    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    
    usuario_id = current_user.id
    lembretes = ler_lembretes_cache(usuario_id)

    # Busca o lembrete pelo ID no cache local
    lembrete = next((l for l in lembretes if l[0] == id), None)
    if not lembrete:
        flash('Lembrete não encontrado ou você não tem permissão para editá-lo.', 'danger')
        return redirect(url_for('home'))

    nome_atual, vencimento_atual, dias_antes_atual, marcador_atual = lembrete[1:]
    vencimento_atual = datetime.strptime(vencimento_atual, '%Y-%m-%d')

    # Coletar todos os marcadores do cache
    marcadores_existentes = sorted(set(l[4] for l in lembretes))

    if request.method == 'POST':
        nome = request.form['nome']
        vencimento = request.form['vencimento']
        dias_antes = request.form['dias_antes']

        marcador_selecionado = request.form.get('marcador_existente')
        novo_marcador = request.form.get('novo_marcador_input')

        # Lógica para determinar o marcador final
        if marcador_selecionado == 'novo_marcador' and novo_marcador:
            marcador_final = novo_marcador.strip()
        elif marcador_selecionado and marcador_selecionado != 'novo_marcador':
            marcador_final = marcador_selecionado.strip()
        else:
            marcador_final = marcador_atual or 'Geral'

        novos_dados = (nome, vencimento, int(dias_antes), marcador_final)

        try:
            editar_lembrete_cache(usuario_id, id, novos_dados)
            flash('Lembrete atualizado localmente! Será sincronizado mais tarde.', 'success')
            return redirect(url_for('home'))
        except Exception as e:
            flash(f'Erro ao atualizar lembrete localmente: {e}', 'danger')

    return render_template(
        'editar.html',
        id=id,
        nome=nome_atual,
        vencimento=vencimento_atual,
        dias_antes=dias_antes_atual,
        marcador_atual=marcador_atual,
        marcadores_existentes=marcadores_existentes
    )


@app.route('/logout')
#@login_required
def logout():

    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    
    usuario_id = current_user.id

    try:
        # ⚡️ Sincroniza com Postgre antes de sair
        sincronizar_cache_com_postgre(current_user.id, app.config['DB_CONN_PARAMS'])
        flash('Dados sincronizados com sucesso.', 'success')
    except Exception as e:
        flash(f'Erro ao sincronizar os dados com o servidor: {e}', 'danger')

    logout_user()
    session.clear()
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('login'))



@app.route('/suporte', methods=['GET', 'POST'])
#@login_required
def suporte():
    if request.method == 'POST':
        assunto = request.form['assunto']
        mensagem_usuario = request.form['mensagem']

        remetente_email = current_user.email
        remetente_nome = current_user.nome

        destinatario_suporte = 'leonardomoreira@petroserra.com'

        try:
            msg = Message(
                subject=f"Suporte Notify - {assunto} (de {remetente_nome} - {remetente_email})",
                sender=app.config['MAIL_DEFAULT_SENDER'],
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
            return redirect(url_for('home'))
        except Exception as e:
            app.logger.error(f"Erro ao enviar demanda de suporte de {remetente_email}: {e}")
            flash('Ocorreu um erro ao enviar sua demanda de suporte. Por favor, tente novamente mais tarde.', 'danger')
            return render_template('suporte.html',
                                   assunto_preenchido=assunto,
                                   mensagem_preenchida=mensagem_usuario)

    return render_template('suporte.html')

# --- Registro das Rotas de Senha do 'senha.py' ---
app.add_url_rule('/forgot_password', 'forgot_password', forgot_password_route, methods=['GET', 'POST'])
app.add_url_rule('/reset_password/<token>', 'reset_password', reset_password_route, methods=['GET', 'POST'])
app.add_url_rule('/change_password', 'change_password', change_password_route, methods=['GET', 'POST'])


@app.route('/sincronizar', methods=['POST'])
#@login_required
def sincronizar():
    try:
        sincronizar_cache_com_postgre(current_user.id, app.config['DB_CONN_PARAMS'])
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'erro', 'mensagem': str(e)}), 500


# Garante que as tabelas sejam criadas ao iniciar o aplicativo
with app.app_context():
    criar_tabela()


if __name__ == '__main__':
    app.run(debug=True)