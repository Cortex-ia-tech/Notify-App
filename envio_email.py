import smtplib
import sqlite3
import os
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ========= CONFIGURAÇÕES =========
remetente = "leonardomoreira@petroserra.com"
senha_app = "obdf ilkz cpcj hbfn"
destinatario = "leonardomoreira@petroserra.com"
CAMINHO_CONTROLE = "/tmp/emails_enviados.txt"

# ========= FUNÇÃO PARA GERAR O CÓDIGO =========
def gerar_codigo_envio(id_licenca):
    hoje = datetime.now()
    lll = str(id_licenca).zfill(3)
    dd = str(hoje.day).zfill(2)
    mm = str(hoje.month).zfill(2)
    yyyy = str(hoje.year)
    return f"{lll}{dd}{mm}{yyyy}"

# ========= GARANTE QUE O ARQUIVO EXISTA =========
if not os.path.exists(CAMINHO_CONTROLE):
    with open(CAMINHO_CONTROLE, "w") as f:
        pass

# ========= LÊ OS CÓDIGOS JÁ ENVIADOS =========
with open(CAMINHO_CONTROLE, "r") as f:
    codigos_enviados = set(f.read().splitlines())

# ========= CONEXÃO COM O BANCO =========
conn = sqlite3.connect('database.db')
c = conn.cursor()
c.execute('SELECT id, nome, vencimento, dias_antes FROM licencas')
licencas = c.fetchall()

hoje = datetime.now().date()

for id_, nome, vencimento, dias_antes in licencas:
    data_venc = datetime.strptime(vencimento, '%Y-%m-%d').date()
    data_alerta = data_venc - timedelta(days=int(dias_antes))

    # Gera o código de controle
    codigo_envio = gerar_codigo_envio(id_)

    # Verifica se já foi enviado
    if codigo_envio in codigos_enviados:
        print(f"⚠️ E-mail já enviado hoje para: {nome} ({codigo_envio})")
        continue

    # Se estiver no período de alerta, envia
    if data_alerta <= hoje <= data_venc:
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

            print(f"✅ E-mail enviado para: {nome} ({codigo_envio})")

            # Registra o código como já enviado
            with open(CAMINHO_CONTROLE, "a") as f:
                f.write(codigo_envio + "\n")

        except Exception as e:
            print(f"❌ Erro ao enviar e-mail para {nome}:", e)

conn.close()
