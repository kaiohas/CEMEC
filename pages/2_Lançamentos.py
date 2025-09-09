import streamlit as st
import pandas as pd
from datetime import date, datetime
import time
from database import get_data, update_data, delete_data

st.set_page_config(page_title="Lançamentos", layout="wide")
st.title("📜 Lançamentos Realizados")

# ---------------------------
# Helpers
# ---------------------------
def fmt_date(d) -> str:
    if d in (None, "", "N/A"):
        return "—"
    try:
        if isinstance(d, (date, datetime)):
            return d.strftime("%d/%m/%Y")
        dt = pd.to_datetime(d, errors="coerce")
        if pd.isna(dt):
            return str(d)
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return str(d)

# Gatekeeper
user = st.session_state.get('user')
if not user:
    st.error("Faça login para continuar."); st.stop()
if user.get('role') != 'gestor':
    st.error("Acesso restrito a gestores."); st.stop()

# --- Carregar dados do Supabase e fazer as junções com Pandas ---
try:
    df_movs = pd.DataFrame(get_data("movimentacoes", "*") or [])
    df_estudos = pd.DataFrame(get_data("estudos", "id, nome") or [])
    df_produtos = pd.DataFrame(get_data("produtos", "id, nome") or [])

    if df_movs.empty:
        st.warning("Nenhum lançamento encontrado.")
        st.stop()
        
    # Junções
    df = pd.merge(df_movs, df_estudos, left_on='estudo_id', right_on='id', how='left', suffixes=('', '_est'))
    df.rename(columns={'nome': 'estudo'}, inplace=True)
    df = pd.merge(df, df_produtos, left_on='produto_id', right_on='id', how='left', suffixes=('', '_prod'))
    df.rename(columns={'nome': 'produto'}, inplace=True)

    # Seleção de colunas finais
    df = df[['id', 'data', 'tipo_transacao', 'estudo', 'produto', 'tipo_produto',
             'quantidade', 'validade', 'lote', 'nota', 'tipo_acao', 'consideracoes',
             'responsavel', 'localizacao']].copy()

    # Converte 'data' para datetime (para filtros) e cria campos BR p/ exibição
    df['data_dt'] = pd.to_datetime(df['data'], errors='coerce')
    df['data_brl'] = df['data_dt'].apply(fmt_date)
    df['validade_brl'] = pd.to_datetime(df['validade'], errors='coerce').apply(fmt_date)

    df = df.sort_values(by='id', ascending=True)

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}"); st.stop()

# =========================
# Bloco de Filtros
# =========================
st.subheader("Filtros")
c0, c1, c2, c3, c4 = st.columns([1, 2, 2, 2, 2])

with c1:
    filtro_estudo = st.selectbox("Estudo", ["(Todos)"] + sorted([x for x in df["estudo"].dropna().unique().tolist()]))
with c2:
    filtro_produto = st.selectbox("Produto", ["(Todos)"] + sorted([x for x in df["produto"].dropna().unique().tolist()]))

# Período opcional (evita usar date_input com None)
aplicar_periodo = c0.checkbox("Filtrar por período?", value=False)
min_dt = df["data_dt"].min()
max_dt = df["data_dt"].max()

if aplicar_periodo:
    with c3:
        dt_ini = st.date_input("Data de Início", value=min_dt.date() if pd.notna(min_dt) else date.today())
    with c4:
        dt_fim = st.date_input("Data de Fim", value=max_dt.date() if pd.notna(max_dt) else date.today())
else:
    dt_ini = None
    dt_fim = None

df_view = df.copy()
if filtro_estudo != "(Todos)":
    df_view = df_view[df_view["estudo"] == filtro_estudo]
if filtro_produto != "(Todos)":
    df_view = df_view[df_view["produto"] == filtro_produto]
