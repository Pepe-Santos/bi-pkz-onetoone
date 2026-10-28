# API de avaliações (schema `api`)

Contrato das views que o Grupo de Desenvolvimento expõe pela API REST do Supabase para o gerador de relatórios e para os outros consumidores internos da empresa.

**Estado:** provisório. As views são criadas pelo `sql/06_api_avaliacoes.sql` (24/10) e, as de treino, pelo `sql/08_api_treinos.sql` (28/10). Os nomes das colunas não mudam sem aviso no grupo. Os valores de exemplo são fictícios (`exemplos/api/`). As regras por teste (unidade, direção, faixa plausível) ficam marcadas como **não confirmadas** até a PKZ validar o catálogo.

## Como chamar

A API é a REST automática do Supabase (PostgREST). Cada view vira um endpoint:

```
GET {SUPABASE_URL}/rest/v1/<view>?<filtros>
```

Cabeçalhos obrigatórios:

| Cabeçalho | Valor |
|---|---|
| `apikey` | chave do projeto (publishable no front; secret só no backend) |
| `Authorization` | `Bearer <token>`: JWT do usuário logado, ou a secret key no gerador de relatórios |
| `Accept-Profile` | `api` (sem isso o PostgREST procura a view em `public`) |

Sem login não há resposta: o schema `api` só tem permissão para os papéis `authenticated` (usuário logado) e `service_role` (secret key). Para o schema aparecer na API, ele precisa estar em **Project Settings → Data API → Exposed schemas** no painel do Supabase.

Filtros seguem a sintaxe do PostgREST: `?atleta_id=eq.<uuid>`, `&order=data_avaliacao.asc`, `&select=teste,valor`.

Cada chamada devolve no máximo 1.000 linhas (limite do Supabase). Filtre por `atleta_id`; para ler tudo, pagine com `&limit=1000&offset=1000`.

### Login (dashboard e testes)

Quem não é o gerador de relatórios entra com e-mail e senha de um usuário do Supabase (*Authentication → Users*). A senha do usuário de teste é passada em particular, nunca no GitHub.

1. Pedir o token, com a publishable key:

```
POST {SUPABASE_URL}/auth/v1/token?grant_type=password
apikey: <publishable key>
Content-Type: application/json

{"email": "<e-mail>", "password": "<senha>"}
```

2. A resposta traz `access_token` (vale 1 hora) e `refresh_token`. Chamar as views com o token:

```
GET {SUPABASE_URL}/rest/v1/atleta
apikey: <publishable key>
Authorization: Bearer <access_token>
Accept-Profile: api
```

3. Quando o token vencer, a API responde `401`. Pedir outro com `POST /auth/v1/token?grant_type=refresh_token` e o corpo `{"refresh_token": "<refresh_token>"}`, ou fazer login de novo.

No front, a biblioteca `supabase-js` faz o login e renova o token sozinha:

```js
const supabase = createClient(SUPABASE_URL, PUBLISHABLE_KEY, { db: { schema: "api" } });
await supabase.auth.signInWithPassword({ email, password });
const { data } = await supabase.from("evolucao").select("*").eq("atleta_id", atletaId);
```

### Criar um usuário

O cadastro público está desligado: qualquer membro do grupo cria os usuários, de um destes dois jeitos.

**Pelo script (um passo só).** Precisa da `SUPABASE_SECRET_KEY` no `backend/.env`. Cria o usuário já confirmado e com a unidade:

```
python backend/scripts/criar_usuario.py <email> <senha> <PKZ|ONE_TO_ONE|TODAS>
```

Se o e-mail já existir, o script avisa e não muda nada; para trocar a unidade de quem já existe, use o passo 4 abaixo.

**Pelo painel do Supabase.** O formulário do painel não tem campo para a unidade, então são dois passos (criar e depois definir a unidade):

1. No projeto do Supabase, abra **Authentication → Users**.
2. Clique em **Add user → Create new user**.
3. Preencha o e-mail e a senha e deixe **Auto Confirm User** marcado (sem isso o login falha). Clique em **Create user**.
4. Defina a unidade que o usuário pode ver. No **SQL Editor**, rode o comando abaixo trocando o e-mail e a unidade (`PKZ`, `ONE_TO_ONE` ou `TODAS`):

```sql
UPDATE auth.users
SET raw_app_meta_data = coalesce(raw_app_meta_data, '{}'::jsonb) || '{"unidade": "PKZ"}'
WHERE email = '<e-mail do usuário>';
```

5. Faça login com o usuário (passos acima). Se ele já estava logado quando a unidade mudou, faça login de novo: a unidade só vale a partir do próximo login.

Cada usuário só vê os atletas da sua unidade. Usuário sem unidade (passo 4 esquecido) não vê nada; o gerador de relatórios vê as duas unidades. Já existe um usuário de teste com `TODAS`, usado nos testes de acesso.

