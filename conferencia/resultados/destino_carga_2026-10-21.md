# Conferencias no destino — Task 2.3 — 2026-10-21

- Script: `conferencia/sql/06_destino_carga.sql` (branch `feat/conferencias-origem`). A primeira execucao usou o
  commit `d429749`; a reexecucao dos blocos 1 e 7b usou a versao corrigida, commitada junto com este relatorio.
- Destino: projeto Supabase `jhspjkelmnbvrnleawwf` (mesmo projeto do preflight de 2026-10-21)
- Sessao: `supabase_read_only_user`, `rolbypassrls = true`, `rolsuper = false`. As contagens mostram as
  tabelas inteiras, sem filtro de RLS.
- Execucao: MCP `supabase` / `execute_sql`, somente SELECT, bloco por bloco.
- Conteudo: apenas contagens e status; sem uuids, caminhos, nomes de usuario ou dados pessoais.

## Historico de execucao e correcoes do script

1. **Primeira execucao (commit `d429749`).** O bloco 1 falhou com `42601 syntax error at or near ","`: nas
   linhas 29–30 (`physio_evolutions`, `specialist_evolutions`), o `)` da subconsulta escalar estava depois de
   `'VALIDA'`. Rodei uma copia com o parentese corrigido, sem a coluna `observacao`. O resumo final do bloco 7
   (7b) somava todos os lancamentos sem reiniciar na renovacao e deu 196 DIVERGENCIA.
2. **Correcao autorizada em 2026-10-21**, commitada junto com este relatorio, em `conferencia/sql/06_destino_carga.sql`:
   - linhas 29–30: so o parentese foi movido, `(... WHERE EXISTS (...)),'VALIDA')`; a logica nao mudou;
   - bloco 7b: o resumo passou a usar a mesma reconstrucao da consulta detalhada do bloco 7 (renovacao mais
     recente por `criado_em DESC, id DESC`; soma do delta da renovacao uma vez mais os lancamentos com
     `(criado_em,id)` posterior). Nenhuma regra nova.
3. **Reexecucao com o arquivo corrigido.** Os blocos 1 e 7b foram rodados com o texto exato do arquivo
   (incluindo `observacao`). Resultados abaixo.
4. **Blocos 5 e 7 rodaram em forma agregada para nao expor uuids.** Na forma original eles devolvem uma linha por
   registro, com username, storage_path e uuids de aluno/servico/renovacao/lancamento. Rodei os mesmos predicados
   dentro de agregacoes que so retornam contagens por chave/categoria. Isso vale para as duplicidades do bloco 5,
   as listagens de renovacoes/lancamentos e a comparacao detalhada do bloco 7. As consultas de FK do bloco 6
   foram unidas num unico SELECT (UNION ALL), com os predicados inalterados. Na revisao de 25/10 (Frente 1)
   essas formas agregadas passaram para o proprio arquivo, e foram reexecutadas com o mesmo resultado
   (12/12 chaves sem duplicidade; 201 pares OK).

## Resumo

| Bloco | Conferencia | Resultado |
|---|---|---|
| 1 | Gabarito x destino (19 mapeamentos) | 15 OK, 4 INCONCLUSIVO (por desenho), 0 DIVERGENCIA |
| 1b | Arquivos (origem derivada) | OK (523 = 523 + 0) |
| 2 | Rejeicoes | `novo.carga_rejeitado` vazia (0 linhas) |
| 3 | Pendencias | 28 tabelas; contagens abaixo (informativo) |
| 4 | Duas ultimas execucoes | 8/8 IGUAL |
| 5 | Duplicidades (12 chaves) | 12 OK |
| 6 | FKs (41 relacoes) | 0 orfaos; 0 nulos obrigatorios |
| 7 | Creditos: reconstrucao com reinicio na renovacao x view | 201 OK, 0 DIVERGENCIA, 0 SOMENTE_NA_* |
| 7b | Creditos: resumo final (arquivo corrigido, mesma reconstrucao) | 201 OK, 0 DIVERGENCIA, 0 SOMENTE_NA_* |

## 1) Gabarito x destino (reexecutado com o arquivo corrigido)

