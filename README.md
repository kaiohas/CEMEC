# Controle de Estoque (Streamlit + SQLite)

Aplicação web para controle de estoque local com autenticação (gestor/visualizador), gestão de acessos, cadastro de variáveis/produtos, registro de movimentações e visão geral com farol e filtros.

---

## 🗂 Estrutura sugerida de pastas/arquivos

```text
.
├── app.py
├── database.py
├── 0_Gestão_de_Acessos.py
├── 1_movimentações.py
├── 2_Cadastro_de_Variáveis.py
├── 3_Cadastro_de_Produtos.py
├── 4_Visão_Geral.py
├── 5_Lançamentos.py
├── requirements.txt
└── estoque.db           # criado automaticamente ao rodar (SQLite)
```

> Dica: os arquivos `0_...`, `1_...`, etc. podem ficar na raiz **ou** dentro de uma pasta `pages/` (formato nativo do Streamlit). Se usar `pages/`, mantenha `app.py` na raiz e mova as páginas para `pages/`.

---

## ▶️ Rodando localmente

1. Crie e ative um ambiente virtual (opcional, mas recomendado).
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Execute o app:
   ```bash
   streamlit run app.py
   ```
4. Acesse no navegador: http://localhost:8501

> Primeiro login padrão (criado automaticamente): **admin / admin** (perfil gestor). Altere em **🔐 Gestão de Acessos**.

---

## ☁️ Publicando (Streamlit Community Cloud)

1. Suba o projeto para um repositório no **GitHub** (inclua `requirements.txt`).
2. Acesse [Streamlit Community Cloud](https://streamlit.io/cloud) → **Create app** → selecione seu repositório, branch e o arquivo principal (`app.py`).
3. *Advanced settings* (se solicitado), defina o comando de start (geralmente automático):
   ```bash
   streamlit run app.py --server.port $PORT --server.address 0.0.0.0
   ```
4. Clique em **Deploy**. Uma URL pública será gerada.

**Observações sobre SQLite em hosts gratuitos:**
- O arquivo `estoque.db` fica no disco do servidor do app. Em plataformas gratuitas, o armazenamento pode ser efêmero em rebuilds ou ao trocar de máquina. Para não perder dados:
  - Inclua recursos de **exportar/backup** (CSV/Excel) no app.
  - Considere migrar depois para um banco gerenciado (ex.: Postgres) se precisar de alta durabilidade ou acesso multiusuário simultâneo.
- O SQLite funciona bem para uso leve/local. Em uso concorrente alto, prefira um serviço de banco externo.

---

## 🚀 Publicando (Hugging Face Spaces)

1. Crie um **Space** novo em https://huggingface.co/spaces, escolha **SDK = Streamlit**.
2. Faça upload dos arquivos (ou conecte via GitHub).
3. Garanta que `requirements.txt` está no repositório. O build roda automaticamente e gera uma URL pública.

> Dica: segredos (se houver) podem ser definidos como **Repository secrets** no Space. Para este projeto (SQLite local), não há segredos obrigatórios.

---

## 🔒 Usuários e Papéis

- **Gestor:** acesso total (inclui **Gestão de Acessos**, **Movimentações**, **Cadastros** e **Lançamentos**).
- **Visualizador:** acesso à **Visão Geral**.
- O responsável de cada movimentação é o **usuário logado** (campo não editável).

> Tabela `users` é criada automaticamente com um usuário inicial `admin/admin` (gestor).

---

## 🧰 Requisitos e versões

- Python 3.10+ recomendado.
- Principais libs: `streamlit`, `pandas`, `numpy` (veja `requirements.txt`). `sqlite3` e `hashlib` são da biblioteca padrão do Python.

---

## 🆘 Dicas e Solução de Problemas

- **Erro `st.experimental_rerun`:** use `st.rerun()` nas versões recentes do Streamlit.
- **`sqlite3.OperationalError: database is locked`:** evite muitas gravações simultâneas. Feche conexões após uso; use uma conexão global com `check_same_thread=False` e `PRAGMA foreign_keys=ON`.
- **Atualizações de schema:** se alterar tabelas, crie migrações simples (ex.: scripts SQL para `ALTER TABLE`), e faça backup do `.db` antes.

---

## 📦 Roadmap (sugestões)

- Exportação de relatórios (CSV/Excel) respeitando filtros.
- Migração opcional para Postgres gerenciado em produção.
- Logs/audit trail de movimentações.
- Testes automatizados para regras de saldo/negativação.

---

## Licença

Uso interno. Adapte conforme necessidade do seu cliente (CEMEC).