O `backend/scripts/testar_acesso.py` confere os três casos: sem login (não devolve dados), com o usuário de teste e com a secret key (devolvem). Ele lê as variáveis do `backend/.env`.

### Gerador de relatórios (secret key)

Exemplo em Python, com a secret key:

```python
import os, requests

base = os.environ["SUPABASE_URL"] + "/rest/v1/"
key = os.environ["SUPABASE_SECRET_KEY"]
headers = {"apikey": key, "Authorization": f"Bearer {key}", "Accept-Profile": "api"}

atleta_id = "a1b2c3d4-0000-4000-8000-000000000001"
comparacao = requests.get(base + "comparacao", headers=headers,
                          params={"atleta_id": f"eq.{atleta_id}"}).json()
evolucao = requests.get(base + "evolucao", headers=headers,
                        params={"atleta_id": f"eq.{atleta_id}", "order": "data_avaliacao.asc"}).json()
```

A resposta é sempre um array JSON de linhas, no mesmo formato dos arquivos em `exemplos/api/`. Enquanto a API não existe, o gerador lê esses arquivos.

## Views

### `atleta`: identificação e filtros

Uma linha por atleta. É a única view com nome; as de desempenho não trazem nome, para que a IA receba só id, idade e números.

| Coluna | Tipo | Descrição |
|---|---|---|
| `atleta_id` | uuid | id do atleta no banco novo |
| `unidade` | text | `PKZ` ou `ONE_TO_ONE` |
| `nome` | text | nome do atleta |
| `idade` | int | idade em anos na data da consulta |
| `categoria` | text | categoria do cadastro; pode ser nulo |
| `ativo` | bool | atleta ativo no app |
| `total_avaliacoes` | int | avaliações físicas com pelo menos uma medida válida |
| `ultima_avaliacao_em` | date | data da última avaliação; nulo se nunca avaliado |

Exemplo: `exemplos/api/atleta.json`.

### `evolucao`: histórico de cada teste do atleta

Uma linha por atleta, avaliação, teste e lado. O valor é a **melhor tentativa válida** da avaliação (menor tempo ou maior distância), já na unidade padrão do catálogo. Avaliação sem tentativa válida para um teste não gera linha: o valor foi para `revisao_dados`.

| Coluna | Tipo | Descrição |
|---|---|---|
| `atleta_id` | uuid | |
| `avaliacao_id` | uuid | id da avaliação no banco novo |
| `data_avaliacao` | date | |
| `teste` | text | código do teste, igual ao `novo.metrica.codigo` (ex.: `sprint_20`) |
| `teste_nome` | text | nome para exibir |
| `lado` | text | `dir` ou `esq` nos testes feitos com cada perna (`single_hop`, `cross_hop`); nulo nos demais |
| `unidade_medida` | text | `s`, `ms`, `cm`, `m`, `km/h`, `kg`, `hits` ou `desequilibrios` |
| `maior_melhor` | bool | `true`: maior valor é melhor; `false`: menor é melhor |
| `confirmado` | bool | `true` só depois que a PKZ validou a regra do teste |
| `valor` | numeric | melhor tentativa válida, na unidade padrão |
| `tentativas_validas` | int | quantas tentativas entraram na escolha |

Serve para o gráfico de evolução: filtrar por `atleta_id`, agrupar por `teste` e `lado`, ordenar por `data_avaliacao`.

Exemplo: `exemplos/api/evolucao.json`.

### `comparacao`: avaliação atual contra a anterior

Uma linha por atleta, teste e lado, comparando a última avaliação com a imediatamente anterior em que o teste tem valor válido.

| Coluna | Tipo | Descrição |
|---|---|---|
| `atleta_id` | uuid | |
| `teste`, `teste_nome`, `lado`, `unidade_medida`, `maior_melhor`, `confirmado` | | como em `evolucao` |
| `data_anterior` | date | nulo quando só existe uma avaliação do teste |
| `valor_anterior` | numeric | idem |
| `data_atual` | date | |
| `valor_atual` | numeric | |
| `variacao_abs` | numeric | `valor_atual - valor_anterior`, na unidade do teste |
| `variacao_pct` | numeric | `(valor_atual - valor_anterior) / valor_anterior * 100`, 1 casa decimal; nulo quando o valor anterior é 0 (ex.: Aquabag sem desequilíbrio) |
| `situacao` | text | `melhorou`, `piorou`, `estavel`, `sem_classificacao` ou `sem_comparacao` |

Regras de `situacao`:

- `estavel`: `abs(variacao_pct)` abaixo do parâmetro `variacao_estavel_pct` (2% provisório), ou valor igual.
- `sem_classificacao`: mudou além do estável, mas o teste não tem direção (`maior_melhor` nulo: altura, peso e `slalom_wallball`, cuja direção ainda não foi definida).
- `melhorou` / `piorou`: pela direção do teste (`maior_melhor`). Variação negativa num teste de tempo é melhora.
- `sem_comparacao`: não há avaliação anterior com valor válido.