Rotulo usado pelo script: `congelamento-2026-10-12` (o mesmo identificado no preflight, etapa 6).

| # | script | tabela_origem | destino | modo | gabarito | destino | rejeicoes | destinos_da_origem | status |
|---|---|---|---|---|---|---|---|---|---|
| 1 | cadastro | profiles | novo.perfil_usuario | VALIDA | 152 | 152 | 0 | 1 | OK |
| 2 | cadastro | athletes | novo.aluno | PARCIAL | 106 | 106 | 0 | 2 | INCONCLUSIVO |
| 3 | comercial | athletes | novo.matricula | PARCIAL | 106 | 106 | 0 | 2 | INCONCLUSIVO |
| 4 | comercial | credit_transactions | novo.credito_lancamento | VALIDA | 1155 | 1155 | 0 | 1 | OK |
| 5 | agenda | schedule_blocks | novo.bloqueio_agenda | VALIDA | 36 | 36 | 0 | 1 | OK |
| 6 | agenda | bookings | novo.agendamento | VALIDA | 536 | 536 | 0 | 1 | OK |
| 7 | agenda | waitlist | novo.lista_espera | VALIDA | 0 | 0 | 0 | 1 | OK |
| 8 | agenda | training_feedback | novo.feedback_treino | VALIDA | 169 | 169 | 0 | 1 | OK |
| 9 | relatorio | training_report_materials | novo.catalogo_item (material) | VALIDA | 30 | 30 | 0 | 1 | OK |
| 10 | relatorio | training_report_technologies | novo.catalogo_item (tecnologia) | VALIDA | 10 | 10 | 0 | 1 | OK |
| 11 | relatorio | training_reports | novo.relatorio_treino | VALIDA | 228 | 228 | 0 | 1 | OK |
| 12 | avaliacao | physical_test_sessions | novo.avaliacao (teste_fisico) | VALIDA | 59 | 59 | 0 | 1 | OK |
| 13 | avaliacao | weekly_evaluations | novo.avaliacao (semanal) | VALIDA | 1 | 1 | 0 | 1 | OK |
| 14 | atendimento | physio_assessments | novo.avaliacao (fisioterapia) | PARCIAL | 4 | 4 | 0 | 2 | INCONCLUSIVO |
| 15 | atendimento | physio_assessments | novo.anamnese | PARCIAL | 4 | 4 | 0 | 2 | INCONCLUSIVO |
| 16 | atendimento | physio_evolutions | novo.atendimento (fisio) | VALIDA | 7 | 7 | 0 | 1 | OK |
| 17 | atendimento | specialist_evolutions | novo.atendimento (especialista) | VALIDA | 15 | 15 | 0 | 1 | OK |
| 18 | documentos | activity_logs | novo.evento_auditoria (activity_logs) | VALIDA | 1163 | 1163 | 0 | 1 | OK |
| 19 | documentos | booking_audit_logs | novo.evento_auditoria (booking_audit_logs) | VALIDA | 226 | 226 | 0 | 1 | OK |

Os 4 INCONCLUSIVO vem de origens com 2 destinos (`athletes`, `physio_assessments`), com a observacao do
script: "Uma origem alimenta mais de um destino; a rejeicao nao e atribuida individualmente sem regra de
rateio." Mesmo sem rateio, nos 4 casos o destino bate com o gabarito (106/106 e 4/4) e nao ha rejeicoes.
Nas linhas OK, `observacao` e nula. Os resultados sao identicos aos da copia corrigida da primeira execucao.

### 1b) Arquivos (ORIGEM_DERIVADA)

| caminhos_distintos_origem | arquivos_destino | rejeicoes_registradas | status |
|---|---|---|---|
| 523 | 523 | 0 | OK |

## 2) Rejeicoes

`novo.carga_rejeitado` esta vazia: as duas consultas (por motivo e resumo) retornaram 0 linhas. Isso bate com
`linhas_rejeitadas = 0` nas 16 execucoes do bloco 4.

## 3) Pendencias por tabela (informativo)

