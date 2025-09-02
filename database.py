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

# Funções que você usava no seu código original
# Essas funções vão chamar as novas funções do Supabase
def conectar():
    """Retorna o cliente Supabase. 'conn' será o objeto 'supabase'."""
    return supabase

# Substituição de criar_tabelas
# O Supabase exige que você crie as tabelas manualmente pela interface
def criar_tabelas():
    # Não faz nada aqui, pois as tabelas são criadas manualmente no Supabase.
    # Vamos adaptar a lógica de criação do admin em app.py
    pass
    
def obter_saldo(estudo_id, produto_id, validade, lote):
    """
    Retorna o saldo atual (Entradas - Saídas) para a combinação
    Estudo + Produto + Validade + Lote, usando Supabase.
    """
    query = supabase.table("movimentacoes").select("quantidade, tipo_transacao")
    
    # Adicionando os filtros dinâmicos
    query = query.eq("estudo_id", estudo_id).eq("produto_id", produto_id)

    if validade:
        query = query.eq("validade", str(validade))
    else:
        query = query.is_("validade", "NULL")

    if lote:
        query = query.eq("lote", lote)
    else:
        query = query.is_("lote", "NULL")
        
    response = query.execute()

    # Calcular o saldo
    if not response.data:
        return 0
    
    df = pd.DataFrame(response.data)
    
    saldo = (df[df['tipo_transacao'] == 'Entrada']['quantidade'].sum() -
             df[df['tipo_transacao'] == 'Saída']['quantidade'].sum())

    return saldo