import streamlit as st
import pandas as pd
from datetime import date
from database import conectar

st.set_page_config(page_title="Movimentações", layout="wide")
st.title("📝 Registro de Movimentações")

# Gatekeeper: apenas gestor
user = st.session_state.get('user')
if not user:
    st.error("Faça login para continuar."); st.stop()
if user['role'] != 'gestor':
    st.error("Acesso restrito a gestores."); st.stop()

conn = conectar()
cursor = conn.cursor()

# ---------------------------
# Helpers
# ---------------------------
def obter_saldo(conn, estudo_id, produto_id, validade, lote):
    """
    Retorna o saldo atual (Entradas - Saídas) para a combinação
    Estudo + Produto + Validade + Lote.
    """
    params = {"estudo_id": estudo_id, "produto_id": produto_id}
    cond = ["m.estudo_id = :estudo_id", "m.produto_id = :produto_id"]

    # Filtro por validade (NULL vs valor)
    if validade:
        cond.append("m.validade = :validade")
        params["validade"] = str(validade)
    else:
        cond.append("m.validade IS NULL")

    # Filtro por lote (NULL vs valor)
    if lote:
        cond.append("m.lote = :lote")
        params["lote"] = lote
    else:
        cond.append("m.lote IS NULL")

    sql = f"""
        SELECT
            COALESCE(SUM(CASE WHEN m.tipo_transacao = 'Entrada' THEN m.quantidade ELSE 0 END), 0)
          - COALESCE(SUM(CASE WHEN m.tipo_transacao = 'Saída'   THEN m.quantidade ELSE 0 END), 0)
        AS saldo
        FROM movimentacoes m
        WHERE {" AND ".join(cond)}
    """
    df_s = pd.read_sql(sql, conn, params=params)
    try:
        return int(df_s.iloc[0, 0]) if not df_s.empty else 0
    except Exception:
        return 0

# ---------------------------
# Carregar dimensões
# ---------------------------
estudos = pd.read_sql("SELECT id, nome FROM estudos ORDER BY nome", conn)
produtos = pd.read_sql("SELECT id, nome, estudo_id, tipo_produto FROM produtos ORDER BY nome", conn)
localizacoes = pd.read_sql("SELECT nome FROM localizacao ORDER BY nome", conn)
tipos_acao = pd.read_sql("SELECT nome FROM tipo_acao ORDER BY nome", conn)

# ---------------------------
# Formulário
# ---------------------------
col1, col2 = st.columns(2)
with col1:
    tipo_transacao = st.selectbox("Tipo de Transação", ["Entrada", "Saída"])
    estudo = st.selectbox("Estudo", estudos['nome'] if not estudos.empty else [])
    estudo_id = int(estudos.loc[estudos['nome'] == estudo, 'id'].values[0]) if not estudos.empty and estudo else None

with col2:
    # Data travada no dia atual
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
    base_movs = pd.read_sql(
        """
        SELECT validade, lote
        FROM movimentacoes
        WHERE estudo_id = ? AND produto_id = ?
        """,
        conn, params=(estudo_id if estudo_id else -1, produto_id if produto_id else -1)
    )

    op_validade = (
        pd.to_datetime(base_movs['validade'], errors='coerce').dt.date.dropna().drop_duplicates().sort_values()
        if not base_movs.empty else pd.Series([], dtype="object")
    )
    op_lote = (
        base_movs['lote'].dropna().drop_duplicates().sort_values()
        if not base_movs.empty else pd.Series([], dtype="object")
    )

    # Observação: permitir também Saída de itens sem validade/lote (pode existir)
    validade = st.selectbox("Validade", [None] + op_validade.astype(object).tolist())
    lote = st.selectbox("Lote", [None] + op_lote.astype(str).tolist())

nota = st.text_input("Nota Fiscal")
tipo_acao_sel = st.selectbox("Tipo de Ação", tipos_acao['nome'] if not tipos_acao.empty else [])
consideracoes = st.text_area("Considerações")
localizacao = st.selectbox("Localização", localizacoes['nome'] if not localizacoes.empty else [])

# Responsável amarrado ao usuário logado
responsavel = user['username']
st.caption(f"Responsável: **{responsavel}**")

# ---------------------------
# Salvar
# ---------------------------
if st.button("Salvar Movimentação", type="primary"):
    # Valida seleção mínima
    if not (estudo_id and produto_id):
        st.error("Selecione **Estudo** e **Produto**.")
        st.stop()

    # Regras de validação para Saída: não permitir saldo negativo
    if tipo_transacao == 'Saída':
        # Para cálculo do saldo, consideramos a mesma chave (estudo+produto+validade+lote)
        saldo_atual = obter_saldo(conn, estudo_id, produto_id, validade, lote)

        if quantidade > saldo_atual:
            # Mensagem amigável com o saldo atual
            chave_validade = validade.isoformat() if hasattr(validade, "isoformat") else ("—" if validade is None else str(validade))
            chave_lote = lote if lote else "—"
            st.error(
                f"Não foi possível registrar a saída: quantidade informada (**{int(quantidade)}**) "
                f"excede o saldo disponível (**{int(saldo_atual)}**)\n\n"
                f"**Produto:** {produto} | **Validade:** {chave_validade} | **Lote:** {chave_lote}"
            )
            st.stop()

    # Tudo ok, inserir
    cursor.execute(
        """
        INSERT INTO movimentacoes 
        (data, tipo_transacao, estudo_id, produto_id, tipo_produto, quantidade, validade, lote, nota, tipo_acao, consideracoes, responsavel, localizacao)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(data_acao), tipo_transacao, estudo_id, produto_id, tipo_produto,
            int(quantidade),
            str(validade) if validade else None,
            lote if lote else None,
            nota if nota else None,
            tipo_acao_sel if tipo_acao_sel else None,
            consideracoes if consideracoes else None,
            responsavel,
            localizacao if localizacao else None
        )
    )
    conn.commit()
    st.success("Movimentação registrada com sucesso!")
    st.rerun()

conn.close()
