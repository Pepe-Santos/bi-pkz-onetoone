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
        │  views de leitura (vw_*) feitas pelo grupo de Dados
        ▼
trat            regras de tratamento: parâmetros, catálogo de testes, medidas padronizadas, revisão de dados
        │
        ▼
api             views expostas pela API REST do Supabase, filtradas pela unidade do usuário (contrato em docs/api.md)
        │
        ▼
Consumidores    relatórios em PDF e envio por e-mail · telas e dashboards · outros grupos
```

Tudo fica no **mesmo projeto Supabase**: o de ensaio do Lucas (`jhspjkelmnbvrnleawwf`, organização "Projeto BI org"), onde o grupo de Dados mantém o banco novo. Isso foi combinado com o grupo de Dados em 15/10.

- O Grupo de Desenvolvimento só cria objetos nos schemas `trat` e `api` e no bucket `relatorios`.
- Nunca escreve em `novo`, `origem` ou `public`.
- Lê o `novo` por views feitas pelo grupo de Dados, a pedido do Lucas (24/10). O Rafael passa ao Micael a lista, sem cálculo: `vw_aluno`, `vw_avaliacao_medida`, `vw_relatorio_treino` (sem os campos de dor) e `vw_agendamento`. O Iago criou as quatro no `013_views_consumo.sql` do grupo de Dados (27/10), e o `05` e o `06` leem a `vw_avaliacao_medida` e a `vw_aluno`. O grupo de Dados avisa no grupo se mudar a estrutura de uma tabela ou view que usamos.
- O grupo de Dados controla o banco pelo histórico de migrações do Supabase (`pkzbi_...`). Os scripts daqui **não** entram nesse histórico: rodam direto, pelo `psql` ou pelo SQL Editor.
- Quando existir o projeto Supabase definitivo (tarefa 3.6 do grupo de Dados), os mesmos scripts recriam tudo.

## Estrutura

```
backend/
├── sql/
│   ├── 01_schemas.sql                  schemas trat e api e leitura da API
│   ├── 03_storage.sql                  bucket privado relatorios para os PDFs
│   ├── 04_trat_parametros_catalogo.sql parâmetros de negócio e catálogo de regras por teste
│   ├── 05_trat_medidas.sql             medidas padronizadas, revisão de dados e resultado por teste
│   └── 06_api_avaliacoes.sql           views da API: atleta, evolucao, comparacao, reavaliacao
├── scripts/
│   ├── testar_acesso.py                os 3 testes de acesso à API (sem login, com login, secret key)
│   └── criar_usuario.py                cria um usuário da API já confirmado e com a unidade
├── docs/api.md                         contrato das views do schema api
├── exemplos/api/                       respostas de exemplo, com dados fictícios
├── agents/git_flow.md                  regras do agente de git
├── .mcp.json                           conexão somente leitura do Claude Code com o Supabase
└── env.example                         variáveis de ambiente (copiar para backend/.env)
```

O `02_fdw.sql` saiu em 20/10. Ele conectava a um banco remoto do grupo de Dados, o que deixou de ser necessário com o banco novo no mesmo projeto. A numeração dos outros scripts foi mantida.

## Estado em 24/10

- `01`, `03`, `04`, `05` e `06` aplicados no projeto do Lucas: schemas `trat` e `api`, bucket `relatorios` privado, 3 parâmetros, 20 testes no catálogo, medidas tratadas e as 4 views da API.
- API no ar: o schema `api` está em Exposed schemas e as 4 views (`atleta`, `evolucao`, `comparacao`, `reavaliacao`) respondem pela REST. Contrato em `docs/api.md`.
- Catálogo: recodificado com os códigos da `novo.metrica` (decidido em 20/10). Tem os testes físicos numéricos mais altura e peso, com faixas e conversões tiradas dos valores reais do `novo`. Os testes por perna (`single_hop`, `cross_hop`) saem com a coluna `lado` na API.
- Medidas: o `05` converte as unidades misturadas (ex.: 4,01 m e 543 cm viram cm), separa os valores impossíveis em `trat.revisao_dados` (37 tentativas) e escolhe a melhor tentativa válida. Lê a `novo.vw_avaliacao_medida` do grupo de Dados; a unidade e os dados do atleta vêm da `novo.vw_aluno` (matrícula vigente). Rode o `06` sempre depois do `05`: o `05` recria o `trat` e apaga as views da `api`.
- Acesso: cadastro público de usuários desligado; usuário de teste criado, com acesso às duas unidades; separação por unidade ativa (ver [API](#api)). Os 3 testes de acesso passam.
- Envio: nenhum aluno da cópia tem e-mail ligado (nem do responsável, nem próprio), então o envio automático é demonstrado com e-mails de teste.

## Como rodar os scripts

Os scripts podem rodar mais de uma vez (`IF NOT EXISTS` e `ON CONFLICT`). Também dá para colar cada um no SQL Editor do painel.

Linux / macOS, na raiz do repositório, com o `backend/.env` preenchido:

```bash
set -a; source backend/.env; set +a
psql "$SUPABASE_DB_URL" -f backend/sql/01_schemas.sql
psql "$SUPABASE_DB_URL" -f backend/sql/03_storage.sql
psql "$SUPABASE_DB_URL" -f backend/sql/04_trat_parametros_catalogo.sql
psql "$SUPABASE_DB_URL" -f backend/sql/05_trat_medidas.sql
psql "$SUPABASE_DB_URL" -f backend/sql/06_api_avaliacoes.sql
```

Windows (PowerShell), na raiz do repositório:

```powershell
$env:SUPABASE_DB_URL = "postgresql://postgres:SENHA@db.xxxx.supabase.co:5432/postgres"
psql "$env:SUPABASE_DB_URL" -f .\backend\sql\01_schemas.sql
psql "$env:SUPABASE_DB_URL" -f .\backend\sql\03_storage.sql
psql "$env:SUPABASE_DB_URL" -f .\backend\sql\04_trat_parametros_catalogo.sql
psql "$env:SUPABASE_DB_URL" -f .\backend\sql\05_trat_medidas.sql
psql "$env:SUPABASE_DB_URL" -f .\backend\sql\06_api_avaliacoes.sql
```

A string de conexão fica em **Connect**, no painel do Supabase.

## Segredos

- A `SUPABASE_SECRET_KEY` ignora todas as permissões. Só vai no `.env` do back-end e do gerador de relatórios.
- Nunca no GitHub, no front ou em chat. Se vazar: *Project Settings → API Keys*, gere outra e apague a antiga.
- O front usa apenas a publishable key.
- Este repositório é **público**: nada de dados do cliente, nem mesmo da cópia (veja as regras no README da raiz).

## API

- A API é a REST automática do Supabase: cada view do schema `api` vira um endpoint. Colunas, regras e exemplos estão em [`docs/api.md`](docs/api.md).
- O schema `api` está em *Project Settings → Data API → Exposed schemas* (24/10). Num projeto novo, incluir de novo: o `GRANT` do `01_schemas.sql` sozinho não basta. Como o projeto é compartilhado, combine com o Lucas antes de mudar essa configuração.
- Quem chama envia o cabeçalho `Accept-Profile: api`; sem ele o Supabase procura a view em `public`.
- Só recebem resposta o usuário logado (`authenticated`) e o gerador de relatórios (`service_role`, pela secret key). O papel `anon` não tem acesso ao schema. Como fazer login: seção "Login" do [`docs/api.md`](docs/api.md).
- **Usuários:** o cadastro público está desligado (*Authentication → Sign In / Providers → Allow new users to sign up*). Qualquer membro do grupo cria usuários pelo `scripts/criar_usuario.py` (já com a unidade) ou pelo painel: passo a passo em "Criar um usuário", no [`docs/api.md`](docs/api.md).
- **Separação por unidade:** cada usuário só vê os atletas da unidade gravada em `app_metadata.unidade` (`PKZ`, `ONE_TO_ONE` ou `TODAS`), gravada pelo `criar_usuario.py` ou pelo passo 4 de "Criar um usuário". Usuário sem unidade não vê nada; o gerador de relatórios vê tudo. O filtro fica em `trat.unidade_permitida`, no `06_api_avaliacoes.sql`.
- **Teste de acesso:** com o `backend/.env` preenchido, `python backend/scripts/testar_acesso.py` confere os 3 casos (sem login não devolve dados; com o usuário de teste e com a secret key, devolve) e mostra quantos atletas de cada unidade cada acesso vê.

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
