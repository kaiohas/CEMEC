import streamlit as st
import pandas as pd
from datetime import date, datetime
from database import get_data, insert_data, obter_saldo
import time

st.set_page_config(page_title="Movimentações", layout="wide")
st.title("📝 Registro de Movimentações")

# ---------------------------
# Helpers
# ---------------------------
def fmt_date(d) -> str:
    """Formata date/datetime/str para dd/mm/aaaa apenas para exibição."""
    if d in (None, "", "N/A"):
        return "—"
    try:
        if isinstance(d, (date, datetime)):
            return d.strftime("%d/%m/%Y")
        # tentar parsear string
        dt = pd.to_datetime(d, errors="coerce")
        if pd.isna(dt):
            return str(d)
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return str(d)

# Gatekeeper: apenas gestor
user = st.session_state.get('user')
if not user:
    st.error("Faça login para continuar."); st.stop()
if user.get('role') != 'gestor':
    st.error("Acesso restrito a gestores."); st.stop()

# ---------------------------
# Carregar dimensões
# ---------------------------
def df_or_empty(records, cols_rename=None):
    df = pd.DataFrame(records or [])
    if cols_rename:
        df = df.rename(columns=cols_rename)
    return df

estudos = df_or_empty(get_data("estudos", "id, nome"))
produtos = df_or_empty(get_data("produtos", "id, nome, estudo_id, tipo_produto"))
localizacoes = df_or_empty(get_data("localizacao", "nome"))
tipos_acao = df_or_empty(get_data("tipo_acao", "nome"))

# ---------------------------
# Formulário
# ---------------------------
col1, col2 = st.columns(2)
with col1:
    tipo_transacao = st.selectbox("Tipo de Transação", ["Entrada", "Saída"])
    estudo = st.selectbox("Estudo", estudos['nome'] if not estudos.empty else [])
    estudo_id = int(estudos.loc[estudos['nome'] == estudo, 'id'].values[0]) if not estudos.empty and estudo else None

with col2:
    data_acao = date.today()
    st.info(f"Data da Ação: **{fmt_date(data_acao)}**")
    quantidade = st.number_input("Quantidade", min_value=1, step=1)

# Produtos filtrados pelo estudo
produtos_estudo = produtos[produtos['estudo_id'] == estudo_id] if (estudo_id is not None) else pd.DataFrame()
produto = st.selectbox("Produto", produtos_estudo['nome'] if not produtos_estudo.empty else [])
produto_id = int(produtos_estudo.loc[produtos_estudo['nome'] == produto, 'id'].values[0]) if not produtos_estudo.empty and produto else None
tipo_produto = produtos_estudo.loc[produtos_estudo['nome'] == produto, 'tipo_produto'].values[0] if not produtos_estudo.empty and produto else ''

st.markdown(f"**Tipo de Produto:** {tipo_produto if tipo_produto else '-'}")

# Campos dependentes
validade = None
lote = None

if tipo_transacao == 'Entrada':
    cva, cvb = st.columns([1, 2])
    with cva:
        sem_validade = st.checkbox("Sem validade", value=True, help="Desmarque para informar uma data de validade.")
    with cvb:
        if sem_validade:
            validade = None
        else:
            validade = st.date_input("Validade", value=date.today())
    lote = st.text_input("Lote")
else:
    # Para saída, puxamos as opções existentes para ESTE estudo+produto
    base_movs = df_or_empty(get_data("movimentacoes", "validade, lote, estudo_id, produto_id"))
    if not base_movs.empty and (estudo_id is not None) and (produto_id is not None):
        base_movs = base_movs[(base_movs["estudo_id"] == estudo_id) & (base_movs["produto_id"] == produto_id)]
    else:
        base_movs = base_movs.iloc[0:0]  # vazio

    # Opções de validade (como labels dd/mm/aaaa)
    if not base_movs.empty and "validade" in base_movs.columns:
        vdates = pd.to_datetime(base_movs["validade"], errors="coerce").dt.date.dropna().drop_duplicates().sort_values().tolist()
    else:
        vdates = []
    validade_labels = ["Sem validade"] + [fmt_date(d) for d in vdates]
    validade_map = {"Sem validade": None}
    validade_map.update({fmt_date(d): d for d in vdates})
    validade_label = st.selectbox("Validade", validade_labels)
    validade = validade_map.get(validade_label)

    # Opções de lote
    if not base_movs.empty and "lote" in base_movs.columns:
        lotes = base_movs["lote"].dropna().drop_duplicates().sort_values().astype(str).tolist()
    else:
        lotes = []
    lote = st.selectbox("Lote", ["—"] + lotes)
    lote = None if (lote == "—") else lote

    # Mostra saldo disponível dinâmico (informativo)
    if (estudo_id is not None) and (produto_id is not None):
        saldo_preview = obter_saldo(estudo_id, produto_id, validade, lote)
        st.caption(
            f"Saldo disponível para **{produto or '—'}** | "
            f"**Validade:** {fmt_date(validade)} | **Lote:** {lote or '—'} → "
            f"**{int(saldo_preview)}**"
        )

nota = st.text_input("Nota Fiscal")
tipo_acao_sel = st.selectbox("Tipo de Ação", tipos_acao['nome'] if not tipos_acao.empty else [])
consideracoes = st.text_area("Considerações")
localizacao = st.selectbox("Localização", localizacoes['nome'] if not localizacoes.empty else [])

responsavel = user.get('username')
st.caption(f"Responsável: **{responsavel}**")

# ---------------------------
# Salvar
# ---------------------------
if st.button("Salvar Movimentação", type="primary"):
    if (estudo_id is None) or (produto_id is None):
        st.error("Selecione **Estudo** e **Produto**.")
        st.stop()

    if tipo_transacao == 'Saída':
        saldo_atual = obter_saldo(estudo_id, produto_id, validade, lote)
        if quantidade > (saldo_atual or 0):
            st.error(
                f"Não foi possível registrar a saída: quantidade informada (**{int(quantidade)}**) "
                f"excede o saldo disponível (**{int(saldo_atual or 0)}**)\n\n"
                f"**Produto:** {produto or '—'} | **Validade:** {fmt_date(validade)} | **Lote:** {lote or '—'}"
            )
            st.stop()

    payload = {
        "data": str(data_acao),  # mantemos ISO no banco; exibimos em BR no app
        "tipo_transacao": tipo_transacao,
        "estudo_id": estudo_id,
        "produto_id": produto_id,
        "tipo_produto": tipo_produto,
        "quantidade": int(quantidade),
        "validade": str(validade) if validade else None,
        "lote": lote if lote else None,
        "nota": nota if nota else None,
        "tipo_acao": tipo_acao_sel if tipo_acao_sel else None,
        "consideracoes": consideracoes if consideracoes else None,
        "responsavel": responsavel,
        "localizacao": localizacao if localizacao else None
    }

    try:
        insert_data("movimentacoes", payload)
        st.success("Movimentação registrada com sucesso!")
        time.sleep(1.2)
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao salvar movimentação: {e}")
