import os
import sqlite3
import psycopg2
from datetime import datetime

# Caminho para armazenar os arquivos SQLite locais
CACHE_DIR = 'persist'

def caminho_cache(usuario_id):
    return os.path.join(CACHE_DIR, f'cache_usuario_{usuario_id}.db')

def inicializar_cache_sqlite(usuario_id, lembretes):
    """Cria o banco SQLite local para o usuário e popula com os lembretes vindos do PostgreSQL."""
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
            modificado BOOLEAN DEFAULT 0 -- indica se precisa ser sincronizado
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
        os.remove(caminho)  # Nenhuma alteração, apaga direto
        return

    try:
        pg_conn = psycopg2.connect(**db_conn_params)
        pg_cur = pg_conn.cursor()
        for id_, nome, vencimento, dias_antes, marcador in alterados:
            pg_cur.execute('''
                UPDATE licencas SET nome = %s, vencimento = %s, dias_antes = %s, marcador = %s
                WHERE id = %s AND usuario_id = %s
            ''', (nome, vencimento, dias_antes, marcador, id_, usuario_id))
        pg_conn.commit()
        pg_conn.close()
        sqlite_conn.close()
        os.remove(caminho)  # Só apaga se deu tudo certo
    except Exception as e:
        print(f"Erro ao sincronizar com PostgreSQL: {e}")
        sqlite_conn.close()  # Mantém o cache para tentar depois
