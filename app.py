import streamlit as st
from database import criar_tabelas, obter_usuario, verificar_senha

st.set_page_config(page_title="Controle de Estoque", page_icon="🧪", layout="wide")

with st.sidebar:
    st.image("assets/logo.png", use_container_width=True)
    st.write("")  # pequeno espaçamento


st.title("🧪 Controle de Estoque de Farmácia")
st.markdown("""
Este aplicativo permite gerenciar entradas, saídas e controle de produtos de forma local.


Perfis:
- **Gestor**: acesso total (inclui Gestão de Acessos).
- **Visualizador**: apenas **Visão Geral**.
""")

# Garante que todas as tabelas existam (inclui users e admin/admin)
criar_tabelas()

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
        st.caption("Primeiro acesso: **admin / admin**")
    else:
        st.success(f"Logado como: **{st.session_state['user']['username']}** ({st.session_state['user']['role']})")
        if st.button("Sair", use_container_width=True):
            st.session_state.pop('user', None)
            st.rerun()




