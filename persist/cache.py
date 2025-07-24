import os
import sqlite3
import psycopg2
from datetime import datetime

# Caminho para armazenar os arquivos SQLite locais
CACHE_DIR = 'persist'

def caminho_cache(usuario_id):
    return os.path.join(CACHE_DIR, f'cache_usuario_{usuario_id}.db')

# -------------------- LEMBRETES ------------------------

def inicializar_cache_sqlite(usuario_id, lembretes):
    os.makedirs(CACHE_DIR, exist_ok=True)
    caminho = caminho_cache(usuario_id)

    conn = sqlite3.connect(caminho)
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS lembretes (
            id INTEGER PRIMARY KEY,
            nome TEXT NOT NULL,
            vencimento TEXT NOT NULL,
            dias_antes INTEGER NOT NULL,
            marcador TEXT NOT NULL,
            modificado BOOLEAN DEFAULT 0
        )
    ''')

    c.execute('DELETE FROM lembretes')  # Limpa qualquer cache antigo

    for l in lembretes:
        c.execute('''INSERT INTO lembretes (id, nome, vencimento, dias_antes, marcador, modificado)
                     VALUES (?, ?, ?, ?, ?, 0)''', l)

    conn.commit()
    conn.close()

def ler_lembretes_cache(usuario_id):
    caminho = caminho_cache(usuario_id)
    if not os.path.exists(caminho):
        return []

    conn = sqlite3.connect(caminho)
    c = conn.cursor()
    c.execute('SELECT id, nome, vencimento, dias_antes, marcador FROM lembretes')
    dados = c.fetchall()
    conn.close()
    return dados

def inserir_lembrete_cache(usuario_id, lembrete):
    caminho = caminho_cache(usuario_id)
    conn = sqlite3.connect(caminho)
    c = conn.cursor()
    c.execute('''INSERT INTO lembretes (id, nome, vencimento, dias_antes, marcador, modificado)
                 VALUES (?, ?, ?, ?, ?, 1)''', lembrete)
    conn.commit()
    conn.close()

def editar_lembrete_cache(usuario_id, lembrete_id, novos_dados):
    caminho = caminho_cache(usuario_id)
    conn = sqlite3.connect(caminho)
    c = conn.cursor()
    c.execute('''UPDATE lembretes
                 SET nome = ?, vencimento = ?, dias_antes = ?, marcador = ?, modificado = 1
                 WHERE id = ?''', (*novos_dados, lembrete_id))
    conn.commit()
    conn.close()

def sincronizar_cache_com_postgre(usuario_id, db_conn_params):
    caminho = caminho_cache(usuario_id)
    if not os.path.exists(caminho):
        return

    sqlite_conn = sqlite3.connect(caminho)
    c_sqlite = sqlite_conn.cursor()
    c_sqlite.execute('SELECT id, nome, vencimento, dias_antes, marcador FROM lembretes WHERE modificado = 1')
    alterados = c_sqlite.fetchall()

    if not alterados:
        sqlite_conn.close()
        os.remove(caminho)
        return

    try:
        pg_conn = psycopg2.connect(**db_conn_params)
        pg_cur = pg_conn.cursor()

        for id_, nome, vencimento, dias_antes, marcador in alterados:
            if id_ > 0:
                pg_cur.execute('''
                    UPDATE licencas
                    SET nome = %s, vencimento = %s, dias_antes = %s, marcador = %s
                    WHERE id = %s AND usuario_id = %s
                ''', (nome, vencimento, dias_antes, marcador, id_, usuario_id))
            else:
                pg_cur.execute('''
                    INSERT INTO licencas (nome, vencimento, dias_antes, usuario_id, marcador)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (nome, vencimento, dias_antes, usuario_id, marcador))

        pg_conn.commit()
        pg_conn.close()
        sqlite_conn.close()
        os.remove(caminho)
    except Exception as e:
        print(f"Erro ao sincronizar com PostgreSQL: {e}")
        sqlite_conn.close()

# -------------------- PLACAS ------------------------

def inserir_placa_cache(placa):
    caminho = caminho_cache('compartilhado')
    conn = sqlite3.connect(caminho)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS placas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placa TEXT NOT NULL UNIQUE
        )
    ''')
    c.execute('INSERT OR IGNORE INTO placas (placa) VALUES (?)', (placa,))
    conn.commit()
    conn.close()

def ler_placas_cache():
    caminho = caminho_cache('compartilhado')
    conn = sqlite3.connect(caminho)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS placas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placa TEXT NOT NULL UNIQUE
        )
    ''')
    c.execute('SELECT placa FROM placas ORDER BY placa')
    placas = [row[0] for row in c.fetchall()]
    conn.close()
    return placas

# -------------------- LOGISTICA ------------------------

def criar_tabela_logistica_sqlite():
    caminho = caminho_cache('compartilhado')
    conn = sqlite3.connect(caminho)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS logistica (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placa TEXT NOT NULL UNIQUE,

            afericao TEXT,
            afericao_modificado INTEGER DEFAULT 0,

            cipp TEXT,
            cipp_modificado INTEGER DEFAULT 0,

            civ TEXT,
            civ_modificado INTEGER DEFAULT 0,

            tacografo TEXT,
            tacografo_modificado INTEGER DEFAULT 0,

            aet_federal TEXT,
            aet_federal_modificado INTEGER DEFAULT 0,

            aet_bahia TEXT,
            aet_bahia_modificado INTEGER DEFAULT 0,

            aet_goias TEXT,
            aet_goias_modificado INTEGER DEFAULT 0,

            aet_alagoas TEXT,
            aet_alagoas_modificado INTEGER DEFAULT 0,

            aet_minas_gerais TEXT,
            aet_minas_gerais_modificado INTEGER DEFAULT 0
        )
    ''')

    conn.commit()
    conn.close()

def ler_logistica_cache():
    caminho = caminho_cache('compartilhado')  # ← usa banco compartilhado
    conn = sqlite3.connect(caminho)
    c = conn.cursor()

    criar_tabela_logistica_sqlite()

    c.execute('SELECT * FROM logistica ORDER BY id')
    dados = c.fetchall()
    colunas = [desc[0] for desc in c.description]
    conn.close()

    resultado = []
    for linha in dados:
        registro = dict(zip(colunas, linha))
        resultado.append(registro)

    return resultado

    conn.commit()
    conn.close()


def salvar_campo_logistica(placa, campo, valor):
    print(f"Salvando campo: {campo=} {valor=} para {placa=}")

    if campo == 'placa':
        print("⛔ Campo 'placa' não deve ser editado individualmente. Ignorando.")
        return

    caminho = caminho_cache('compartilhado')
    conn = sqlite3.connect(caminho)
    c = conn.cursor()

    criar_tabela_logistica_sqlite()

    campo_modificado = f"{campo}_modificado"

    c.execute('SELECT 1 FROM logistica WHERE placa = ?', (placa,))
    existe = c.fetchone()

    if existe:
        c.execute(f'''
            UPDATE logistica
            SET {campo} = ?, {campo_modificado} = 1
            WHERE placa = ?
        ''', (valor, placa))
    else:
        c.execute(f'''
            INSERT INTO logistica (placa, {campo}, {campo_modificado})
            VALUES (?, ?, ?)
        ''', (placa, valor, 1))

    conn.commit()
    conn.close()


