# Preflight do destino — Task 2.3 — 2026-10-21

- Script: `conferencia/sql/00_preflight_destino.sql` (branch `feat/conferencias-origem`, commit `d429749`)
- Destino: projeto Supabase `jhspjkelmnbvrnleawwf` ("DevLucasLSA's Project", org "Projeto BI org",
  ultima migration `pkzbi_eg_011_saldo_nao_cumulativo`), confirmado pelo responsavel no dashboard em 2026-10-21.
- Execucao: MCP `supabase` / `execute_sql`, somente SELECT em catalogos e contagens, etapas 1→10 em ordem.
- Nao executados neste preflight: INSERT/UPDATE/DELETE/DDL, migrations, `06_destino_carga.sql`. O `06` rodou
  depois, somente com SELECT e com autorizacao; ver `destino_carga_2026-10-21.md`.
- Conteudo: apenas metadados e contagens; sem tokens, senhas, strings de conexao ou dados pessoais.

## Resumo

| Etapa | Resultado | Bloqueio? |
|---|---|---|
| 1 Identidade da sessao | `postgres` / `supabase_read_only_user` / PG 17.6 | Nao |
| 2 Schemas | `novo` e `origem` existem, USAGE ok, sem CREATE | Nao |
| 3 Objetos essenciais | 39/39 `OK` | Nao |
| 4 Colunas criticas | 12 `OK`, 1 `NAO_VALIDADO` (`carga_rejeitado.id_origem` = uuid) | Nao |
| 5 View de saldo | `OK` | Nao |
| 6 Gabarito | `ROTULO_IDENTIFICADO_CONFIRMACAO_OPERACIONAL_PENDENTE` | Nao (confirmacao pendente) |
| 7 Esquema `carga_execucao` | PK `carga_execucao_pkey (id)` | Nao |
| 8 Historico dos scripts | 8/8 `INCONCLUSIVO_DESEMPATE_E_SEMANTICA_NAO_CONFIRMADOS` (por desenho) | Registrado, seguiu |
| 9 Permissoes e RLS | SELECT em todos; RLS habilitado; 0 policies | Ver observacao |
| 10 JSONB | 4 registros, 4 objetos, 0 nao-objeto | Nao |

Nenhuma etapa retornou AUSENTE, TIPO_INCOMPATIVEL, SELECT_INDISPONIVEL, GABARITO_INEXISTENTE,
INCONCLUSIVO_ROTULO_EMPATE ou SEM_TABELA_NO_GABARITO.

## 1) Identidade da sessao

| banco_atual | usuario_efetivo | usuario_da_sessao | schema_atual | endereco_servidor | porta_servidor | versao_postgresql |
|---|---|---|---|---|---|---|
| postgres | supabase_read_only_user | supabase_read_only_user | public | (IPv6, omitido) | 5432 | 17.6 |

`current_database()` nao identifica o projeto; identidade confirmada externamente (dashboard, 2026-10-21).
A sessao usa papel somente leitura.

## 2) Schemas e privilegios basicos

| schema_name | existe | possui_usage | possui_create_informativo |
|---|---|---|---|
| novo | true | true | false |
| origem | true | true | false |

## 3) Objetos essenciais de 06_destino_carga.sql

Todos os 39 objetos existem, com relkind esperado e SELECT disponivel (`preflight_status = OK`):

- `novo` (r): agendamento, aluno, aluno_servico, anamnese, arquivo, atendimento, avaliacao, bloqueio_agenda,
  carga_execucao, carga_gabarito, carga_rejeitado, catalogo_item, credito_lancamento, evento_auditoria,
  feedback_treino, horario_grade, lista_espera, matricula, papel, papel_usuario, perfil_usuario, pessoa, plano,
  profissional, profissional_servico, relatorio_treino, renovacao, servico, sessao_treino, unidade
- `novo` (v): vw_saldo_credito
- `origem` (r): nutritionist_files, physical_test_comparisons, physio_assessments, physio_evolutions,
  specialist_evolutions, student_files, student_tests, training_reports

## 4) Colunas criticas e tipos

