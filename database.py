import sqlite3
import hashlib

DB_NAME = 'estoque.db'

def conectar():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# ---------- Usuários / Autenticação ----------
def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verificar_senha(password: str, password_hash: str) -> bool:
    return _hash_password(password) == password_hash

def obter_usuario(username: str):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("SELECT id, username, password_hash, role, is_active FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "username": row[1], "password_hash": row[2], "role": row[3], "is_active": bool(row[4])}

def criar_usuario(username: str, password: str, role: str = 'visualizador', is_active: bool = True):
    conn = conectar()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username, password_hash, role, is_active) VALUES (?, ?, ?, ?)",
        (username, _hash_password(password), role, 1 if is_active else 0)
    )
    conn.commit()
    conn.close()

def atualizar_usuario(user_id: int, username: str = None, password: str = None, role: str = None, is_active: bool = None):
    conn = conectar()
    cur = conn.cursor()
    sets, params = [], []
    if username is not None:
        sets.append("username = ?"); params.append(username)
    if password is not None:
        sets.append("password_hash = ?"); params.append(_hash_password(password))
    if role is not None:
        sets.append("role = ?"); params.append(role)
    if is_active is not None:
        sets.append("is_active = ?"); params.append(1 if is_active else 0)
    if not sets:
        conn.close(); return
    params.append(user_id)
    cur.execute(f"UPDATE users SET {', '.join(sets)} WHERE id = ?", params)
    conn.commit()
    conn.close()

def deletar_usuario(user_id: int):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

# ---------- Tabelas principais ----------
def criar_tabelas():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS estudos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS localizacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS responsavel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tipo_acao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tipo_produto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estudo_id INTEGER,
            nome TEXT,
            tipo_produto TEXT,
            FOREIGN KEY (estudo_id) REFERENCES estudos (id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS variaveis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT,
            valor TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movimentacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            tipo_transacao TEXT,
            estudo_id INTEGER,
            produto_id INTEGER,
            tipo_produto TEXT,
            quantidade INTEGER,
            validade TEXT,
            lote TEXT,
            nota TEXT,
            tipo_acao TEXT,
            consideracoes TEXT,
            responsavel TEXT,
            localizacao TEXT,
            FOREIGN KEY (estudo_id) REFERENCES estudos (id),
            FOREIGN KEY (produto_id) REFERENCES produtos (id)
        )
    ''')

    # ---------- NOVA: tabela de usuários ----------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('gestor','visualizador')),
            is_active INTEGER NOT NULL DEFAULT 1
        )
    ''')

    # Admin padrão se a tabela estiver vazia
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO users (username, password_hash, role, is_active) VALUES (?, ?, 'gestor', 1)",
            ('admin', _hash_password('admin'))
        )

    conn.commit()
    conn.close()