| tabela | total | com_pendencia |
|---|---|---|
| agendamento | 536 | 26 |
| aluno | 106 | 106 |
| anamnese | 4 | 0 |
| arquivo | 523 | 6 |
| atendimento | 22 | 7 |
| avaliacao | 64 | 0 |
| avaliacao_medida | 2908 | 147 |
| bloqueio_agenda | 36 | 0 |
| catalogo_item | 72 | 5 |
| configuracao_unidade | 2 | 2 |
| credito_lancamento | 1155 | 182 |
| evento_auditoria | 1389 | 40 |
| evolucao | 22 | 0 |
| feedback_treino | 169 | 0 |
| horario_grade | 37 | 37 |
| lista_espera | 0 | 0 |
| matricula | 106 | 106 |
| metrica | 109 | 65 |
| papel_usuario | 153 | 3 |
| perfil_usuario | 152 | 0 |
| pessoa | 258 | 0 |
| plano | 7 | 3 |
| plano_beneficio | 13 | 3 |
| profissional | 31 | 5 |
| relatorio_treino | 228 | 21 |
| renovacao | 968 | 33 |
| responsavel_aluno | 106 | 0 |
| sessao_treino | 224 | 0 |

O script nao define limite para pendencias, entao nao ha status. Os casos com 100% de pendencia estao
explicados (ver "Pendencias", item 4).

## 4) Duas ultimas execucoes por script

| script | execucoes | ultima (UTC) | penultima (UTC) | carregadas ult/pen | rejeitadas ult/pen | status |
|---|---|---|---|---|---|---|
| agenda | 2 | 2026-10-16 12:58:09 | 2026-10-16 12:50:44 | 1036 / 1036 | 0 / 0 | IGUAL |
| atendimento | 2 | 2026-10-16 13:01:17 | 2026-10-16 12:54:20 | 241 / 241 | 0 / 0 | IGUAL |
| avaliacao | 2 | 2026-10-16 13:01:17 | 2026-10-16 12:54:20 | 2888 / 2888 | 0 / 0 | IGUAL |
| cadastro | 2 | 2026-10-16 12:58:09 | 2026-10-16 12:48:58 | 1092 / 1092 | 0 / 0 | IGUAL |
| comercial | 2 | 2026-10-16 12:58:09 | 2026-10-16 12:50:44 | 2229 / 2229 | 0 / 0 | IGUAL |
| documentos | 2 | 2026-10-16 13:01:17 | 2026-10-16 12:54:20 | 1912 / 1912 | 0 / 0 | IGUAL |
| referencia | 2 | 2026-10-16 12:58:09 | 2026-10-16 12:48:58 | 33 / 33 | 0 / 0 | IGUAL |
| relatorio | 2 | 2026-10-16 12:58:09 | 2026-10-16 12:50:44 | 1212 / 1212 | 0 / 0 | IGUAL |

Tabela da primeira execucao; o bloco 4 nao foi alterado na correcao e nao foi reexecutado. O desempate usa
`executado_em DESC, id DESC`, e `id` e identity, uma linha por execucao (ver "Pendencias", item 3). Como todos os
scripts tem horarios distintos, o desempate por `id` nao chegou a ser usado.

## 5) Duplicidades (agregado)

| chave | grupos_duplicados | linhas_nos_grupos | status |
|---|---|---|---|
| perfil_usuario.username | 0 | 0 | OK |
| pessoa.origem | 0 | 0 | OK |
| papel_usuario | 0 | 0 | OK |
| plano.codigo | 0 | 0 | OK |
| servico.codigo | 0 | 0 | OK |
| unidade.codigo | 0 | 0 | OK |
| renovacao_chave_constraint | 0 | 0 | OK |
| renovacao_regra_negocio_restritiva | 0 | 0 | OK |
| arquivo.storage_path | 0 | 0 | OK |
| feedback_treino.agendamento_id | 0 | 0 | OK |
| sessao_treino.agendamento_id | 0 | 0 | OK |
| agendamento.ativo | 0 | 0 | OK |

## 6) FKs

Nenhuma das 41 relacoes tem orfaos. Nenhuma relacao com nulo obrigatorio tem nulos.

Relacoes com nulo permitido e nulos > 0 (informativo):