| schema | tabela | coluna | regra | tipo_encontrado | status |
|---|---|---|---|---|---|
| novo | carga_execucao | executado_em | timestamp_ou_timestamptz | timestamp with time zone | OK |
| novo | carga_execucao | linhas_carregadas | numerico | integer | OK |
| novo | carga_execucao | linhas_rejeitadas | numerico | integer | OK |
| novo | carga_execucao | script | texto | text | OK |
| novo | carga_gabarito | linhas | numerico | bigint | OK |
| novo | carga_gabarito | registrado_em | timestamp_ou_timestamptz | timestamp with time zone | OK |
| novo | carga_gabarito | rotulo | texto | text | OK |
| novo | carga_gabarito | tabela | texto | text | OK |
| novo | carga_rejeitado | id_origem | numerico_ou_nao_validado | uuid | NAO_VALIDADO |
| novo | carga_rejeitado | motivo | texto | text | OK |
| novo | carga_rejeitado | script | texto | text | OK |
| novo | carga_rejeitado | tabela_origem | texto | text | OK |
| origem | physio_assessments | pkz_data | jsonb | jsonb | OK |

`NAO_VALIDADO` e previsto pelo script e nao e bloqueio. Observacao: `id_origem` e `uuid`, nao numerico.

## 5) View de saldo

| preflight_status | existe | relkind | possui_select | colunas_criticas_ausentes | colunas_com_tipo_incompativel |
|---|---|---|---|---|---|
| OK | true | v | true | 0 | 0 |

| coluna_critica | existe | tipo_encontrado |
|---|---|---|
| aluno_id | true | uuid |
| saldo | true | integer |
| servico_id | true | uuid |

## 6) Snapshot do gabarito

| preflight_status | existe_snapshot | rotulo_mais_recente | registrado_em_mais_recente | rotulos_no_timestamp_maximo | quantidade_tabelas | contagens_nulas | tabelas_nulas |
|---|---|---|---|---|---|---|---|
| ROTULO_IDENTIFICADO_CONFIRMACAO_OPERACIONAL_PENDENTE | true | congelamento-2026-10-12 | 2026-10-16 12:47:47.225627+00 | 1 | 28 | 0 | 0 |

Duplicidade de tabela no rotulo: nenhuma linha (sem duplicidade).

O rotulo foi registrado em 2026-10-16, quatro dias depois da data no nome, porque o gabarito foi registrado de
novo no ensaio geral de 16/10. Confirmacao em "Pendencias" (resolvido).

## 7) Esquema real de carga_execucao

| ordinal | coluna | data_type | udt_name | nullable |
|---|---|---|---|---|
| 1 | id | bigint | int8 | NO |
| 2 | script | text | text | NO |
| 3 | linhas_carregadas | integer | int4 | YES |
| 4 | linhas_rejeitadas | integer | int4 | YES |
| 5 | observacao | text | text | YES |
| 6 | executado_em | timestamp with time zone | timestamptz | NO |

| constraint | tipo | colunas |
|---|---|---|
| carga_execucao_pkey | p | {id} |

Existe PK `id`. A semantica de `id` como identificador de execucao foi confirmada pelo DDL; ver "Pendencias"
(resolvido).

## 8) Historico dos oito scripts (INCONCLUSIVO por desenho)

| script | quantidade_execucoes | horarios_distintos | possui_duas_execucoes | historico_status |
|---|---|---|---|---|
| agenda | 2 | 2 | true | INCONCLUSIVO_DESEMPATE_E_SEMANTICA_NAO_CONFIRMADOS |
| atendimento | 2 | 2 | true | INCONCLUSIVO_DESEMPATE_E_SEMANTICA_NAO_CONFIRMADOS |
| avaliacao | 2 | 2 | true | INCONCLUSIVO_DESEMPATE_E_SEMANTICA_NAO_CONFIRMADOS |
| cadastro | 2 | 2 | true | INCONCLUSIVO_DESEMPATE_E_SEMANTICA_NAO_CONFIRMADOS |
| comercial | 2 | 2 | true | INCONCLUSIVO_DESEMPATE_E_SEMANTICA_NAO_CONFIRMADOS |
| documentos | 2 | 2 | true | INCONCLUSIVO_DESEMPATE_E_SEMANTICA_NAO_CONFIRMADOS |
| referencia | 2 | 2 | true | INCONCLUSIVO_DESEMPATE_E_SEMANTICA_NAO_CONFIRMADOS |
| relatorio | 2 | 2 | true | INCONCLUSIVO_DESEMPATE_E_SEMANTICA_NAO_CONFIRMADOS |

