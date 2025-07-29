import psycopg2
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES DO BANCO DE DADOS ---
DB_CONFIG = {
    "host": "aws-0-sa-east-1.pooler.supabase.com",
    "port": 6543,
    "dbname": "postgres",
    "user": "postgres.yqwohzkwllelxptcysmn",
    "password": "2GJJMcsVVP1BPKKK",
}

# --- CONFIGURAÇÕES DO E-MAIL ---
EMAIL_REMETENTE = "leonardomoreira@petroserra.com"
EMAIL_SENHA_APP = "obdf ilkz cpcj hbfn"
EMAIL_DESTINATARIO = "leonardomoreira@petroserra.com"

# --- CAMPOS DE DOCUMENTOS E NOMES FORMATADOS ---
CAMPOS_DOCUMENTOS = {
    'aetfederal': 'AET FEDERAL',
    'aetbahia': 'AET BAHIA',
    'aetgoias': 'AET GOIÁS',
    'aetalagoas': 'AET ALAGOAS',
    'aetminasgerais': 'AET MINAS GERAIS',
    'afericao': 'AFERIÇÃO',
    'cipp': 'CIPP',
    'civ': 'CIV',
    'tacografo': 'TACÓGRAFO'
}

# --- FUNÇÃO PARA ENVIAR E-MAIL ---
def enviar_email(documento, placa, dias, data_vencimento):
    data_formatada = data_vencimento.strftime('%d/%m/%Y')
    hoje = datetime.today().date().strftime('%d/%m/%Y')

    if dias in [30, 15]:
        assunto = f"Lembrete 🗖 {documento} – {placa} - Vence em {dias} dias."
        corpo = f"""
Olá,

Faltam {dias} dias para o vencimento do documento {documento} do veículo {placa} (vence em {data_formatada}).

Você optou por ser avisado(a) com {dias} dias de antecedência.

Acesse o Notify para atualizar suas preferências.

-- 
Notify | Uma criação Cortex-ia Business Intelligence®
"""
    elif dias == 0:
        assunto = f"Lembrete 🗖 {documento} – {placa} - Vencendo HOJE, ({hoje})."
        corpo = f"""
Olá,

O documento {documento} do veículo {placa} está vencendo HOJE.

Você optou por ser avisado(a) com 0 dias de antecedência.

Acesse o Notify para atualizar suas preferências.

-- 
Notify | Uma criação Cortex-ia Business Intelligence®
"""
    elif dias == -1:
        assunto = f"Lembrete 🗖 {documento} – {placa} - VENCIDO."
        corpo = f"""
Olá,

O documento {documento} do veículo {placa} está VENCIDO (venceu ontem, {data_formatada}).

Você optou por ser avisado(a) com -1 dias de antecedência.

Acesse o Notify para atualizar suas preferências.

-- 
Notify | Uma criação Cortex-ia Business Intelligence®
"""
    else:
        return  # Não envia se não for um dos dias desejados

    msg = MIMEMultipart()
    msg['From'] = EMAIL_REMETENTE
    msg['To'] = EMAIL_DESTINATARIO
    msg['Subject'] = assunto
    msg.attach(MIMEText(corpo, 'plain'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as servidor:
            servidor.starttls()
            servidor.login(EMAIL_REMETENTE, EMAIL_SENHA_APP)
            servidor.send_message(msg)
            print(f"✅ Email enviado: {documento} – {placa} – {dias} dias")
    except Exception as e:
        print(f"❌ Erro ao enviar email: {e}")

# --- CONVERSOR DE DATA ---
def str_para_data(data_str):
    try:
        return datetime.strptime(data_str, "%d/%m/%Y").date()
    except:
        return None

# --- EXECUÇÃO PRINCIPAL ---
def verificar_vencimentos():
    hoje = datetime.today().date()
    dias_alvo = [30, 15, 0, -1]

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT placa, " + ", ".join(CAMPOS_DOCUMENTOS.keys()) + " FROM logistica")
        linhas = cur.fetchall()

        for linha in linhas:
            placa = linha[0]
            for idx, campo in enumerate(CAMPOS_DOCUMENTOS.keys(), start=1):
                valor = linha[idx]
                data = str_para_data(valor) if valor else None
                if data:
                    dias_restantes = (data - hoje).days
                    if dias_restantes in dias_alvo:
                        enviar_email(CAMPOS_DOCUMENTOS[campo], placa, dias_restantes, data)

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Erro ao acessar banco de dados: {e}")

if __name__ == "__main__":
    verificar_vencimentos()
