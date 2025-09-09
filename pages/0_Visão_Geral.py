import streamlit as st
import pandas as pd
from datetime import datetime, date
from database import get_data

st.set_page_config(page_title="Visão Geral do Estoque", layout="wide")
st.title("📊 Visão Geral do Estoque")

# ---------------------------
# Helpers
# ---------------------------
def fmt_date_br(d) -> str:
    """Formata datas (str/date/datetime) para dd/mm/aaaa apenas para exibição."""
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

def farol(validade_value):
    """Retorna emoji do farol conforme dias para vencer."""
    if validade_value in (None, "", "N/A"):
        return ""
    try:
        # suporta tanto string ISO quanto date/datetime
        if isinstance(validade_value, (date, datetime)):
            validade_date = validade_value if isinstance(validade_value, date) else validade_value.date()
        else:
            validade_date = pd.to_datetime(validade_value, errors="coerce")
            if pd.isna(validade_date):
                return ""
            validade_date = validade_date.date()
        dias = (validade_date - date.today()).days
        if dias < 0:
            return "🔴"  # vencido
        elif dias <= 30:
            return "🟠"  # 0-30d
        elif dias <= 60:
            return "🟡"  # 31-60d
        elif dias <= 90:
            return "🔵"  # 61-90d
        else:
            return "🟢"  # >90d
    except Exception:
        return ""

# ---------------------------
# Gatekeeper (gestor e visualizador)
# ---------------------------
user = st.session_state.get('user')
if not user:
    st.error("Faça login para continuar.")
    st.stop()

# ---------------------------
# Carregar dados
# ---------------------------
try:
    df_movs = pd.DataFrame(get_data("movimentacoes", "*") or [])
    if df_movs.empty:
        st.warning("Nenhuma movimentação registrada.")
        st.stop()

    df_estudos = pd.DataFrame(get_data("estudos", "id, nome") or [])
    df_produtos = pd.DataFrame(get_data("produtos", "id, nome") or [])

    # Enriquecimento
    df_movs = pd.merge(df_movs, df_estudos, left_on='estudo_id', right_on='id', how='left', suffixes=('', '_est'))
    df_movs.rename(columns={'nome': 'estudo'}, inplace=True)

    df_movs = pd.merge(df_movs, df_produtos, left_on='produto_id', right_on='id', how='left', suffixes=('', '_prod'))
    df_movs.rename(columns={'nome': 'produto'}, inplace=True)

    # Campos de interesse
    df = df_movs[['id', 'data', 'tipo_transacao', 'estudo', 'produto', 'tipo_produto',
                  'quantidade', 'validade', 'lote']].copy()

    # Normalização para evitar NaN no agrupamento
    df[['estudo', 'produto', 'validade', 'lote', 'tipo_transacao']] = \
        df[['estudo', 'produto', 'validade', 'lote', 'tipo_transacao']].fillna('')

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.stop()

# ---------------------------
# Filtros superiores
# ---------------------------
col_esq, col_dir = st.columns([1, 1])

with col_esq:
    estudo_filter = st.multiselect("Filtrar por Estudo", sorted([x for x in df['estudo'].unique() if x]))
with col_dir:
    produto_filter = st.multiselect("Filtrar por Produto", sorted([x for x in df['produto'].unique() if x]))

if estudo_filter:
    df = df[df['estudo'].isin(estudo_filter)]
if produto_filter:
    df = df[df['produto'].isin(produto_filter)]

# Filtro opcional por período de validade
c_chk, c_periodo = st.columns([1, 3])
with c_chk:
    considerar_validade = st.checkbox("Filtrar por intervalo de validade", value=False)

