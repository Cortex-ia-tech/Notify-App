# senha.py

from flask import render_template, request, redirect, url_for, flash, current_app
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_required, current_user # Importe se for usar alteração de senha para usuário logado
import psycopg2 # Importar psycopg2 aqui também para o banco de dados

# --- Funções Auxiliares de Banco de Dados (usando a conexão do app principal) ---
def get_db_connection():
    # current_app acessa o objeto Flask da aplicação em execução,
    # onde conn_params deve estar configurado.
    return psycopg2.connect(**current_app.config['DB_CONN_PARAMS'])

def get_user_by_email_db(email):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT id, nome, email, senha FROM usuarios WHERE email = %s', (email,))
    user_data = c.fetchone()
    conn.close()
    return user_data # Retorna uma tupla (id, nome, email, senha_hash) ou None

def update_user_password_db(user_id, new_password_hash):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('UPDATE usuarios SET senha = %s WHERE id = %s', (new_password_hash, user_id))
    conn.commit()
    conn.close()

# --- Funções Auxiliares de Token ---
def get_serializer():
    if 'SECURITY_PASSWORD_SALT' not in current_app.config or 'SECRET_KEY' not in current_app.config:
        raise ValueError("SECRET_KEY e SECURITY_PASSWORD_SALT devem estar configurados no app.py")
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'])

# --- Rotas e Lógica de Senha ---

# Rota para solicitar redefinição de senha (envio de email)
def forgot_password_route():
    if request.method == 'POST':
        email = request.form.get('email')

        user_data = get_user_by_email_db(email) # BUSCAR NO DB REAL

        # Mensagem genérica por segurança para não vazar se o email existe
        flash_message = 'Se o e-mail estiver registrado, um link para redefinir sua senha foi enviado para seu e-mail.', 'info'

        if user_data:
            try:
                s = get_serializer()
                token = s.dumps(email, salt=current_app.config['SECURITY_PASSWORD_SALT'])

                reset_url = url_for('reset_password', token=token, _external=True)

                msg = Message("Redefinição de Senha", recipients=[email],
                              sender=current_app.config['MAIL_DEFAULT_SENDER'])
                msg.html = f"""
                <p>Olá,</p>
                <p>Você solicitou a redefinição de sua senha.</p>
                <p>Para redefinir sua senha, clique no link abaixo:</p>
                <p><a href="{reset_url}">Redefinir Minha Senha</a></p>
                <p>Este link é válido por 1 hora. Se você não solicitou isso, por favor, ignore este e-mail.</p>
                <p>Atenciosamente,<br>Sua Equipe</p>
                """
                current_app.mail.send(msg)
                flash(*flash_message)
            except Exception as e:
                current_app.logger.error(f"Erro ao enviar email de redefinição para {email}: {e}")
                flash('Ocorreu um erro ao enviar o e-mail. Tente novamente mais tarde.', 'error')
        else:
            flash(*flash_message) # Ainda mostra a mensagem genérica

        return redirect(url_for('forgot_password'))
    return render_template('forgot_password.html')


# Rota para redefinir a senha usando o token
def reset_password_route(token):
    s = get_serializer()
    email = None
    try:
        email = s.loads(token, salt=current_app.config['SECURITY_PASSWORD_SALT'], max_age=3600)
    except SignatureExpired:
        flash('O link de redefinição de senha expirou. Por favor, solicite um novo.', 'error')
        return redirect(url_for('forgot_password'))
    except (BadTimeSignature, ValueError):
        flash('Link de redefinição de senha inválido ou corrompido.', 'error')
        return redirect(url_for('forgot_password'))

    # Verifica se o email do token corresponde a um usuário existente
    user_data = get_user_by_email_db(email)
    if not user_data:
        flash('Erro: Usuário não encontrado para este link de redefinição.', 'error')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not new_password or not confirm_password:
            flash('Por favor, preencha ambos os campos de senha.', 'error')
            return render_template('reset_password.html', token=token)

        if new_password != confirm_password:
            flash('As senhas não coincidem.', 'error')
            return render_template('reset_password.html', token=token)

        if len(new_password) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'error')
            return render_template('reset_password.html', token=token)

        # Atualiza a senha no banco de dados REAL
        hashed_password = generate_password_hash(new_password)
        update_user_password_db(user_data[0], hashed_password) # user_data[0] é o id do usuário
        flash('Sua senha foi redefinida com sucesso! Por favor, faça login.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html', token=token)


# Rota para alterar a senha (usuário logado)
def change_password_route():
    if not current_user.is_authenticated:
        flash('Você precisa estar logado para alterar sua senha.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if not old_password or not new_password or not confirm_password:
            flash('Por favor, preencha todos os campos.', 'error')
            return render_template('change_password.html')

        # Obtenha os dados do usuário logado (current_user)
        # O current_user deve ter um atributo `email` ou um método para obter o email
        user_email = current_user.email
        user_data = get_user_by_email_db(user_email)

        if not user_data:
            flash('Erro: Dados do usuário não encontrados no banco de dados.', 'error')
            return redirect(url_for('home'))

        # Verifique a senha antiga usando o hash armazenado (user_data[3] é a senha hash)
        if not check_password_hash(user_data[3], old_password):
            flash('Senha antiga incorreta.', 'error')
            return render_template('change_password.html')

        # Validações da nova senha
        if new_password != confirm_password:
            flash('As novas senhas não coincidem.', 'error')
            return render_template('change_password.html')

        if len(new_password) < 6:
            flash('A nova senha deve ter pelo menos 6 caracteres.', 'error')
            return render_template('change_password.html')

        # Atualiza a senha no banco de dados REAL
        hashed_password = generate_password_hash(new_password)
        update_user_password_db(user_data[0], hashed_password) # user_data[0] é o id do usuário
        flash('Sua senha foi alterada com sucesso!', 'success')
        return redirect(url_for('home')) # Redireciona para onde fizer sentido

    return render_template('change_password.html')