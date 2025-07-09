import smtplib
import psycopg2
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import os

# Configurações do remetente (só muda aqui se for outro e-mail de envio geral)
remetente = "leonardomoreira@petroserra.com"
senha_app = "obdf ilkz cpcj hbfn"

# Conexão com o banco PostgreSQL
conn_params = {
    "host": "aws-0-sa-east-1.pooler.supabase.com",
    "port": 6543,
    "dbname": "postgres",
    "user": "postgres.yqwohzkwllelxptcysmn",
    "password": "2GJJMcsVVP1BPKKK"
}

# Caminho do arquivo persistente
ARQUIVO_ENVIADOS = 'persist/emails_enviados.txt'
os.makedirs('persist', exist_ok=True)
if not os.path.exists(ARQUIVO_ENVIADOS):
    open(ARQUIVO_ENVIADOS, 'w').close()

# Lê os códigos já enviados
with open(ARQUIVO_ENVIADOS, 'r') as f:
    codigos_enviados = set(linha.strip() for linha in f)

# Conecta ao banco
conn = psycopg2.connect(**conn_params)
c = conn.cursor()

# Recupera as licenças com dados do usuário
c.execute('''
    SELECT licencas.id, licencas.nome, licencas.vencimento, licencas.dias_antes,
           usuarios.email
    FROM licencas
    JOIN usuarios ON licencas.usuario_id = usuarios.id
''')
licencas = c.fetchall()
conn.close()

hoje = datetime.now().date()

for id_, nome, vencimento, dias_antes, email_usuario in licencas:
    if isinstance(vencimento, str):
        vencimento = datetime.strptime(vencimento, '%Y-%m-%d').date()

    data_alerta = vencimento - timedelta(days=int(dias_antes))
    codigo = f"{int(id_):03d}{hoje.strftime('%d%m%Y')}"

    if not (data_alerta <= hoje <= vencimento):
        continue

    if codigo in codigos_enviados:
        print(f"[SKIP] Já enviado hoje: {nome} ({email_usuario})")
        continue

    # Monta e envia o e-mail
    mensagem = MIMEMultipart()
    mensagem["From"] = remetente
    mensagem["To"] = email_usuario
    mensagem["Subject"] = f"⚠️ Lembrete: {nome} vence em {vencimento.strftime('%d/%m/%Y')}"
    corpo = f"""
Olá,

A licença "{nome}" está próxima do vencimento (vence em {vencimento.strftime('%d/%m/%Y')}).
Você optou por ser avisado(a) com {dias_antes} dias de antecedência.

Acesse o SkyNotify para atualizar essa licença.

Att,  
SkyNotify | Uma criação SkyNet Business Intelligence®
"""
    mensagem.attach(MIMEText(corpo, "plain"))

    try:
        servidor = smtplib.SMTP("smtp.gmail.com", 587)
        servidor.starttls()
        servidor.login(remetente, senha_app)
        servidor.sendmail(remetente, email_usuario, mensagem.as_string())
        servidor.quit()
        print(f"[OK] E-mail enviado para: {email_usuario} ({nome})")

        with open(ARQUIVO_ENVIADOS, 'a') as f:
            f.write(codigo + '\n')

    except Exception as e:
        print(f"[ERRO] Falha ao enviar para {email_usuario}: {e}")
