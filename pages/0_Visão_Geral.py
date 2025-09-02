import streamlit as st
import pandas as pd
from datetime import datetime, date
import numpy as np
from database import get_data

st.set_page_config(page_title="Visão Geral do Estoque", layout="wide")
st.title("📊 Visão Geral do Estoque")

# Gatekeeper (gestor e visualizador)
user = st.session_state.get('user')
if not user:
    st.error("Faça login para continuar."); st.stop()

# --- Carregar dados do Supabase e fazer as junções com Pandas ---
try:
    df_movs = pd.DataFrame(get_data("movimentacoes", "*"))
    
    if df_movs.empty:
        st.warning("Nenhuma movimentação registrada.")
        st.stop()

    df_estudos = pd.DataFrame(get_data("estudos", "id, nome"))
    df_produtos = pd.DataFrame(get_data("produtos", "id, nome"))

    df_movs = pd.merge(df_movs, df_estudos, left_on='estudo_id', right_on='id', how='left', suffixes=('', '_est'))
    df_movs.rename(columns={'nome': 'estudo'}, inplace=True)
    df_movs = pd.merge(df_movs, df_produtos, left_on='produto_id', right_on='id', how='left', suffixes=('', '_prod'))
    df_movs.rename(columns={'nome': 'produto'}, inplace=True)
    
    # --- CORREÇÃO AQUI ---
    # Substitui os valores nulos por uma string vazia para o agrupamento funcionar
    df = df_movs[['id', 'data', 'tipo_transacao', 'estudo', 'produto', 'tipo_produto', 'quantidade', 'validade', 'lote']]
    df = df.fillna('')
    # Fim da correção
    

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}"); st.stop()

def farol(validade):
    if pd.isna(validade) or validade == "" or validade == "N/A":
        return ""
    try:
        validade_date = datetime.strptime(validade, "%Y-%m-%d").date()
        dias = (validade_date - date.today()).days
        if dias < 0:
            return "⚫"
        elif dias < 30:
            return "🔴"
        elif dias < 60:
            return "🟠"
        elif dias < 90:
            return "🔵"
        else:
            return "🟢"
    except (ValueError, TypeError):
        return ""

estudo_filter = st.multiselect("Filtrar por Estudo", sorted(df['estudo'].dropna().unique()))
produto_filter = st.multiselect("Filtrar por Produto", sorted(df['produto'].dropna().unique()))

if estudo_filter:
    df = df[df['estudo'].isin(estudo_filter)]
if produto_filter:
    df = df[df['produto'].isin(produto_filter)]

col_chk, col_dt = st.columns([1, 2])
with col_chk:
    considerar_validade = st.checkbox("Considerar data de validade", value=False)

if considerar_validade:
    df["validade_dt"] = pd.to_datetime(df["validade"], errors="coerce")
    min_valid = df["validade_dt"].min(skipna=True)
    max_valid = df["validade_dt"].max(skipna=True)
    
    if pd.isna(min_valid) or pd.isna(max_valid):
        default_range = (date.today(), date.today())
    else:
        default_range = (min_valid.date(), max_valid.date())

    with col_dt:
        intervalo_validade = st.date_input("Intervalo de Validade", value=default_range, help="Selecione início e fim do intervalo de validade.")

    if isinstance(intervalo_validade, (list, tuple)) and len(intervalo_validade) == 2:
        dt_ini, dt_fim = intervalo_validade
    else:
        dt_ini = dt_fim = intervalo_validade
    
    dt_ini = pd.to_datetime(dt_ini) if dt_ini else None
    dt_fim = pd.to_datetime(dt_fim) if dt_fim else None

    if dt_ini is not None and dt_fim is not None:
        df = df[df["validade_dt"].between(dt_ini, dt_fim, inclusive="both")].copy()

df['Entradas'] = df.apply(lambda row: row['quantidade'] if row['tipo_transacao'] == 'Entrada' else 0, axis=1)
df['Saidas'] = df.apply(lambda row: row['quantidade'] if row['tipo_transacao'] == 'Saída' else 0, axis=1)

agrupado = df.groupby(['estudo', 'produto', 'validade', 'lote']).agg(
    Entradas=('Entradas', 'sum'),
    Saidas=('Saidas', 'sum')
).reset_index()

agrupado['Saldo Total'] = agrupado['Entradas'] - agrupado['Saidas']

agrupado['Farol'] = agrupado['validade'].apply(farol)
agrupado = agrupado.sort_values(by=['estudo', 'produto', 'validade', 'lote'], na_position="last")
agrupado.fillna(0, inplace=True)
agrupado['Entradas'] = agrupado['Entradas'].astype(int)
agrupado['Saidas'] = agrupado['Saidas'].astype(int)
agrupado['Saldo Total'] = agrupado['Saldo Total'].astype(int)

if not agrupado.empty:
    st.dataframe(agrupado[['Farol', 'estudo', 'produto', 'validade', 'lote', 'Entradas', 'Saidas', 'Saldo Total']], width='stretch', hide_index=True,
                column_config={
        "Farol": st.column_config.Column(width="tiny"),
        "estudo": st.column_config.Column(width="small"),
        "produto": st.column_config.Column(width="medium"),
        "validade": st.column_config.Column(width="small"),
        "lote": st.column_config.Column(width="small"),
        "Entradas": st.column_config.Column(width="small"),
        "Saidas": st.column_config.Column(width="small"),
        "Saldo Total": st.column_config.Column(width="small")
    })

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