Todos os scripts tem 2 execucoes em horarios distintos (sem empate em `executado_em`).
Condicao: a comparacao valida exige chave de execucao confirmada na etapa 7 e revisao operacional da sua semantica.

## 9) Permissoes e RLS

| schema | objeto | relkind | rls_habilitado | rls_forcado | possui_select |
|---|---|---|---|---|---|
| novo | arquivo | r | true | false | true |
| novo | carga_execucao | r | true | false | true |
| novo | carga_gabarito | r | true | false | true |
| novo | carga_rejeitado | r | true | false | true |
| novo | credito_lancamento | r | true | false | true |
| novo | renovacao | r | true | false | true |
| novo | vw_saldo_credito | v | false | false | true |
| origem | nutritionist_files | r | true | false | true |
| origem | physical_test_comparisons | r | true | false | true |
| origem | physio_assessments | r | true | false | true |
| origem | physio_evolutions | r | true | false | true |
| origem | specialist_evolutions | r | true | false | true |
| origem | student_files | r | true | false | true |
| origem | student_tests | r | true | false | true |
| origem | training_reports | r | true | false | true |

Policies em `novo`/`origem` (`pg_policies`): **0 linhas**.

Observacao: com RLS habilitado e nenhuma policy, um papel sem BYPASSRLS e que nao seja dono da tabela
veria 0 linhas. Mesmo assim, as etapas 6, 8 e 10 retornaram linhas para `supabase_read_only_user`. O script
nao verifica esse atributo; a consulta complementar 9b confirmou `rolbypassrls = true`, e isso explica a
visibilidade.

### 9b) Atributo do papel (consulta complementar, 2026-10-21)

Consulta: `select rolname, rolbypassrls, rolsuper from pg_roles where rolname = current_user;`

| rolname | rolbypassrls | rolsuper |
|---|---|---|
| supabase_read_only_user | true | false |

A visibilidade fica explicada: o papel tem BYPASSRLS e nao e superusuario. As contagens desta sessao
mostram a tabela inteira e nao o que os papeis da aplicacao enxergam. RLS sem policies continua
bloqueando anon/authenticated (ponto de seguranca/produto, fora do escopo deste preflight).

## 10) JSONB

| total_registros | pkz_data_nulo | objetos_json | valores_nao_objeto |
|---|---|---|---|
| 4 | 0 | 4 | 0 |

Nenhum valor nao-objeto; a conferencia de arquivos derivada nao fica bloqueada por este item.

## Pendencias

1. **Rotulo do ensaio (etapa 6): resolvido.** `dados/migracoes/README.md` (branch `dados`) registra o ensaio
   geral refeito em 16/10, com o gabarito `congelamento-2026-10-12` registrado de novo e igual ao antigo nas 28
   tabelas. A Frente 2 no ClickUp define esse mesmo rotulo como gabarito (informado pelo responsavel).
2. **Semantica de `carga_execucao.id` (etapas 7/8): resolvido.** `dados/migracoes/migrations/001_infra_carga.sql`
   (branch `dados`) define `id bigint generated always as identity primary key`, uma linha por execucao. A
   comparacao das duas ultimas execucoes por `executado_em DESC, id DESC` e valida.
3. **Visibilidade sob RLS sem policies (etapa 9): resolvido** na 9b (`rolbypassrls = true`).
4. **`carga_rejeitado.id_origem` uuid (etapa 4): sem impacto.** E `uuid` pelo DDL (`001_infra_carga.sql`), e o
   `06_destino_carga.sql` so usa `id_origem IS NULL` e `COUNT(DISTINCT id_origem)`, que funcionam com uuid.

A aprovacao do relatorio da Frente 2 fica para a Task 2.6.
