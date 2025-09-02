# supabase_db.py
import hashlib
import streamlit as st
from supabase import create_client, Client
from dotenv import load_dotenv
import os

# Carrega as variáveis de ambiente do arquivo .env
# Isso é para o desenvolvimento local, para não expor as chaves.
# No Hugging Face Spaces, as chaves serão carregadas como secrets.
load_dotenv()

# --- Configuração da Conexão com o Supabase ---
# Usamos st.secrets para carregar as chaves de forma segura,
# tanto localmente (via secrets.toml) quanto na nuvem.
@st.cache_resource
def init_connection():
    # Lê as variáveis de ambiente diretamente do Render
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    return create_client(url, key)

supabase: Client = init_connection()

# --- Helpers de Autenticação (adaptados) ---
def _hash_password(password: str) -> str:
    # A função de hash pode ser mantida, mas a do Supabase é mais robusta.
    # Para simplicidade, vamos usar a mesma para não precisar refazer o hash de todos os usuários.
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verificar_senha(password: str, password_hash: str) -> bool:
    return _hash_password(password) == password_hash

def obter_usuario(username: str):
    response = supabase.table("users").select("*").eq("username", username).limit(1).execute()
    if not response.data:
        return None
    user = response.data[0]
    return {
        "id": user.get("id"),
        "username": user.get("username"),
        "password_hash": user.get("password_hash"),
        "role": user.get("role"),
        "is_active": user.get("is_active")
    }

def criar_usuario(username: str, password: str, role: str = 'visualizador', is_active: bool = True):
    data, count = supabase.table("users").insert({
        "username": username,
        "password_hash": _hash_password(password),
        "role": role,
        "is_active": is_active
    }).execute()
    return data

def atualizar_usuario(user_id: int, username: str = None, password: str = None, role: str = None, is_active: bool = None):
    update_data = {}
    if username is not None:
        update_data["username"] = username
    if password is not None:
        update_data["password_hash"] = _hash_password(password)
    if role is not None:
        update_data["role"] = role
    if is_active is not None:
        update_data["is_active"] = is_active
    
    if update_data:
        supabase.table("users").update(update_data).eq("id", user_id).execute()

def deletar_usuario(user_id: int):
    supabase.table("users").delete().eq("id", user_id).execute()

# --- Funções de Consulta de Dados (adaptadas) ---

def get_data(table_name, select_cols="*", limit=50000):
    """Busca dados de uma tabela no Supabase com um limite opcional."""
    response = supabase.table(table_name).select(select_cols).limit(limit).execute()
    return response.data

def insert_data(table_name, data):
    response = supabase.table(table_name).insert(data).execute()
    return response.data

def update_data(table_name, data, eq_col, eq_val):
    response = supabase.table(table_name).update(data).eq(eq_col, eq_val).execute()
    return response.data

def delete_data(table_name, eq_col, eq_val):
    response = supabase.table(table_name).delete().eq(eq_col, eq_val).execute()

    return response.data
