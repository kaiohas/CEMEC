import streamlit as st
import pandas as pd
from database import conectar

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

conn = conectar()
cur = conn.cursor()

# Carregar dimensões
df_estudos = pd.read_sql("SELECT id, nome FROM estudos ORDER BY nome", conn)
df_tipos   = pd.read_sql("SELECT nome FROM tipo_produto ORDER BY nome", conn)

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
            cur.execute(
                "INSERT INTO produtos (estudo_id, nome, tipo_produto) VALUES (?, ?, ?)",
                (estudo_id, produto_nome.strip(), tipo_produto),
            )
            conn.commit()
            st.toast("Produto cadastrado com sucesso!", icon="✅")
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao cadastrar: {e}")

st.divider()

st.subheader("📋 Produtos cadastrados")
# Base para listagem com join do Estudo
sql_list = """
SELECT p.id, p.nome AS produto, p.tipo_produto, e.nome AS estudo, p.estudo_id
FROM produtos p
LEFT JOIN estudos e ON e.id = p.estudo_id
ORDER BY e.nome, p.nome
"""
df_prod = pd.read_sql(sql_list, conn)

if df_prod.empty:
    st.info("Nenhum produto cadastrado ainda.")
else:
    # Filtros
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

    st.dataframe(df_view, use_container_width=True)

    st.markdown("### 🗑️ Excluir produto")
    if df_view.empty:
        st.caption("Nenhum item para excluir com os filtros atuais.")
    else:
        # Seleciona por ID (mostra rótulo amigável com nome + estudo)
        opcoes = df_view.apply(lambda r: f"[{r['id']}] {r['produto']} — {r['estudo']}", axis=1).tolist()
        map_rotulo_id = {label: int(label.split("]")[0][1:]) for label in opcoes}
        sel_rotulo = st.selectbox("Selecione o produto", opcoes)
        sel_id = map_rotulo_id[sel_rotulo]

        # Verificar se há movimentações
        cur.execute("SELECT COUNT(*) FROM movimentacoes WHERE produto_id = ?", (sel_id,))
        qtd_movs = cur.fetchone()[0]

        if qtd_movs > 0:
            st.warning(f"Este produto possui **{qtd_movs} lançamento(s)** vinculado(s). "
                       "Para manter a integridade dos dados, exclua os lançamentos primeiro em **📜 Lançamentos**.")
            st.button("Excluir produto", disabled=True)
        else:
            if st.button("Excluir produto", type="secondary"):
                try:
                    cur.execute("DELETE FROM produtos WHERE id = ?", (sel_id,))
                    conn.commit()
                    st.toast("Produto excluído com sucesso.", icon="🗑️")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao excluir: {e}")

conn.close()
