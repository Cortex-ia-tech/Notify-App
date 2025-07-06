import smtplib
import sqlite3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import os

# Configurações
remetente = "leonardomoreira@petroserra.com"
senha_app = "obdf ilkz cpcj hbfn"
destinatario = "leonardomoreira@petroserra.com"

hoje = datetime.now().date()

# Arquivo persistente com os códigos dos e-mails enviados
ARQUIVO_ENVIADOS = 'emails_enviados.txt'

# Garante que o arquivo existe
if not os.path.exists(ARQUIVO_ENVIADOS):
    with open(ARQUIVO_ENVIADOS, 'w') as f:
        pass  # cria o arquivo vazio

# Lê os códigos já enviados
with open(ARQUIVO_ENVIADOS, 'r') as f:
    codigos_enviados = set(linha.strip() for linha in f.readlines())

# Conecta ao banco de dados
conn = sqlite3.connect('database.db')
c = conn.cursor()

# Garante que a tabela existe (evita erro se rodar isoladamente)
c.execute('''
    CREATE TABLE IF NOT EXISTS licencas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        vencimento DATE NOT NULL,
        dias_antes INTEGER NOT NULL
    )
''')
conn.commit()

# Busca todas as licenças
c.execute('SELECT id, nome, vencimento, dias_antes FROM licencas')
licencas = c.fetchall()

# Verifica e envia e-mails
for id_, nome, vencimento, dias_antes in licencas:
    try:
        data_venc = datetime.strptime(vencimento, '%Y-%m-%d').date()
        data_alerta = data_venc - timedelta(days=int(dias_antes))

        if data_alerta <= hoje <= data_venc:
            # Código único com base no ID da licença + data atual
            codigo = f"{int(id_):03d}{hoje.strftime('%d%m%Y')}"

            if codigo in codigos_enviados:
                print(f"[SKIP] Já enviado hoje: {codigo} ({nome})")
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

            # Envia o e-mail
            servidor = smtplib.SMTP("smtp.gmail.com", 587)
            servidor.starttls()
            servidor.login(remetente, senha_app)
            servidor.sendmail(remetente, destinatario, mensagem.as_string())
            servidor.quit()

            print(f"[OK] E-mail enviado para licença: {nome}")

            # Registra o código no arquivo
            with open(ARQUIVO_ENVIADOS, 'a') as f:
                f.write(codigo + '\n')

    except Exception as e:
        print(f"[ERRO] Erro ao processar licença {nome}:", e)

conn.close()
