import streamlit as st
import pandas as pd
import time
# Importa as novas funções do database.py
from database import get_data, insert_data, delete_data

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

# Não precisamos mais de 'conn' e 'cursor' do SQLite.

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
            # Substitui a chamada cursor.execute() por insert_data()
            insert_data(tabela, {"nome": valor.strip()})
            st.success(f"{tipo} adicionado com sucesso!", icon="✅")
            time.sleep(1.5)
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao adicionar: {e}")

st.divider()

st.subheader(f"{tipo}s Cadastrados")
tabela = tabela_por_tipo[tipo]
try:
    # Substitui pd.read_sql() por get_data()
    df = pd.DataFrame(get_data(tabela, "id, nome"))
    
    if not df.empty:
        df = df.sort_values(by='id')

    st.dataframe(df, width='stretch', hide_index=True)

    if not df.empty:
        st.markdown("### Excluir item")
        # col1, col2 = st.columns([2, 1])
        # with col1:
        id_excluir = st.selectbox("Selecione o ID para excluir", df["id"].tolist())
        # with col2:
        if st.button("Excluir", type="secondary"):
            try:
                # Substitui a chamada cursor.execute() por delete_data()
                delete_data(tabela, "id", int(id_excluir))
                st.success("Excluído com sucesso.", icon="🗑️")
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao excluir: {e}")
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")