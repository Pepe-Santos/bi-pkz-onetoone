# Banco reestruturado (Frente 1 de Modelagem & Banco)

> Esta pasta (`dados/migracoes/`) era o repositório local `pkz-banco`. Todos os caminhos abaixo são relativos a ela: rode o `psql` **de dentro de `dados/migracoes/`**.

Banco modelado do Projeto BI (PKZ Lab / Playmakerz × Studio One to One): estrutura nova (DDL) e scripts que carregam os dados do app atual para ela.

Escopo do grupo: banco estruturado e carregado, pronto para consumo. Front-end, dashboards, relatórios e o app (Lovable) **não** são desta pasta.

Regras do grupo: [CONVENCOES.md](CONVENCOES.md). Leia antes do primeiro commit. Decisões em aberto: [PENDENCIAS.md](PENDENCIAS.md).

## Estrutura

```
migrations/   DDL do modelo novo, aplicado em ordem (001, 002, ...)
carga/        scripts de carga: 10 a 80 por domínio, 99 = mestre; _modelo.sql = ponto de partida
conferencia/  consultas de conferência por domínio
mapeamento/   de/para por domínio (uma linha por coluna de destino)
ensaio/       apoio para o ambiente de ensaio
```

## O ensaio

O ensaio roda na **cópia descaracterizada** do banco de produção, no projeto Supabase de ensaio do Lucas, com a concordância dele. A identificação do projeto e o acesso ficam no canal interno da equipe.

Dentro desse banco há três schemas que importam:

| Schema | O que é | Quem grava |
|---|---|---|
| `public` | As tabelas do app. **Continuam mudando**: duas rotinas automáticas rodam todo dia às 00:00 e 00:15 (Brasília) e mexem em `athletes`, `credit_transactions`, `notifications` e `student_timeline`. | **Ninguém do grupo.** Nem leitura nos scripts. |
| `origem` | **Foto congelada** das 28 tabelas de `public`, tirada em 12/10/2026 com `ensaio/congelar_origem.sql`. Mesmos nomes de tabela e coluna. | Ninguém. Os scripts só leem daqui. |
| `novo` | Destino: modelo novo + infraestrutura de carga. | Migrations e scripts de carga. |

As contagens da foto estão em `novo.carga_gabarito` (rótulo `congelamento-2026-10-12`). A conferência compara com elas.

O destino definitivo é um **projeto Supabase separado**. Lá o arranjo vai ser o mesmo (dump da produção em `public` → `congelar_origem.sql` → migrations → carga), então os scripts rodam sem mudança.

### Já feito (12/10)

- `migrations/001_infra_carga.sql` aplicado (migration `pkzbi_001_infra_carga`).
- `ensaio/congelar_origem.sql` executado: 28 tabelas em `origem`, contagens iguais às de `public` no momento da foto, RLS ligado, sem acesso para `anon`/`authenticated`. `novo` e `origem` não estão expostos na API.

### 13/10 — DDL do modelo (tarefa 1.2)

- `migrations/002` a `008`: 40 tabelas e 4 views do modelo, um arquivo por domínio. As escolhas de cada um estão no cabeçalho do arquivo e resumidas em [PENDENCIAS.md](PENDENCIAS.md).
- `conferencia/00_estrutura_ddl.sql`: confere RLS, índice de FK, colunas padrão e comentário de origem. As 4 primeiras consultas devem voltar vazias.
- `ensaio/limpar_tabelas_avulsas.sql`: rodado uma vez antes do 002. Renomeou para `avulsa_*` as 4 tabelas criadas fora das migrations (dados guardados); apagar depois, quando o grupo confirmar.
- Aplicado no ensaio em 13/10 (migrations `pkzbi_002` a `pkzbi_008`), idêntico aos arquivos (md5 conferido).

### 14/10 — Mapeamento de/para (tarefa 1.3)

