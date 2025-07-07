import smtplib
import psycopg2
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

# Configuração do horário fixo (ex: 08h00)
HORA_ALVO = (13, 00)

# Conexão com o banco PostgreSQL Supabase
conn_params = {
    "host": "aws-0-sa-east-1.pooler.supabase.com",
    "database": "postgres",
    "user": "postgres.yqwohzkwllelxptcysmn",
    "password": "Slmg300803$",
    "port": "6543"
}

# Configurações de e-mail
remetente = "leonardomoreira@petroserra.com"
senha_app = "obdf ilkz cpcj hbfn"
destinatario = "leonardomoreira@petroserra.com"

# Verifica se é exatamente o horário definido
agora = datetime.now()
if (agora.hour, agora.minute, agora.second) != HORA_ALVO:
    print(f"Horário atual: {agora.strftime('%H:%M:%S')}. E-mails só são enviados exatamente às {HORA_ALVO[0]:02d}:{HORA_ALVO[1]:02d}:{HORA_ALVO[2]:02d}.")
    exit()

# Caminho do arquivo persistente
ARQUIVO_ENVIADOS = 'persist/emails_enviados.txt'
os.makedirs(os.path.dirname(ARQUIVO_ENVIADOS), exist_ok=True)

# Garante que o arquivo exista
if not os.path.exists(ARQUIVO_ENVIADOS):
    open(ARQUIVO_ENVIADOS, 'w').close()

# Lê os códigos já enviados
with open(ARQUIVO_ENVIADOS, 'r') as f:
    codigos_enviados = set(linha.strip() for linha in f)

# Conecta ao banco
conn = psycopg2.connect(**conn_params)
c = conn.cursor()
c.execute("SELECT id, nome, vencimento, dias_antes FROM licencas")
licencas = c.fetchall()

# Verifica cada licença
hoje = agora.date()
hora = f"{agora.hour:02d}"

for id_, nome, vencimento, dias_antes in licencas:
    data_venc = datetime.strptime(vencimento, '%Y-%m-%d').date()
    data_alerta = data_venc - timedelta(days=int(dias_antes))

    if data_alerta <= hoje <= data_venc:
        codigo = f"{int(id_):03d}{hoje.strftime('%d%m%Y')}{hora}"

        if codigo in codigos_enviados:
            print(f"[SKIP] Já enviado hoje às {hora} para: {nome}")
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

            # Registra o código
            with open(ARQUIVO_ENVIADOS, 'a') as f:
                f.write(codigo + '\n')

        except Exception as e:
            print(f"[ERRO] Falha ao enviar e-mail para {nome}: {e}")

conn.close()