if dt_ini and dt_fim:
    df_view = df_view[(df_view['data_dt'] >= pd.to_datetime(dt_ini)) & (df_view['data_dt'] <= pd.to_datetime(dt_fim))]

if df_view.empty:
    st.info("Nenhum lançamento encontrado com os filtros atuais.")
    st.stop()

# Monta visão com datas no padrão BR
cols_order = ['id', 'data_brl', 'tipo_transacao', 'estudo', 'produto', 'tipo_produto',
              'quantidade', 'validade_brl', 'lote', 'nota', 'tipo_acao', 'consideracoes',
              'responsavel', 'localizacao']
df_show = df_view[cols_order].rename(columns={"data_brl": "Data", "validade_brl": "Validade"})

st.dataframe(df_show, use_container_width=True, hide_index=True)

# =========================
# Bloco de Edição
# =========================
st.markdown("---")
st.subheader("✏️ Editar Lançamento")

opcoes = df_view.apply(lambda r: f"[{r['id']}] {r['produto']} ({r['data_brl']})", axis=1).tolist()
map_rotulo_id = {label: int(label.split("]")[0][1:]) for label in opcoes}
sel_rotulo = st.selectbox("Selecione o lançamento para editar", opcoes)
selecionado = map_rotulo_id[sel_rotulo]

# Obter os dados do registro selecionado (usa df, não df_view)
registro = df[df['id'] == selecionado].iloc[0]

with st.expander("Dados do Lançamento"):
    with st.form("form_edicao"):
        col1, col2, col3 = st.columns(3)
        with col1:
            data_val = pd.to_datetime(registro['data'], errors='coerce')
            data_edit = st.date_input("Data", value=(data_val.date() if pd.notna(data_val) else date.today()))
        with col2:
            tipo_transacao = st.selectbox(
                "Tipo de Transação",
                ["Entrada", "Saída"],
                index=["Entrada", "Saída"].index(registro['tipo_transacao'])
            )
        with col3:
            quantidade = st.number_input("Quantidade", min_value=1, value=int(registro['quantidade']), step=1)

        st.caption(f"Produto: **{registro['produto']}** ({registro['estudo']})")

        c4, c5 = st.columns(2)
        with c4:
            validade_val = registro['validade']
            sem_validade = st.checkbox("Sem validade", value=(not bool(validade_val)))
            if sem_validade:
                validade_edit = None
            else:
                validade_parsed = pd.to_datetime(validade_val, errors='coerce')
                validade_edit = st.date_input(
                    "Validade",
                    value=(validade_parsed.date() if pd.notna(validade_parsed) else date.today())
                )
        with c5:
            lote = st.text_input("Lote", registro['lote'] if registro['lote'] else "")

        nota = st.text_input("Nota Fiscal", registro['nota'] if registro['nota'] else "")
        tipo_acao = st.text_input("Tipo de Ação", registro['tipo_acao'] if registro['tipo_acao'] else "")
        consideracoes = st.text_area("Considerações", registro['consideracoes'] if registro['consideracoes'] else "")
        st.text_input("Responsável (não editável)", registro['responsavel'], disabled=True)
        localizacao = st.text_input("Localização", registro['localizacao'] if registro['localizacao'] else "")

        submit = st.form_submit_button("Salvar Alterações")

        if submit:
            update_data("movimentacoes", {
                "data": str(data_edit),  # mantemos ISO no banco; exibimos em BR
                "tipo_transacao": tipo_transacao,
                "quantidade": int(quantidade),
                "validade": (str(validade_edit) if validade_edit else None),
                "lote": lote if lote else None,
                "nota": nota if nota else None,
                "tipo_acao": tipo_acao if tipo_acao else None,
                "consideracoes": consideracoes if consideracoes else None,
                "localizacao": localizacao if localizacao else None
            }, "id", selecionado)
            st.success("Lançamento atualizado com sucesso.")
            time.sleep(1.2)
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
        time.sleep(1.2)
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao excluir: {e}")
