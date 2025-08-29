import streamlit as st
import pandas as pd
from database import conectar
from datetime import date

st.set_page_config(page_title="Lançamentos", layout="wide")
st.title("📜 Lançamentos Realizados")

# Flash (mensagens pós-rerun)
flash = st.session_state.pop("_flash_lanc", None)
if flash:
    level, msg = flash
    getattr(st, level)(msg)

# Gatekeeper
user = st.session_state.get('user')
if not user:
    st.error("Faça login para continuar."); st.stop()
if user['role'] != 'gestor':
    st.error("Acesso restrito a gestores."); st.stop()

conn = conectar()
cursor = conn.cursor()

query = """
SELECT 
    m.id, m.data, m.tipo_transacao, e.nome AS estudo, p.nome AS produto, 
    m.tipo_produto, m.quantidade, m.validade, m.lote, m.nota, 
    m.tipo_acao, m.consideracoes, m.responsavel, m.localizacao
FROM movimentacoes m
LEFT JOIN estudos e ON m.estudo_id = e.id
LEFT JOIN produtos p ON m.produto_id = p.id
ORDER BY m.id DESC
"""
df = pd.read_sql(query, conn)

if df.empty:
    st.warning("Nenhum lançamento encontrado.")
    st.stop()

# =========================
# NOVO: Bloco de Filtros
# =========================

# Coluna auxiliar para filtrar validade (sem mexer no texto original)
df["validade_dt"] = pd.to_datetime(df["validade"], errors="coerce").dt.date

# Linha 1 de filtros: Estudo, Produto, Responsável
fc1, fc2, fc3 = st.columns(3)
with fc1:
    f_estudo = st.multiselect(
        "Filtrar por Estudo",
        sorted(df["estudo"].dropna().unique().tolist())
    )
with fc2:
    f_produto = st.multiselect(
        "Filtrar por Produto",
        sorted(df["produto"].dropna().unique().tolist())
    )
with fc3:
    f_resp = st.multiselect(
        "Filtrar por Responsável",
        sorted(df["responsavel"].dropna().unique().tolist())
    )

mask = pd.Series(True, index=df.index)
if f_estudo:
    mask &= df["estudo"].isin(f_estudo)
if f_produto:
    mask &= df["produto"].isin(f_produto)
if f_resp:
    mask &= df["responsavel"].isin(f_resp)

# Linha 2 de filtros: Validade (intervalo) e incluir sem validade
min_v = df.loc[mask, "validade_dt"].min()
max_v = df.loc[mask, "validade_dt"].max()
default_range = (
    (min_v if pd.notna(min_v) else date.today()),
    (max_v if pd.notna(max_v) else date.today()),
)

fv1, fv2 = st.columns([2, 1])
with fv1:
    intervalo_validade = st.date_input(
        "Validade (intervalo)",
        value=default_range,
        help="Selecione o período de validade."
    )
with fv2:
    incluir_sem_validade = st.checkbox("Incluir sem validade", value=True)

# Normaliza retorno do date_input
if isinstance(intervalo_validade, (list, tuple)) and len(intervalo_validade) == 2:
    dt_ini, dt_fim = intervalo_validade
else:
    dt_ini = dt_fim = intervalo_validade

mask_valid = pd.Series(False, index=df.index)
if dt_ini and dt_fim:
    mask_valid |= df["validade_dt"].between(dt_ini, dt_fim)
if incluir_sem_validade:
    mask_valid |= df["validade_dt"].isna()

mask &= mask_valid

# Filtro de Lote (com base no recorte atual)
df_partial = df[mask].copy()
f_lote = st.multiselect(
    "Filtrar por Lote",
    sorted(df_partial["lote"].dropna().astype(str).unique().tolist())
)
if f_lote:
    mask &= df["lote"].astype(str).isin(f_lote)

# Resultado final dos filtros
df_view = df[mask].copy()

# Caso não haja registros após o filtro
if df_view.empty:
    st.info("Nenhum lançamento encontrado com os filtros selecionados.")
    st.stop()

# =========================
# Exibição e edição (usa df_view)
# =========================
st.dataframe(df_view, use_container_width=True)

ids = df_view['id'].tolist()
selecionado = st.selectbox("Selecione o ID", ids)
registro = df_view[df_view['id'] == selecionado].iloc[0]

with st.expander("✏️ Editar Lançamento"):
    with st.form("editar_form"):
        data_padrao = pd.to_datetime(registro['data'], errors="coerce")
        data_padrao = data_padrao.date() if pd.notna(data_padrao) else date.today()

        data = st.date_input("Data", data_padrao)
        tipo_transacao = st.selectbox(
            "Tipo de Transação",
            ["Entrada", "Saída"],
            index=(0 if registro['tipo_transacao'] == "Entrada" else 1)
        )
        quantidade = st.number_input("Quantidade", min_value=1, value=int(registro['quantidade']))
        validade = st.text_input("Validade", registro['validade'] if registro['validade'] else "")
        lote = st.text_input("Lote", registro['lote'] if registro['lote'] else "")
        nota = st.text_input("Nota Fiscal", registro['nota'] if registro['nota'] else "")
        tipo_acao = st.text_input("Tipo de Ação", registro['tipo_acao'] if registro['tipo_acao'] else "")
        consideracoes = st.text_area("Considerações", registro['consideracoes'] if registro['consideracoes'] else "")
        st.text_input("Responsável (não editável)", registro['responsavel'], disabled=True)
        localizacao = st.text_input("Localização", registro['localizacao'] if registro['localizacao'] else "")

        submit = st.form_submit_button("Salvar Alterações")

        if submit:
            cursor.execute("""
                UPDATE movimentacoes 
                SET data=?, tipo_transacao=?, quantidade=?, validade=?, lote=?, nota=?, 
                    tipo_acao=?, consideracoes=?, localizacao=?
                WHERE id=?
            """, (
                str(data), 
                tipo_transacao, 
                int(quantidade), 
                validade if validade else None, 
                lote if lote else None,
                nota if nota else None, 
                tipo_acao if tipo_acao else None, 
                consideracoes if consideracoes else None,
                localizacao if localizacao else None, 
                selecionado
            ))
            conn.commit()
            st.session_state["_flash_lanc"] = ("success", "Lançamento atualizado com sucesso.")
            st.rerun()

with st.expander("🗑️ Excluir Lançamento"):
    if st.button("Excluir"):
        cursor.execute("DELETE FROM movimentacoes WHERE id=?", (selecionado,))
        conn.commit()
        st.session_state["_flash_lanc"] = ("success", "Lançamento atualizado com sucesso.")
        st.rerun()

conn.close()

