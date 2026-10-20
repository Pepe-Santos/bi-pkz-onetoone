# Desenvolvimento: back-end

**Branch:** `backend` · **Grupo:** Desenvolvimento · **Membros:** Ewerton Arrais (gerente), Miguel Veiga, Gian, Henrique, Christian, Rafael

O Grupo de Desenvolvimento cuida da área de tratamento de dados, da API que será consumida e da automação da geração e do envio dos relatórios por e-mail. Esta pasta guarda a parte de back-end; os relatórios ficam em [`relatorios/`](../relatorios/) e as telas em [`frontend/`](../frontend/), todos na mesma branch.

> **Origem deste código.** Até 20/10/2026 o Grupo de Desenvolvimento trabalhava em [`migsv/Proj-BI`](https://github.com/migsv/Proj-BI) (criado pelo Miguel Veiga em 13/10) e no fork [`ewerside/Proj-BI-dev`](https://github.com/ewerside/Proj-BI-dev) (Ewerton Arrais). O histórico foi trazido para cá com os autores originais. Como os arquivos ficavam na raiz daquele repositório, o histórico de cada um aparece com `git log --follow -- backend/<arquivo>` (ex.: `backend/sql/03_storage.sql`), ou no histórico completo da branch `backend`.

## Como o back-end se encaixa

```
Banco do app (Lovable / Supabase)
        │  foto congelada + carga feitas pelo grupo de Dados
        ▼
novo            banco novo do grupo de Dados (o Grupo de Desenvolvimento só lê)
        │  views de leitura publicadas pelo grupo de Dados (tarefa 3.4 deles)
        ▼
trat            regras de tratamento: parâmetros, catálogo de testes, medidas padronizadas
        │
        ▼
api             views expostas pela API REST do Supabase (contrato em docs/api.md)
        │
        ▼
Consumidores    relatórios em PDF e envio por e-mail · telas e dashboards · outros grupos
```

Tudo fica no **mesmo projeto Supabase**: o de ensaio do Lucas (`jhspjkelmnbvrnleawwf`, organização "Projeto BI org"), onde o grupo de Dados mantém o banco novo. Isso foi combinado com o grupo de Dados em 15/10.

- O Grupo de Desenvolvimento só cria objetos nos schemas `trat` e `api` e no bucket `relatorios`.
- Nunca escreve em `novo`, `origem` ou `public`.
- O grupo de Dados controla o banco pelo histórico de migrações do Supabase (`pkzbi_...`). Os scripts daqui **não** entram nesse histórico: rodam direto, pelo `psql` ou pelo SQL Editor.
- Quando existir o projeto Supabase definitivo (tarefa 3.6 do grupo de Dados), os mesmos scripts recriam tudo.

## Estrutura

```
backend/
├── sql/
│   ├── 01_schemas.sql                  schemas trat e api e leitura da API
│   ├── 03_storage.sql                  bucket privado relatorios para os PDFs
│   └── 04_trat_parametros_catalogo.sql parâmetros de negócio e catálogo de regras por teste
├── docs/api.md                         contrato das views do schema api
├── exemplos/api/                       respostas de exemplo, com dados fictícios
├── agents/git_flow.md                  regras do agente de git
├── .mcp.json                           conexão somente leitura do Claude Code com o Supabase
└── env.example                         variáveis de ambiente (copiar para backend/.env)
```

O `02_fdw.sql` saiu em 20/10. Ele conectava a um banco remoto do grupo de Dados, o que deixou de ser necessário com o banco novo no mesmo projeto. A numeração dos outros scripts foi mantida.

## Estado em 20/10

- `01`, `03` e `04` aplicados no projeto do Lucas: schemas `trat` e `api`, bucket `relatorios` privado, 3 parâmetros e 10 testes no catálogo.
- Views da `api`: contrato em `docs/api.md`, ainda não criadas. Vão ler as views de leitura do grupo de Dados.
- Catálogo: a `novo.metrica` já traz unidade e direção dos 19 testes físicos, mas não traz faixa plausível nem regra de conversão, e os códigos são outros (`sprint_20` lá, `sprint_20m` aqui). O alinhamento está pendente com o grupo de Dados.

## Como rodar os scripts

Os scripts podem rodar mais de uma vez (`IF NOT EXISTS` e `ON CONFLICT`). Também dá para colar cada um no SQL Editor do painel.

Linux / macOS, na raiz do repositório, com o `backend/.env` preenchido:

```bash
set -a; source backend/.env; set +a
psql "$SUPABASE_DB_URL" -f backend/sql/01_schemas.sql
psql "$SUPABASE_DB_URL" -f backend/sql/03_storage.sql
psql "$SUPABASE_DB_URL" -f backend/sql/04_trat_parametros_catalogo.sql
```

Windows (PowerShell), na raiz do repositório:

```powershell
$env:SUPABASE_DB_URL = "postgresql://postgres:SENHA@db.xxxx.supabase.co:5432/postgres"
psql "$env:SUPABASE_DB_URL" -f .\backend\sql\01_schemas.sql
psql "$env:SUPABASE_DB_URL" -f .\backend\sql\03_storage.sql
psql "$env:SUPABASE_DB_URL" -f .\backend\sql\04_trat_parametros_catalogo.sql
```

A string de conexão fica em **Connect**, no painel do Supabase.

## Segredos

- A `SUPABASE_SECRET_KEY` ignora todas as permissões. Só vai no `.env` do back-end e do gerador de relatórios.
- Nunca no GitHub, no front ou em chat. Se vazar: *Project Settings → API Keys*, gere outra e apague a antiga.
- O front usa apenas a publishable key.
- Este repositório é **público**: nada de dados do cliente, nem mesmo da cópia (veja as regras no README da raiz).

## API

- A API é a REST automática do Supabase: cada view do schema `api` vira um endpoint. Colunas, regras e exemplos estão em [`docs/api.md`](docs/api.md).
- Para o schema `api` aparecer na API, ele precisa estar em *Project Settings → Data API → Exposed schemas*. O `GRANT` do `01_schemas.sql` sozinho não basta. Como o projeto é compartilhado, combine com o Lucas antes de mudar essa configuração.
- Quem chama envia o cabeçalho `Accept-Profile: api`; sem ele o Supabase procura a view em `public`.
- Só usuário logado (`authenticated`) recebe resposta. O papel `anon` não tem acesso ao schema.

## Storage

- O bucket `relatorios` é privado (criado pelo `03_storage.sql`).
- Os PDFs são acessados por URL assinada, gerada pelo back-end.

## Claude + Supabase (MCP)

O arquivo `backend/.mcp.json` conecta o Claude Code ao projeto Supabase do Lucas, **somente leitura** (`read_only=true`) e limitado a esse projeto (`project_ref`). Ele não guarda nenhum segredo.

1. Instale o Claude Code (PowerShell): `irm https://claude.ai/install.ps1 | iex`. Se o comando `claude` não for reconhecido, adicione `C:\Users\<seu_usuario>\.local\bin` ao PATH do usuário e abra um terminal novo.
2. **Dentro da pasta `backend/`**, rode `claude`. Quando ele perguntar sobre o servidor `supabase`, escolha **"Use this MCP server"**.
3. Digite `/mcp`, escolha `supabase` e depois *Authenticate*. Entre com **a sua conta do Supabase**.
4. Teste pedindo: "liste as tabelas dos schemas trat, api e novo".

Para acessar o projeto, a pessoa precisa ser membro da organização "Projeto BI org" no Supabase (peça ao Lucas). Mantenha o `read_only=true`: sem ele, o Claude consegue alterar e apagar dados de todos os grupos.

## Fluxo de git

As regras completas estão em [`agents/git_flow.md`](agents/git_flow.md). Em resumo:

- Cada tarefa ganha uma branch própria, criada a partir da `backend`: `<tipo>/<assunto>` (ex.: `feat/views-avaliacao`), com PR de volta para a `backend`.
- Não use nome de branch começando com `backend/`: o git recusa criar `backend/...` enquanto existir a branch `backend`.
- A `backend` vai para a `main` por PR, revisado pela gerência.
- Mudança em view da `api` = PR revisado também por Dados e QA.
- Teste com dados sintéticos; nada da produção ou da cópia no repositório.

**Fora do escopo:** cadastro, agenda, login e cobrança, que continuam no app do cliente; carga e modelagem do banco novo, que são do grupo de Dados.
