import streamlit as st
import pandas as pd
from database import conectar, criar_usuario, atualizar_usuario, deletar_usuario

st.set_page_config(page_title="Gestão de Acessos", layout="wide")
st.title("🔐 Gestão de Acessos")

# Gatekeeper
user = st.session_state.get('user')
if not user:
    st.error("Faça login para continuar."); st.stop()
if user['role'] != 'gestor':
    st.error("Acesso restrito a gestores."); st.stop()

conn = conectar()

st.subheader("Usuários cadastrados")
df = pd.read_sql("SELECT id, username, role, is_active FROM users ORDER BY username", conn)
st.dataframe(df, use_container_width=True)

st.divider()
st.subheader("➕ Criar novo usuário")
col1, col2, col3 = st.columns([2,2,2])
with col1:
    novo_user = st.text_input("Usuário *")
with col2:
    novo_pass = st.text_input("Senha *", type="password")
with col3:
    novo_role = st.selectbox("Perfil *", ["visualizador", "gestor"], index=0)

if st.button("Criar usuário", type="primary"):
    if not novo_user or not novo_pass:
        st.warning("Informe usuário e senha.")
    else:
        try:
            criar_usuario(novo_user, novo_pass, novo_role, True)
            st.success("Usuário criado.")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao criar: {e}")

st.divider()
st.subheader("✏️ Editar usuário")
if not df.empty:
    sel = st.selectbox("Selecione o ID", df['id'].tolist())
    registro = df[df['id']==sel].iloc[0]
    e_user = st.text_input("Usuário", registro['username'])
    e_role = st.selectbox("Perfil", ["visualizador","gestor"], index=0 if registro['role']=="visualizador" else 1)
    e_active = st.checkbox("Ativo", bool(registro['is_active']))
    e_pass = st.text_input("Nova senha (opcional)", type="password", help="Deixe em branco para manter a atual")

    colA, colB = st.columns(2)
    if colA.button("Salvar alterações", type="primary"):
        try:
            atualizar_usuario(sel,
                              username=e_user if e_user != registro['username'] else None,
                              password=e_pass if e_pass else None,
                              role=e_role if e_role != registro['role'] else None,
                              is_active=e_active if e_active != bool(registro['is_active']) else None)
            st.success("Usuário atualizado.")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao atualizar: {e}")

    if colB.button("Excluir usuário", type="secondary"):
        if registro['username'] == 'admin':
            st.warning("Não é permitido excluir o admin padrão.")
        else:
            deletar_usuario(sel)
            st.success("Usuário excluído.")
            st.rerun()

conn.close()
