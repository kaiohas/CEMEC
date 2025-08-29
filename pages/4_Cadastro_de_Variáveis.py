import streamlit as st
import pandas as pd
from database import conectar  # usa a conexão centralizada

st.set_page_config(page_title="Cadastro de Variáveis", layout="wide")
st.title("🗂️ Cadastro de Variáveis")

# --- Gatekeeper: somente gestor ---
user = st.session_state.get('user')
if not user:
    st.error("Faça login para continuar.")
    st.stop()
if user['role'] != 'gestor':
    st.error("Acesso restrito a gestores.")
    st.stop()

conn = conectar()
cursor = conn.cursor()

tabela_por_tipo = {
    "Localização": "localizacao",
    "Tipo de Ação": "tipo_acao",
    "Estudo": "estudos",
    "Tipo de Produto": "tipo_produto",
}
variaveis_tipos = list(tabela_por_tipo.keys())

colsel, colval = st.columns([1, 2])
with colsel:
    tipo = st.selectbox("Tipo de Variável", variaveis_tipos)
with colval:
    valor = st.text_input("Valor (novo)")

if st.button("Adicionar", type="primary"):
    if not valor.strip():
        st.warning("Informe um valor.")
    else:
        tabela = tabela_por_tipo[tipo]
        try:
            cursor.execute(f"INSERT INTO {tabela} (nome) VALUES (?)", (valor.strip(),))
            conn.commit()
            st.toast(f"{tipo} adicionado com sucesso!", icon="✅")
            st.rerun()  # <-- substitui experimental_rerun
        except Exception as e:
            st.error(f"Erro ao adicionar: {e}")

st.divider()

st.subheader(f"{tipo}s Cadastrados")
tabela = tabela_por_tipo[tipo]
try:
    df = pd.read_sql(f"SELECT * FROM {tabela} ORDER BY nome", conn)
    st.dataframe(df, use_container_width=True)

    if not df.empty:
        st.markdown("### Excluir item")
        col1, col2 = st.columns([2, 1])
        with col1:
            id_excluir = st.selectbox("Selecione o ID para excluir", df["id"].tolist())
        with col2:
            if st.button("Excluir", type="secondary"):
                try:
                    cursor.execute(f"DELETE FROM {tabela} WHERE id = ?", (int(id_excluir),))
                    conn.commit()
                    st.toast("Excluído com sucesso.", icon="🗑️")
                    st.rerun()  # <-- substitui experimental_rerun
                except Exception as e:
                    st.error(f"Erro ao excluir: {e}")
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")

conn.close()
