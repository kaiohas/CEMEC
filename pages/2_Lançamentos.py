import streamlit as st
import pandas as pd
from datetime import date
import time
from database import get_data, update_data, delete_data

st.set_page_config(page_title="Lançamentos", layout="wide")
st.title("📜 Lançamentos Realizados")

# Gatekeeper
user = st.session_state.get('user')
if not user:
    st.error("Faça login para continuar."); st.stop()
if user['role'] != 'gestor':
    st.error("Acesso restrito a gestores."); st.stop()

# --- Carregar dados do Supabase e fazer as junções com Pandas ---
try:
    df_movs = pd.DataFrame(get_data("movimentacoes", "*"))
    df_estudos = pd.DataFrame(get_data("estudos", "id, nome"))
    df_produtos = pd.DataFrame(get_data("produtos", "id, nome"))

    if df_movs.empty:
        st.warning("Nenhum lançamento encontrado.")
        st.stop()
        
    # Fazer as junções usando pd.merge
    df = pd.merge(df_movs, df_estudos, left_on='estudo_id', right_on='id', how='left', suffixes=('', '_est'))
    df.rename(columns={'nome': 'estudo'}, inplace=True)
    
    df = pd.merge(df, df_produtos, left_on='produto_id', right_on='id', how='left', suffixes=('', '_prod'))
    df.rename(columns={'nome': 'produto'}, inplace=True)
    
    # Selecionar as colunas finais
    df = df[['id', 'data', 'tipo_transacao', 'estudo', 'produto', 'tipo_produto',
             'quantidade', 'validade', 'lote', 'nota', 'tipo_acao', 'consideracoes',
             'responsavel', 'localizacao']]
    df = df.sort_values(by='id', ascending=True)
    
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}"); st.stop()

# =========================
# Bloco de Filtros
# =========================
st.subheader("Filtros")
c1, c2, c3, c4 = st.columns(4)
with c1:
    filtro_estudo = st.selectbox("Estudo", ["(Todos)"] + sorted(df["estudo"].dropna().unique().tolist()))
with c2:
    filtro_produto = st.selectbox("Produto", ["(Todos)"] + sorted(df["produto"].dropna().unique().tolist()))
with c3:
    dt_ini = st.date_input("Data de Início", value=None)
with c4:
    dt_fim = st.date_input("Data de Fim", value=None)

df_view = df.copy()
if filtro_estudo != "(Todos)":
    df_view = df_view[df_view["estudo"] == filtro_estudo]
if filtro_produto != "(Todos)":
    df_view = df_view[df_view["produto"] == filtro_produto]
if dt_ini and dt_fim:
    df_view = df_view[(pd.to_datetime(df_view['data']) >= pd.to_datetime(dt_ini)) & (pd.to_datetime(df_view['data']) <= pd.to_datetime(dt_fim))]

if df_view.empty:
    st.info("Nenhum lançamento encontrado com os filtros atuais.")
    st.stop()

st.dataframe(df_view, width='stretch',hide_index=True)

# =========================
# Bloco de Edição
# =========================
st.markdown("---")
st.subheader("✏️ Editar Lançamento")

if not df_view.empty:
    opcoes = df_view.apply(lambda r: f"[{r['id']}] {r['produto']} ({r['data']})", axis=1).tolist()
    map_rotulo_id = {label: int(label.split("]")[0][1:]) for label in opcoes}
    sel_rotulo = st.selectbox("Selecione o lançamento para editar", opcoes)
    selecionado = map_rotulo_id[sel_rotulo]
else:
    st.info("Nenhum lançamento para editar.")
    st.stop()
    
# Obter os dados do registro selecionado
registro = df[df['id'] == selecionado].iloc[0]

with st.expander("Dados do Lançamento"):
    with st.form("form_edicao"):
        col1, col2, col3 = st.columns(3)
        with col1:
            data = st.date_input("Data", value=date.fromisoformat(registro['data']))
        with col2:
            tipo_transacao = st.selectbox("Tipo de Transação", ["Entrada", "Saída"], index=["Entrada", "Saída"].index(registro['tipo_transacao']))
        with col3:
            quantidade = st.number_input("Quantidade", min_value=1, value=int(registro['quantidade']), step=1)
        
        st.caption(f"Produto: **{registro['produto']}** ({registro['estudo']})")

        c4, c5 = st.columns(2)
        with c4:
            validade_val = registro['validade']
            validade = st.date_input("Validade", value=date.fromisoformat(validade_val) if validade_val else None)
        with c5:
            lote = st.text_input("Lote", registro['lote'] if registro['lote'] else "")
        
        nota = st.text_input("Nota Fiscal", registro['nota'] if registro['nota'] else "")
        tipo_acao = st.text_input("Tipo de Ação", registro['tipo_acao'] if registro['tipo_acao'] else "")
        consideracoes = st.text_area("Considerações", registro['consideracoes'] if registro['consideracoes'] else "")
        st.text_input("Responsável (não editável)", registro['responsavel'], disabled=True)
        localizacao = st.text_input("Localização", registro['localizacao'] if registro['localizacao'] else "")

        submit = st.form_submit_button("Salvar Alterações")

        if submit:
            # Sua lógica de atualização
            update_data("movimentacoes", {
                "data": str(data),
                "tipo_transacao": tipo_transacao,
                "quantidade": int(quantidade),
                "validade": str(validade) if validade else None,
                "lote": lote if lote else None,
                "nota": nota if nota else None,
                "tipo_acao": tipo_acao if tipo_acao else None,
                "consideracoes": consideracoes if consideracoes else None,
                "localizacao": localizacao if localizacao else None
            }, "id", selecionado)  # <-- Aqui é onde a correção foi feita
            st.success("Lançamento atualizado com sucesso.")
            time.sleep(1.5)
            st.rerun()

# =========================
# Bloco de Exclusão
# =========================
st.markdown("---")
st.subheader("🗑️ Excluir Lançamento")
if st.button("Excluir", type="secondary"):
    try:
        delete_data("movimentacoes", "id", selecionado)
        st.success("Lançamento excluído com sucesso.")
        time.sleep(1.5)
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao excluir: {e}")