| relacao | nulos |
|---|---|
| papel_usuario.unidade_id | 135 |
| credito_lancamento.renovacao_id | 154 |
| credito_lancamento.ator_id | 1001 |
| agendamento.profissional_id | 298 |
| atendimento.agendamento_id | 7 |
| arquivo.relatorio_id | 318 |
| arquivo.avaliacao_id | 511 |
| arquivo.atendimento_id | 501 |
| evento_auditoria.ator_id | 23 |
| evento_auditoria.unidade_id | 99 |

As demais 31 relacoes tem 0 nulos e 0 orfaos.

## 7) Creditos

### Lancamentos e vinculo com renovacao (agregado)

| verificacao | categoria | quantidade |
|---|---|---|
| lancamentos por origem_tipo | agendamento | 33 |
| lancamentos por origem_tipo | ajuste_manual | 30 |
| lancamentos por origem_tipo | estorno | 91 |
| lancamentos por origem_tipo | renovacao | 1001 |
| renovacoes sem lancamento | — | 0 |
| lancamentos `renovacao` sem `renovacao_id` | — | 0 |

Observacao: ha 1001 lancamentos `renovacao` para 968 renovacoes; algumas renovacoes tem mais de um lancamento.
Os 154 lancamentos com `renovacao_id` nulo sao exatamente os nao-renovacao (33 + 30 + 91).

### Reconstrucao com reinicio na ultima renovacao x `vw_saldo_credito` (agregado por interpretacao)

| interpretacao | empate_no_timestamp | tem_renovacao | pares aluno/servico | soma dif. abs. | maior dif. abs. |
|---|---|---|---|---|---|
| OK | false | false | 3 | 0 | 0 |
| OK | false | true | 198 | 0 | 0 |

Total: 201 pares OK, 0 DIVERGENCIA, 0 SOMENTE_NA_VIEW, 0 SOMENTE_NA_RECONSTRUCAO, 0 empates no timestamp.

### 7b) Resumo final (reexecutado com o arquivo corrigido)

| status | quantidade |
|---|---|
| OK | 201 |

0 DIVERGENCIA, 0 SOMENTE_NA_VIEW, 0 SOMENTE_NA_RECONSTRUCAO. Bate com o agregado da consulta detalhada (201 OK).

Primeira execucao, antes da correcao (registro historico): 5 OK e 196 DIVERGENCIA. Categoria: regra de calculo
da consulta. O resumo somava `SUM(delta)` de todos os lancamentos, sem reiniciar na renovacao, o que contradizia
o comentario do bloco 7 e a migration `pkzbi_eg_011_saldo_nao_cumulativo`. Nao era divergencia de dados.

## Pendencias

1. ~~Corrigir o parentese nas linhas 29–30.~~ Feito.
2. ~~Alinhar o resumo final do bloco 7 com a regra de saldo nao cumulativo.~~ Feito.
3. **Rotulo e `carga_execucao.id`: resolvidos** (evidencias no preflight, Pendencias 1 e 2):
   `congelamento-2026-10-12` registrado de novo no ensaio geral de 16/10, igual nas 28 tabelas
   (`dados/migracoes/README.md`, branch `dados`; Frente 2 no ClickUp); `id` e
   `bigint generated always as identity primary key` (`001_infra_carga.sql`).
4. **Tabelas com 100% de pendencia: explicado.**
   - `aluno` (106/106) e `matricula` (106/106): recebem "data aproximada" de proposito.
     `carga/20_carga_cadastro.sql` grava "data de entrada aproximada (= criacao do cadastro)" e
     `carga/30_carga_comercial.sql` grava "inicio aproximado (= criacao do cadastro)" (branch `dados`).
   - `horario_grade` (37/37) e `configuracao_unidade` (2/2): registradas em `dados/migracoes/PENDENCIAS.md`
     (branch `dados`).
5. **`carga_rejeitado.id_origem` uuid: sem impacto.** E uuid pelo DDL, e o `06` so usa `IS NULL` e
   `COUNT(DISTINCT)`.

A aprovacao do relatorio da Frente 2 fica para a Task 2.6.