**Regra para o relatório dos pais:** escrever "melhorou" ou "piorou" só quando `confirmado = true`. Teste não confirmado aparece com os valores, sem classificação.

Exemplo: `exemplos/api/comparacao.json`.

### `reavaliacao`: reavaliações vencidas e a vencer

Uma linha por atleta com pelo menos uma avaliação. Ainda sem arquivo de exemplo.

| Coluna | Tipo | Descrição |
|---|---|---|
| `atleta_id` | uuid | |
| `unidade` | text | |
| `ultima_avaliacao_em` | date | |
| `vence_em` | date | `ultima_avaliacao_em + reavaliacao_dias` (90 provisório) |
| `dias_para_vencer` | int | negativo quando vencida |
| `situacao` | text | `vencida`, `a_vencer` (dentro de `reavaliacao_aviso_dias`, 30 provisório) ou `em_dia` |

### `presenca`: agendamentos de treino

Uma linha por agendamento de **treino** (só o serviço `treino`; fisioterapia, nutrição e os outros serviços não entram), até a data de hoje em São Paulo. Sem agregação: o gerador filtra o período por `data` (ex.: `?data=gte.2026-10-01&data=lte.2026-10-31`). A unidade é a do próprio agendamento. Criada pelo `sql/08_api_treinos.sql`; ainda sem arquivo de exemplo.

| Coluna | Tipo | Descrição |
|---|---|---|
| `agendamento_id` | uuid | id do agendamento no banco novo |
| `atleta_id` | uuid | como em `atleta` |
| `unidade` | text | `PKZ` ou `ONE_TO_ONE` |
| `data` | date | dia do treino |
| `hora_inicio` | time | |
| `status` | text | `agendado`, `presente`, `falta` ou `cancelado` |

O `aguardando_confirmacao` do banco novo aparece como `agendado`.

### `treino`: relatórios de treino

Uma linha por relatório de treino com status `final` (rascunhos não entram), até a data de hoje em São Paulo: relatórios com data no futuro só aparecem quando o dia chega. A unidade é a do próprio relatório. Criada pelo `sql/08_api_treinos.sql`; ainda sem arquivo de exemplo.

| Coluna | Tipo | Descrição |
|---|---|---|
| `relatorio_id` | uuid | id do relatório no banco novo |
| `atleta_id` | uuid | como em `atleta` |
| `unidade` | text | `PKZ` ou `ONE_TO_ONE` |
| `data` | date | dia do treino |
| `tipo_treino` | text | |
| `intensidade` | | como no banco novo |
| `objetivos` | text | texto livre do treinador |
| `desempenho` | text | idem |
| `observacoes` | text | idem |

Os campos de dor (`dor`, `dor_local`, `dor_intensidade`, `dor_movimento`) são dado de saúde e não são expostos.

## Parâmetros

Os números das regras ficam em `trat.parametro` (`04_trat_parametros_catalogo.sql`), para a PKZ ajustar sem mexer em código:

| Chave | Valor provisório |
|---|---|
| `variacao_estavel_pct` | 2 |
| `reavaliacao_dias` | 90 |
| `reavaliacao_aviso_dias` | 30 |

As regras por teste (unidade padrão, direção, faixa plausível, conversão, confirmado) ficam em `trat.catalogo_teste`, no mesmo script.

## O que ainda falta

- Confirmar com a PKZ a unidade, a direção e a faixa plausível de cada teste, e se algum teste usa média em vez da melhor tentativa.
- Origem dos dados (24/10, a pedido do Lucas): as views leem o banco novo por views de leitura que o grupo de Dados cria no `novo` (o Rafael passa a lista ao Micael), sem cálculo: `vw_aluno`, `vw_avaliacao_medida`, `vw_relatorio_treino` (sem os campos de dor) e `vw_agendamento`. Criadas pelo Iago em 27/10 (`013_views_consumo.sql` do grupo de Dados); as views desta API leem a `vw_avaliacao_medida` e a `vw_aluno`. A unidade (PKZ ou One to One) é a da matrícula vigente, como na `vw_aluno`: aluno sem matrícula vigente só aparece para quem vê `TODAS`. Campos de dor não entram nas views, na API nem nos relatórios.
- Códigos dos testes: decidido em 20/10 que o contrato usa os códigos do banco novo (`novo.metrica.codigo`). Em 24/10 o catálogo e os exemplos em `backend/exemplos/api/` passaram a usar esses códigos, ganharam a coluna `lado` e os testes que faltavam (Banco de Wells, Blazepod, os 3 saltos verticais, o restante do VO2 e o peso). A cópia em `exemplos/api/` na raiz, usada pelo gerador de relatórios, ainda está no formato antigo.
- Views de treino: `presenca` e `treino` (`sql/08_api_treinos.sql`) leem a `novo.vw_agendamento` e a `novo.vw_relatorio_treino`, aplicadas no ensaio em 28/10 (migrations 013 e 014 do grupo de Dados).
