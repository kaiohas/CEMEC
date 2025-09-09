import streamlit as st
from database import criar_tabelas, obter_usuario, verificar_senha, get_data, criar_usuario
# from database_local import criar_tabelas, obter_usuario, verificar_senha

st.set_page_config(page_title="Controle de Estoque", page_icon="🧪", layout="wide")

st.title("🧪 Controle de Estoque de Farmácia")
st.markdown("""
Este aplicativo permite gerenciar entradas, saídas e controle de produtos de forma local.

Perfis:
- **Gestor**: acesso total (inclui Gestão de Acessos).
- **Visualizador**: apenas **Visão Geral**.
""")

# --- Bootstrap: cria admin se tabela 'users' estiver vazia ---
if 'bootstrap_done' not in st.session_state:
    try:
        users_sample = get_data("users", "id", limit=1)
        if not users_sample:
            criar_usuario("admin", "admin", "gestor", True)
            st.toast("🔑 Usuário admin criado (login: admin / senha: admin). Altere a senha em **Gestão de Acessos**.", icon="✅")
    except Exception:
        # Ambiente sem Supabase configurado não deve travar a app
        pass
    st.session_state['bootstrap_done'] = True

with st.sidebar:
    st.image("logo.png", use_container_width=True)
    st.write("")  # pequeno espaçamento

# --- Sidebar: Login / Logout ---
with st.sidebar:
    st.header("Acesso")
    if 'user' not in st.session_state:
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        if st.button("Entrar", use_container_width=True):
            u = obter_usuario(username)
            if not u or not u["is_active"] or not verificar_senha(password, u["password_hash"]):
                st.error("Usuário ou senha inválidos.")
            else:
                st.session_state['user'] = {"id": u["id"], "username": u["username"], "role": u["role"]}
                st.success(f"Bem-vindo, {u['username']} ({u['role']}).")
                st.rerun()
        st.caption("Caso não possua acesso, procurar Helga ou Everson.")
    else:
        st.success(f"Logado como: **{st.session_state['user']['username']}** ({st.session_state['user']['role']})")
        if st.button("Sair", use_container_width=True):
            st.session_state.pop('user', None)
            st.rerun()
    