import smtplib
import sqlite3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

# Dados do remetente
remetente = "leonardomoreira@petroserra.com"
senha_app = "obdf ilkz cpcj hbfn"
destinatario = "leonardomoreira@petroserra.com"

# Conectar ao banco
conn = sqlite3.connect('database.db')
c = conn.cursor()
c.execute('SELECT nome, vencimento, dias_antes FROM licencas')
licencas = c.fetchall()
conn.close()

hoje = datetime.now().date()

for nome, vencimento, dias_antes in licencas:
    data_venc = datetime.strptime(vencimento, '%Y-%m-%d').date()
    data_alerta = data_venc - timedelta(days=int(dias_antes))

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
            print(f"E-mail enviado para licença: {nome}")
        except Exception as e:
            print(f"Erro ao enviar e-mail para {nome}:", e)
