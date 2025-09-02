import streamlit as st
from database import criar_tabelas, obter_usuario, verificar_senha
#from database_local import criar_tabelas, obter_usuario, verificar_senha

st.set_page_config(page_title="Controle de Estoque", page_icon="🧪", layout="wide")

st.title("🧪 Controle de Estoque de Farmácia")
st.markdown("""
Este aplicativo permite gerenciar entradas, saídas e controle de produtos de forma local.

Perfis:
- **Gestor**: acesso total (inclui Gestão de Acessos).
- **Visualizador**: apenas **Visão Geral**.
""")

with st.sidebar:
    st.image("logo.png", use_container_width=True)
    st.write("")  # pequeno espaçamento




# --- Sidebar: Login / Logout ---
with st.sidebar:
    st.header("Acesso")
    if 'user' not in st.session_state:
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        if st.button("Entrar", width='stretch'):
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
        if st.button("Sair", width='stretch'):
            st.session_state.pop('user', None)
            st.rerun()