- `mapeamento/`: um CSV por script de carga (10 a 80) + catálogo de métricas. Formato e achados em [mapeamento/README.md](mapeamento/README.md). Conferido: todas as colunas de `novo` mapeadas e todas as 365 colunas de `origem` com destino ou decisão de não migrar.
- `migrations/009_ajuste_mapeamento.sql`: ajustes no DDL que o mapeamento pediu (grade compartilhada, intervalo, capacidade pela duração, 2 colunas de configuração). Aplicado no ensaio em 15/10.
- `ensaio/origem_estrutura_local.sql` ganhou as 2 colunas novas de `app_settings`.

### 15/10 — Revisão das tarefas 1.1–1.3

- Dois revisores (DDL e mapeamento) conferiram tudo; os ajustes entraram na **009** (capacidade no intervalo inteiro, especializado sem grade = 1 compartilhada, modo de carga restrito ao papel `postgres`, truncate bloqueado nas avaliações, chave da renovação com periodicidade, plano da mesma unidade da matrícula, correção de avaliação coerente, `search_path` fixo, funções do 001 mais robustas) e no mapeamento.
- `ensaio/origem_estrutura_local.sql` agora é igual à foto coluna a coluna (365 colunas, tipo e nulo conferidos).

### 15/10 — Carga de referência e cadastro (tarefa 1.4)

- `carga/10_carga_referencia.sql` e `carga/20_carga_cadastro.sql` rodados no ensaio **duas vezes**, contagens iguais: referência 33 linhas; cadastro 258 pessoas, 152 perfis, 153 papéis de usuário, 106 alunos, 254 serviços de aluno, 106 vínculos de responsável, 31 profissionais (5 admins atuando, com pendência), 32 serviços de profissional; 0 rejeitados.
- `migrations/010_rejeitado_sem_delete.sql`: chave única no registro de rejeitados. Os scripts não usam mais `delete` (o conector do Supabase trava em `delete`/`drop` esperando uma confirmação que não aparece no app).
- `ensaio/dados_inventados.sql`: dados fictícios para testar os scripts localmente.

### 15/10 — Carga comercial, agenda e relatórios (tarefa 1.5)

- `carga/30`, `40` e `50` rodados no ensaio **duas vezes**, contagens iguais, 0 rejeitados:
  - comercial: 106 matrículas, 968 renovações, 1155 lançamentos de crédito (= origem);
  - agenda: grade 37, bloqueios 36 (34 ligados à grade), 536 agendamentos (= origem; 0 fora da grade, 2 acima da capacidade), 224 sessões de treino, 0 na lista de espera, 169 feedbacks (= origem);
  - relatório: 72 itens de catálogo (5 não classificados), 228 relatórios (= origem; 19 duplicados para o mesmo agendamento), 912 itens de relatório.
- `migrations/011_saldo_nao_cumulativo.sql` (aplicada): **créditos não são cumulativos**. A renovação redefine o saldo em vez de somar, então `vw_saldo_credito` passou a somar só os lançamentos desde a última renovação. Com a regra antiga, 104 dos 106 alunos davam saldo diferente; com a nova, 3 dos 318 pares (aluno, serviço), em 3 alunos (pendência 13). Essa conferência tem universo e critério diferentes da conferência 5 da tarefa 2.1: ver "Saldo de créditos: as duas conferências" em [mapeamento/README.md](mapeamento/README.md) e `conferencia/03_saldo_credito.sql`.

### 16/10 — Carga de avaliação, atendimento e documentos (tarefa 1.6)

- `carga/60`, `70` e `80` rodados no ensaio **duas vezes**, contagens iguais, 0 rejeitados:
  - avaliação: 109 métricas, 59 testes físicos e 1 avaliação semanal (= origem), 2719 medidas (= todos os valores não vazios da origem: 2635 do `data` + 79 de altura/peso + 5 notas). Com pendência: 70 pelo limiar provisório (5 sessões de hop, 10 de VO2), 38 alturas ambíguas, 3 valores do formato antigo do blazepod;
  - atendimento: 4 avaliações de fisioterapia (= origem) com 189 medidas (12 de goniometria + 12 de Appley + 165 do `pkz_data`), 4 anamneses, 22 atendimentos e 22 evoluções (7 + 15 = origem); 11 agendamentos de especialista com presença e sem atendimento marcados (pendência 12);
  - documentos: 523 arquivos (= caminhos distintos da origem; 39 clínicos; 205 ligados a relatório, 12 a avaliação, 22 a atendimento), 1389 eventos de auditoria (1163 + 226 = origem), 40 com dado pessoal tirado do payload. Conferido: nenhum payload ficou com `athlete_name`, `phone`, `full_name` ou `username`.
