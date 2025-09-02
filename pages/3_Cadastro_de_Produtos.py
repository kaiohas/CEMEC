import streamlit as st
import pandas as pd
import time
from database import get_data, insert_data, delete_data

st.set_page_config(page_title="Cadastro de Produtos", layout="wide")
st.title("📦 Cadastro de Produtos")

# --- Gatekeeper: somente gestor ---
user = st.session_state.get('user')
if not user:
    st.error("Faça login para continuar.")
    st.stop()
if user['role'] != 'gestor':
    st.error("Acesso restrito a gestores.")
    st.stop()

try:
    # Carregar dimensões do Supabase
    df_estudos = pd.DataFrame(get_data("estudos", "id, nome"))
    df_tipos   = pd.DataFrame(get_data("tipo_produto", "id, nome"))

    if not df_estudos.empty:
        df_estudos = df_estudos.sort_values(by='nome')
    if not df_tipos.empty:
        df_tipos = df_tipos.sort_values(by='nome')

    st.subheader("➕ Cadastrar novo produto")
    c1, c2, c3 = st.columns([2, 3, 2])
    with c1:
        estudo_nome = st.selectbox("Estudo", df_estudos["nome"] if not df_estudos.empty else [])
    with c2:
        produto_nome = st.text_input("Nome do Produto")
    with c3:
        tipo_produto = st.selectbox("Tipo de Produto", df_tipos["nome"] if not df_tipos.empty else [])

    if st.button("Adicionar produto", type="primary"):
        if not estudo_nome or not produto_nome.strip() or not tipo_produto:
            st.warning("Preencha Estudo, Nome do Produto e Tipo de Produto.")
        else:
            try:
                estudo_id = int(df_estudos.loc[df_estudos["nome"] == estudo_nome, "id"].values[0])
                
                insert_data("produtos", {
                    "estudo_id": estudo_id, 
                    "nome": produto_nome.strip(), 
                    "tipo_produto": tipo_produto
                })
                st.success("Produto cadastrado com sucesso!", icon="✅")
                time.sleep(1.5)
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao cadastrar: {e}")

    st.divider()

    st.subheader("📋 Produtos cadastrados")
    
    df_prod = pd.DataFrame(get_data("produtos", "id, estudo_id, nome, tipo_produto"))
    df_estudos_base = pd.DataFrame(get_data("estudos", "id, nome"))
    if not df_prod.empty and not df_estudos_base.empty:
        df_prod = pd.merge(df_prod, df_estudos_base, left_on='estudo_id', right_on='id', how='left', suffixes=('_prod', '_est'))
        df_prod.rename(columns={'nome_prod': 'produto', 'nome_est': 'estudo','id_prod': 'id'}, inplace=True)
        df_prod = df_prod[['id', 'produto', 'tipo_produto', 'estudo', 'estudo_id']]

    if df_prod.empty:
        st.info("Nenhum produto cadastrado ainda.")
    else:
        f1, f2 = st.columns([2, 3])
        with f1:
            filtro_estudo = st.selectbox(
                "Filtrar por Estudo",
                ["(Todos)"] + sorted(df_prod["estudo"].dropna().unique().tolist()),
                index=0,
            )
        with f2:
            filtro_busca = st.text_input("Buscar por Nome do Produto")

        df_view = df_prod.copy()
        if filtro_estudo != "(Todos)":
            df_view = df_view[df_view["estudo"] == filtro_estudo]
        if filtro_busca.strip():
            termo = filtro_busca.strip().lower()
            df_view = df_view[df_view["produto"].str.lower().str.contains(termo)]

        if df_view.empty:
            st.info("Nenhum produto encontrado com os filtros selecionados.")
            st.stop()

        st.dataframe(df_view, width='stretch')

        st.markdown("### 🗑️ Excluir produto")
        
        # --- CORREÇÃO AQUI: Garante que o selectbox só aparece se houver dados ---
        opcoes = []
        map_rotulo_id = {}
        if not df_view.empty:
            for index, row in df_view.iterrows():
                rotulo = f"[{row['id']}] {row['produto']} — {row['estudo']}"
                opcoes.append(rotulo)
                map_rotulo_id[rotulo] = int(row['id'])

            sel_rotulo = st.selectbox("Selecione o produto", opcoes)
            sel_id = map_rotulo_id[sel_rotulo]

            df_movs = pd.DataFrame(get_data("movimentacoes", "id, produto_id"))
            
            qtd_movs = 0
            if not df_movs.empty:
                qtd_movs = len(df_movs[df_movs['produto_id'] == sel_id])

            if qtd_movs > 0:
                st.warning(f"Este produto possui **{qtd_movs} lançamento(s)** vinculado(s). "
                           "Para manter a integridade dos dados, exclua os lançamentos primeiro em **📜 Lançamentos**.")
                st.button("Excluir produto", disabled=True)
            else:
                if st.button("Excluir produto", type="secondary"):
                    try:
                        delete_data("produtos", "id", sel_id)
                        st.success("Produto excluído com sucesso.", icon="🗑️")
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao excluir: {e}")
        else:
            st.caption("Nenhum item para excluir com os filtros atuais.")
            
except Exception as e:
    st.error(f"Erro geral: {e}")