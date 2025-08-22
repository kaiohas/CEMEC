import streamlit as st
import pandas as pd
from database import conectar
from datetime import datetime
import numpy as np

# ...
st.title("📊 Visão Geral do Estoque")

user = st.session_state.get('user')
if not user:
    st.error("Faça login para continuar."); st.stop()
# Visualizador E Gestor têm acesso aqui



conn = conectar()

# Carregar dados
query = """
SELECT 
    m.id, m.data, m.tipo_transacao, e.nome AS estudo, p.nome AS produto, 
    m.tipo_produto, m.quantidade, m.validade, m.lote
FROM movimentacoes m
LEFT JOIN estudos e ON m.estudo_id = e.id
LEFT JOIN produtos p ON m.produto_id = p.id
"""
df = pd.read_sql(query, conn)

if df.empty:
    st.warning("Nenhuma movimentação registrada.")
    st.stop()

# Função para farol
def farol(validade):
    if validade in ["", "N/A", None]:
        return ""
    try:
        validade_date = datetime.strptime(validade, "%Y-%m-%d").date()
        dias = (validade_date - datetime.today().date()).days
        if dias < 0:
            return "⚫"  # Preto
        elif dias < 30:
            return "🔴"  # Vermelho
        elif dias < 60:
            return "🟠"  # Laranja
        elif dias < 90:
            return "🔵"  # Azul
        else:
            return "🟢"  # Verde
    except:
        return ""

# Filtros
estudo_filter = st.multiselect("Filtrar por Estudo", df['estudo'].unique())
produto_filter = st.multiselect("Filtrar por Produto", df['produto'].unique())

if estudo_filter:
    df = df[df['estudo'].isin(estudo_filter)]
if produto_filter:
    df = df[df['produto'].isin(produto_filter)]

# --- Filtro por Validade (NOVO) ---
# cria uma coluna de data para filtrar, sem mexer no texto original usado pelo farol
df["validade_dt"] = pd.to_datetime(df["validade"], errors="coerce").dt.date

# define o intervalo padrão
min_valid = df["validade_dt"].min()
max_valid = df["validade_dt"].max()

# se não houver datas válidas, usa hoje como fallback
from datetime import date
if pd.isna(min_valid) or pd.isna(max_valid):
    default_range = (date.today(), date.today())
else:
    default_range = (min_valid, max_valid)

cval1, cval2 = st.columns([2, 1])
with cval1:
    intervalo_validade = st.date_input(
        "Filtrar por Validade (intervalo)",
        value=default_range,
        help="Selecione início e fim do intervalo de validade."
    )
with cval2:
    incluir_sem_validade = st.checkbox("Incluir itens sem validade", value=True)

# normaliza retorno do date_input
if isinstance(intervalo_validade, (list, tuple)) and len(intervalo_validade) == 2:
    dt_ini, dt_fim = intervalo_validade
else:
    dt_ini = dt_fim = intervalo_validade

# aplica filtro
mask_valid = pd.Series(False, index=df.index)
if dt_ini and dt_fim:
    mask_valid |= df["validade_dt"].between(dt_ini, dt_fim)

if incluir_sem_validade:
    mask_valid |= df["validade_dt"].isna()

df = df[mask_valid].copy()


# Agrupar
agrupado = df.groupby(['estudo', 'produto', 'validade', 'lote']).agg({
    'quantidade': lambda x: x[df.loc[x.index, 'tipo_transacao'] == 'Entrada'].sum() - x[df.loc[x.index, 'tipo_transacao'] == 'Saída'].sum()
}).reset_index()

agrupado.rename(columns={'quantidade': 'Saldo Total'}, inplace=True)

# Calcular farol
agrupado['Farol'] = agrupado['validade'].apply(farol)

# Ajustar para entradas e saídas
df_entrada = df[df['tipo_transacao'] == 'Entrada'].groupby(['estudo', 'produto', 'validade', 'lote'])['quantidade'].sum().reset_index().rename(columns={'quantidade':'Entradas'})
df_saida = df[df['tipo_transacao'] == 'Saída'].groupby(['estudo', 'produto', 'validade', 'lote'])['quantidade'].sum().reset_index().rename(columns={'quantidade':'Saídas'})

resultado = pd.merge(agrupado, df_entrada, on=['estudo','produto','validade','lote'], how='left')
resultado = pd.merge(resultado, df_saida, on=['estudo','produto','validade','lote'], how='left')

resultado['Entradas'] = resultado['Entradas'].fillna(0).astype(int)
resultado['Saídas'] = resultado['Saídas'].fillna(0).astype(int)

# Ordenar
resultado = resultado.sort_values(by=['estudo','produto','validade','lote'])

st.dataframe(resultado)

conn.close()