- `ensaio/dados_inventados.sql` ganhou casos para 60–80 (lista antiga do blazepod, chave sem métrica, sufixo `_dir` da postura, Appley 'Não avaliado', caminho de dois alunos, dado pessoal no payload...).

### 16/10 — Script mestre e ensaio geral (tarefa 1.7)

- `carga/99_carga_mestre.sql`: roda 10 a 80 em ordem (psql, `\i`) e termina com `conferencia/99_conferencia_geral.sql`.
- `conferencia/99_conferencia_geral.sql` (só leitura): origem × destino por tabela (`linhas_origem = linhas_destino + rejeitados`, coluna `ok`), arquivos × caminhos distintos, rejeitados por motivo, pendências por tabela e última execução de cada script.
- **Ensaio geral feito em 16/10** no ensaio, do zero:
  1. o `novo` antigo foi guardado como `novo_pre_ensaio_geral` (renomeado, não apagado: o conector trava em `drop schema`);
  2. migrations 001–011 aplicadas num `novo` vazio (`pkzbi_eg_001` a `pkzbi_eg_011`) → 43 tabelas, 5 views, as 4 regras de estrutura do `00_estrutura_ddl.sql` sem nenhuma violação, todas as funções com `search_path` fixo;
  3. gabarito `congelamento-2026-10-12` registrado de novo: igual ao antigo nas 28 tabelas;
  4. cargas 10–80 rodadas **duas vezes**: as 19 linhas da conferência origem × destino com `ok`, 0 rejeitados, e a "foto" das 41 tabelas (linhas e pendências) idêntica nas duas rodadas.
- Falta: o grupo confirmar e alguém apagar `novo_pre_ensaio_geral` pelo SQL Editor (ver "Ensaio geral" abaixo).

### 21/10 — Respostas à revisão do PR #5 (Rafael)

O PR #5 entrou na `main` em 21/10, com estas respostas. Três conferências novas, só de leitura, e a documentação que a revisão pediu:

- `conferencia/01_cobertura_mapeamento.py`: refaz, de forma reproduzível, a conferência de cobertura do mapeamento contra o `information_schema` e classifica cada coluna (direta, transformada, gerada, não migrada). Resultado: 365/365 colunas da origem e 451/451 do destino, 0 erros. Ver "Como refazer a conferência" em [mapeamento/README.md](mapeamento/README.md).
- `conferencia/02_papel_unidade.sql`: quais papéis são globais (`unidade_id` nula = todas as unidades) e quais são por unidade; 135 globais e 18 por unidade, 0 violações. Ver "Papéis e unidade". O `professor` sem sufixo virou a pendência 15.
- `conferencia/03_saldo_credito.sql`: a ponte entre a conferência de saldo da carga 30 e a conferência 5 da tarefa 2.1. Ver "Saldo de créditos: as duas conferências".

Nada muda no DDL nem nos scripts de carga.

### 26/10 — Políticas de acesso (migration 012, Frente 3)

- `migrations/012_politicas_rls.sql` (Iago, revisada pela Frente 1): grants mínimos (`anon` fora), 10 funções de escopo e uma política de leitura por tabela em 38 tabelas; `evento_auditoria`, `acesso_dado_sensivel` e as 3 `carga_*` ficam fechadas para a API. Matriz em [`../seguranca/matriz-papeis.md`](../seguranca/matriz-papeis.md).
- Testada em 25/10 numa transação desfeita no fim e aplicada no ensaio em 26/10 (migration `pkzbi_012_politicas_rls`, idêntica ao arquivo). Teste por papel: admin vê tudo; recepção, professores e responsável não veem dado clínico; o especialista só vê o clínico do próprio serviço e dos alunos que atende; `anon` não tem acesso ao schema.
- Não muda dado: a carga roda com papel privilegiado e passa por cima do RLS. As pendências 5 e 11 ficam na versão mais fechada até a direção decidir.