if considerar_validade:
    df["validade_dt"] = pd.to_datetime(df["validade"], errors="coerce")
    min_valid = df["validade_dt"].min(skipna=True)
    max_valid = df["validade_dt"].max(skipna=True)
    if pd.isna(min_valid) or pd.isna(max_valid):
        default_range = (date.today(), date.today())
    else:
        default_range = (min_valid.date(), max_valid.date())
    with c_periodo:
        intervalo_validade = st.date_input(
            "Intervalo de Validade",
            value=default_range,
            help="Selecione início e fim do intervalo de validade."
        )
    if isinstance(intervalo_validade, (list, tuple)) and len(intervalo_validade) == 2:
        dt_ini, dt_fim = intervalo_validade
    else:
        dt_ini = dt_fim = intervalo_validade
    dt_ini = pd.to_datetime(dt_ini) if dt_ini else None
    dt_fim = pd.to_datetime(dt_fim) if dt_fim else None
    if (dt_ini is not None) and (dt_fim is not None):
        df = df[df["validade_dt"].between(dt_ini, dt_fim, inclusive="both")].copy()

# ---------------------------
# Agregação
# ---------------------------
# Colunas derivadas para Entradas e Saídas
df['Entradas'] = (df['tipo_transacao'] == 'Entrada').astype(int) * df['quantidade'].astype(float)
df['Saidas'] = (df['tipo_transacao'] == 'Saída').astype(int) * df['quantidade'].astype(float)

agrupado = (
    df.groupby(['estudo', 'produto', 'validade', 'lote'], dropna=False)
      .agg(Entradas=('Entradas', 'sum'),
           Saidas=('Saidas', 'sum'))
      .reset_index()
)

agrupado['Saldo Total'] = agrupado['Entradas'] - agrupado['Saidas']

# Farol e datas para exibição
agrupado['Farol'] = agrupado['validade'].apply(farol)
agrupado['Validade (BR)'] = agrupado['validade'].apply(fmt_date_br)

# ---------------------------
# Filtro de saldos zerados
# ---------------------------
c_zero, _ = st.columns([1, 3])
with c_zero:
    apenas_saldos_zerados = st.checkbox("Mostrar apenas saldos zerados", value=False)

if apenas_saldos_zerados:
    agrupado = agrupado[agrupado['Saldo Total'].fillna(0) == 0]

# Ajustes finais de tipo e ordenação
agrupado = agrupado.fillna({'lote': ''})
agrupado[['Entradas', 'Saidas', 'Saldo Total']] = agrupado[['Entradas', 'Saidas', 'Saldo Total']].round(0).astype(int)
agrupado = agrupado.sort_values(by=['estudo', 'produto', 'validade', 'lote'], na_position="last")

# ---------------------------
# Tabela
# ---------------------------
if not agrupado.empty:
    cols_show = ['Farol', 'estudo', 'produto', 'Validade (BR)', 'lote', 'Entradas', 'Saidas', 'Saldo Total']
    st.dataframe(
        agrupado[cols_show]
                .rename(columns={
                    'estudo': 'Estudo',
                    'produto': 'Produto',
                    'lote': 'Lote',
                    'Entradas': 'Entradas',
                    'Saidas': 'Saídas',
                    'Saldo Total': 'Saldo Total'
                }),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Farol": st.column_config.Column(width="small"),
            "Estudo": st.column_config.Column(width="medium"),
            "Produto": st.column_config.Column(width="large"),
            "Validade (BR)": st.column_config.Column(width="small"),
            "Lote": st.column_config.Column(width="small"),
            "Entradas": st.column_config.Column(width="small"),
            "Saídas": st.column_config.Column(width="small"),
            "Saldo Total": st.column_config.Column(width="small"),
        }
    )

    st.divider()
    st.subheader("Métricas Gerais")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total de Entradas", f"{agrupado['Entradas'].sum():.0f}")
    with c2:
        st.metric("Total de Saídas", f"{agrupado['Saidas'].sum():.0f}")
    with c3:
        st.metric("Saldo Geral", f"{agrupado['Saldo Total'].sum():.0f}")
else:
    st.info("Nenhum item para exibir com os filtros atuais.")
