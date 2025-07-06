import smtplib
import sqlite3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

# Configurações
remetente = "leonardomoreira@petroserra.com"
senha_app = "obdf ilkz cpcj hbfn"
destinatario = "leonardomoreira@petroserra.com"

hoje = datetime.now().date()

# Conecta ao banco
conn = sqlite3.connect('database.db')
c = conn.cursor()

# Garante que a coluna 'ultimo_envio' existe
c.execute("PRAGMA table_info(licencas)")
colunas = [linha[1] for linha in c.fetchall()]
if "ultimo_envio" not in colunas:
    c.execute("ALTER TABLE licencas ADD COLUMN ultimo_envio DATE")

# Busca todas as licenças
c.execute('SELECT id, nome, vencimento, dias_antes, ultimo_envio FROM licencas')
licencas = c.fetchall()

for id_, nome, vencimento, dias_antes, ultimo_envio in licencas:
    data_venc = datetime.strptime(vencimento, '%Y-%m-%d').date()
    data_alerta = data_venc - timedelta(days=int(dias_antes))

    # Converte ultimo_envio para date se não for None
    if ultimo_envio:
        ultimo_envio_date = datetime.strptime(ultimo_envio, '%Y-%m-%d').date()
    else:
        ultimo_envio_date = None

    # Verifica se deve enviar hoje
    if data_alerta <= hoje <= data_venc:
        if ultimo_envio_date == hoje:
            print(f"E-mail já foi enviado hoje para: {nome}")
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
            print(f"E-mail enviado para licença: {nome}")

            # Atualiza o campo ultimo_envio no banco
            c.execute("UPDATE licencas SET ultimo_envio = ? WHERE id = ?", (str(hoje), id_))
            conn.commit()

        except Exception as e:
            print(f"Erro ao enviar e-mail para {nome}: {e}")

conn.close()