### Rodar pelo Claude (conector do Supabase)

Os scripts rodam pelo `execute_sql` sem a linha `\set ON_ERROR_STOP on`. Não colocar `delete`, `drop table` nem `truncate` em script de carga: o conector segura o comando e ele nunca roda. DDL vai por `apply_migration`.

### Refazer a foto (só se o grupo combinar)

Refazer a foto muda o gabarito de todo mundo. Combine antes.

```sql
drop schema origem cascade;
-- depois rodar ensaio/congelar_origem.sql (gera um rótulo novo com a data do dia;
-- se for no mesmo dia, apague antes o gabarito antigo: delete from novo.carga_gabarito where rotulo = '...')
```

## Rodar

Duas formas:

- **Editor SQL do Supabase** (painel do projeto → *SQL Editor*): cole o conteúdo do arquivo e rode. Funciona para migrations e scripts isolados. Tire a linha `\set ON_ERROR_STOP on`, que é comando do `psql`.
- **`psql`** (necessário para o script mestre, que usa `\i`). No Windows: instalador do PostgreSQL 16+, marcando só *Command Line Tools*. A string de conexão fica no painel (*Connect* → *Session pooler*) e vai numa variável de ambiente, **nunca em arquivo do repositório**:
  ```powershell
  $env:ENSAIO_URL = "postgresql://postgres.xxxx:SENHA@aws-0-us-east-1.pooler.supabase.com:5432/postgres"
  psql $env:ENSAIO_URL -f carga/60_carga_avaliacao.sql
  psql $env:ENSAIO_URL -f carga/99_carga_mestre.sql      # de dentro de dados/migracoes
  ```
  A senha do banco é do Dev Lucas: peça a ele, não salve em lugar compartilhado.

**Ensaio geral** (antes de entregar; refeito sempre que uma migration mudar):

1. Tirar o `novo` atual do caminho. Pelo SQL Editor ou psql: `drop schema novo cascade;`. Pelo Claude (o conector trava em `drop`): `alter schema novo rename to novo_pre_ensaio_<data>;` e apagar esse schema depois, pelo SQL Editor: `drop schema novo_pre_ensaio_<data> cascade;`.
2. Aplicar as migrations **001 a 012**, em ordem (os scripts de carga dependem da 009, 010 e 011; a 012, de políticas, não muda dado).
3. Registrar o gabarito de novo: `select novo.registrar_gabarito('congelamento-2026-10-12');` (`origem` não muda).
4. Rodar `conferencia/00_estrutura_ddl.sql`: as 4 primeiras consultas voltam vazias.
5. Rodar o mestre (`psql $env:ENSAIO_URL -f carga/99_carga_mestre.sql`, de dentro de `dados/migracoes`). A conferência no fim precisa ter `ok` em todas as linhas.
6. Rodar o mestre **de novo**: nenhuma contagem pode mudar.

> Apagar o `novo` antigo também apaga as tabelas `avulsa_*` (sobras de antes de 13/10). Desde 16/10 elas estão em `novo_pre_ensaio_geral`; se o grupo ainda quiser os dados delas, exporte antes de apagar.

## Teste rápido sem o ensaio

`ensaio/origem_estrutura_local.sql` recria **só a estrutura** das 28 tabelas (sem dados), gerada dos metadados do backup de 26/08. Serve para testar sintaxe num Postgres local com dados inventados: rode-o, depois `001_infra_carga.sql`, depois `congelar_origem.sql`.

## Nunca vai para o Git

Dados (CSV, dumps, planilhas com dados), `.env`, chaves, senhas, strings de conexão e o conteúdo do backup do app. O repositório é **privado** (desde 21/10), mas a regra continua: nada de dado pessoal nem credencial. O `.gitignore` desta pasta só libera os CSV de `mapeamento/` (estrutura, sem dados); o resto segue o `.gitignore` da raiz. O `.gitignore` cobre os casos comuns, mas a responsabilidade é de quem faz o commit.
