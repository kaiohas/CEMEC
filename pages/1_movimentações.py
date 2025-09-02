import streamlit as st
import pandas as pd
from datetime import date
from database import conectar, get_data, insert_data, obter_saldo
import time

st.set_page_config(page_title="Movimentações", layout="wide")
st.title("📝 Registro de Movimentações")

# Gatekeeper: apenas gestor
user = st.session_state.get('user')
if not user:
    st.error("Faça login para continuar."); st.stop()
if user['role'] != 'gestor':
    st.error("Acesso restrito a gestores."); st.stop()

# Não precisamos mais do objeto 'conn' ou 'cursor' do SQLite.

# ---------------------------
# Carregar dimensões
# ---------------------------
# Substitui pd.read_sql por get_data
estudos = pd.DataFrame(get_data("estudos", "id, nome"))
produtos = pd.DataFrame(get_data("produtos", "id, nome, estudo_id, tipo_produto"))
localizacoes = pd.DataFrame(get_data("localizacao", "nome"))
tipos_acao = pd.DataFrame(get_data("tipo_acao", "nome"))

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
    st.info(f"Data da Ação: **{data_acao.isoformat()}**")
    quantidade = st.number_input("Quantidade", min_value=1, step=1)

# Produtos filtrados pelo estudo
produtos_estudo = produtos[produtos['estudo_id'] == estudo_id] if estudo_id else pd.DataFrame()
produto = st.selectbox("Produto", produtos_estudo['nome'] if not produtos_estudo.empty else [])

produto_id = int(produtos_estudo.loc[produtos_estudo['nome'] == produto, 'id'].values[0]) if not produtos_estudo.empty and produto else None
tipo_produto = produtos_estudo.loc[produtos_estudo['nome'] == produto, 'tipo_produto'].values[0] if not produtos_estudo.empty and produto else ''
st.markdown(f"**Tipo de Produto:** {tipo_produto if tipo_produto else '-'}")

# Campos dependentes
if tipo_transacao == 'Entrada':
    usar_validade = st.checkbox("Informar validade?")
    validade = st.date_input("Validade") if usar_validade else None
    lote = st.text_input("Lote")
else:
    # Para saída, puxamos as opções já existentes para este estudo+produto
    # Substitui pd.read_sql
    base_movs = pd.DataFrame(get_data("movimentacoes", "validade, lote"))

    op_validade = (
        pd.to_datetime(base_movs['validade'], errors='coerce').dt.date.dropna().drop_duplicates().sort_values()
        if not base_movs.empty else pd.Series([], dtype="object")
    )
    op_lote = (
        base_movs['lote'].dropna().drop_duplicates().sort_values()
        if not base_movs.empty else pd.Series([], dtype="object")
    )

    validade = st.selectbox("Validade", [None] + op_validade.astype(object).tolist())
    lote = st.selectbox("Lote", [None] + op_lote.astype(str).tolist())

nota = st.text_input("Nota Fiscal")
tipo_acao_sel = st.selectbox("Tipo de Ação", tipos_acao['nome'] if not tipos_acao.empty else [])
consideracoes = st.text_area("Considerações")
localizacao = st.selectbox("Localização", localizacoes['nome'] if not localizacoes.empty else [])

responsavel = user['username']
st.caption(f"Responsável: **{responsavel}**")

# ---------------------------
# Salvar
# ---------------------------
if st.button("Salvar Movimentação", type="primary"):
    if not (estudo_id and produto_id):
        st.error("Selecione **Estudo** e **Produto**.")
        st.stop()

    if tipo_transacao == 'Saída':
        saldo_atual = obter_saldo(estudo_id, produto_id, validade, lote)

        if quantidade > saldo_atual:
            chave_validade = validade.isoformat() if hasattr(validade, "isoformat") else ("—" if validade is None else str(validade))
            chave_lote = lote if lote else "—"
            st.error(
                f"Não foi possível registrar a saída: quantidade informada (**{int(quantidade)}**) "
                f"excede o saldo disponível (**{int(saldo_atual)}**)\n\n"
                f"**Produto:** {produto} | **Validade:** {chave_validade} | **Lote:** {chave_lote}"
            )
            st.stop()

    # Tudo ok, inserir
    insert_data("movimentacoes", {
        "data": str(data_acao),
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
    })
    st.success("Movimentação registrada com sucesso!")
    time.sleep(1.5)
    st.rerun()