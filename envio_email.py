import smtplib
import psycopg2
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import os

# Configurações de e-mail
remetente = "leonardomoreira@petroserra.com"
senha_app = "obdf ilkz cpcj hbfn"
destinatario = "leonardomoreira@petroserra.com"
hoje = datetime.now().date()

# Arquivo persistente para registrar envios
ARQUIVO_ENVIADOS = 'persist/emails_enviados.txt'

# Garante que o arquivo existe
if not os.path.exists(ARQUIVO_ENVIADOS):
    with open(ARQUIVO_ENVIADOS, 'w') as f:
        pass  # cria o arquivo vazio

# Lê os códigos já enviados
with open(ARQUIVO_ENVIADOS, 'r') as f:
    codigos_enviados = set(linha.strip() for linha in f.readlines())

# Conecta ao banco PostgreSQL (use sua string de conexão real aqui)
conn_params = {
    "host": "db.yqwohzkwllelxptcysmn.supabase.co",
    "database": "postgres",
    "user": "postgres",
    "password": "Slmg300803$",
    "sslmode": "require"
}

conn = psycopg2.connect(**conn_params)
c = conn.cursor()
c.execute('SELECT id, nome, vencimento, dias_antes FROM licencas')
licencas = c.fetchall()

for id_, nome, vencimento, dias_antes in licencas:
    data_venc = vencimento  # no PostgreSQL a data já vem no formato certo
    data_alerta = data_venc - timedelta(days=int(dias_antes))

    if data_alerta <= hoje <= data_venc:
        codigo = f"{int(id_):03d}{hoje.strftime('%d%m%Y')}"

        if codigo in codigos_enviados:
            print(f"[SKIP] E-mail já enviado hoje para: {nome}")
            continue

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

            # Salva o código no arquivo
            with open(ARQUIVO_ENVIADOS, 'a') as f:
                f.write(codigo + '\n')

        except Exception as e:
            print(f"[ERRO] Falha ao enviar e-mail para {nome}:", e)

conn.close()
