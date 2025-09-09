# database.py
from supabase_db import (
    supabase,
    obter_usuario,
    criar_usuario,
    atualizar_usuario,
    deletar_usuario,
    get_data,
    insert_data,
    update_data,
    delete_data,
    verificar_senha
)
import pandas as pd

def conectar():
    """Retorna o cliente Supabase. 'conn' será o objeto 'supabase'."""
    return supabase

def criar_tabelas():
    # Supabase: tabelas criadas manualmente.
    pass

def obter_saldo(estudo_id, produto_id, validade, lote):
    """
    Retorna o saldo atual (Entradas - Saídas) para a combinação
    Estudo + Produto + Validade + Lote, usando Supabase.
    Trata None, '' e 'N/A' como nulos.
    """
    query = (
        supabase
        .table("movimentacoes")
        .select("quantidade, tipo_transacao")
        .eq("estudo_id", estudo_id)
        .eq("produto_id", produto_id)
    )

    # --- Validade ---
    if validade in (None, "", "N/A"):
        query = query.is_("validade", "null")
    else:
        v = validade.isoformat() if hasattr(validade, "isoformat") else str(validade)
        query = query.eq("validade", v)

    # --- Lote ---
    if not lote:
        query = query.is_("lote", "null")
    else:
        query = query.eq("lote", str(lote))

    response = query.execute()

    if not getattr(response, "data", None):
        return 0

    df = pd.DataFrame(response.data)
    entradas = df.loc[df["tipo_transacao"] == "Entrada", "quantidade"].sum()
    saidas = df.loc[df["tipo_transacao"] == "Saída", "quantidade"].sum()
    return int(entradas - saidas)
