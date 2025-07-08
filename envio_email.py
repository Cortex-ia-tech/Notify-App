import smtplib
import psycopg2
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import os

# Configurações do e-mail
remetente = "leonardomoreira@petroserra.com"
senha_app = "obdf ilkz cpcj hbfn"
destinatario = "leonardomoreira@petroserra.com"

# Configurações do banco PostgreSQL (Supabase)
conn_params = {
    "host": "aws-0-sa-east-1.pooler.supabase.com",
    "port": 6543,
    "dbname": "postgres",
    "user": "postgres",
    "password": "PdSE1xyxPqTT5fYO"
}

# Caminho do arquivo persistente
ARQUIVO_ENVIADOS = 'persist/emails_enviados.txt'

# Garante que o arquivo exista
os.makedirs('persist', exist_ok=True)
if not os.path.exists(ARQUIVO_ENVIADOS):
    with open(ARQUIVO_ENVIADOS, 'w') as f:
        pass  # cria arquivo vazio

# Lê os códigos de e-mails já enviados
with open(ARQUIVO_ENVIADOS, 'r') as f:
    codigos_enviados = set(linha.strip() for linha in f)

# Conecta ao banco
conn = psycopg2.connect(**conn_params)
c = conn.cursor()
c.execute('SELECT id, nome, vencimento, dias_antes FROM licencas')
licencas = c.fetchall()
conn.close()

# Data de hoje
hoje = datetime.now().date()

for id_, nome, vencimento, dias_antes in licencas:
    data_venc = vencimento
    if isinstance(data_venc, str):
        data_venc = datetime.strptime(data_venc, '%Y-%m-%d').date()

    data_alerta = data_venc - timedelta(days=int(dias_antes))
    codigo = f"{int(id_):03d}{hoje.strftime('%d%m%Y')}"

    if data_alerta <= hoje <= data_venc:
        if codigo in codigos_enviados:
            print(f"[SKIP] E-mail já enviado hoje para: {nome}")
            continue

        # Monta o e-mail
        mensagem = MIMEMultipart()
        mensagem["From"] = remetente
        mensagem["To"] = destinatario
        mensagem["Subject"] = f"⚠️ Lembrete: {nome} vence em {data_venc.strftime('%d/%m/%Y')}"
        corpo = f"""
Olá,

Esta é uma notificação automática do sistema SkyNotify.

A licença "{nome}" está próxima do vencimento (vence em {data_venc.strftime('%d/%m/%Y')}). 
Você optou por receber lembretes a partir de {dias_antes} dias antes.

Acesse o SkyNotify para atualizar essa licença.

Att,  
SkyNotify | SkyNet Business Automation
"""
        mensagem.attach(MIMEText(corpo, "plain"))

        try:
            servidor = smtplib.SMTP("smtp.gmail.com", 587)
            servidor.starttls()
            servidor.login(remetente, senha_app)
            servidor.sendmail(remetente, destinatario, mensagem.as_string())
            servidor.quit()
            print(f"[OK] E-mail enviado para: {nome}")

            # Registra o código no arquivo
            with open(ARQUIVO_ENVIADOS, 'a') as f:
                f.write(codigo + '\n')

        except Exception as e:
            print(f"[ERRO] Falha ao enviar e-mail para {nome}:", e)
