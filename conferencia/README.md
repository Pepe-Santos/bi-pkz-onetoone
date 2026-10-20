# Conferências da origem

Consultas da tarefa 2.1 para calcular valores esperados exclusivamente no schema `origem`.

## Escopo

- Todas as consultas são somente leitura (`SELECT`, `WITH` e `VALUES`).
- Nenhuma consulta lê `novo` ou `novo_pre_ensaio_geral` para calcular o gabarito.
- Nenhum resultado de produção é versionado neste repositório.
- A validação executada em 20/10/2026 confirmou o schema `origem` do projeto Supabase configurado no MCP e suas 28 tabelas de origem.

## Consultas

| Arquivo | Conferência |
|---|---|
| `sql/01_contagem_linhas.sql` | Contagem das 28 tabelas de `origem` |
| `sql/02_testes_fisicos_json.sql` | Valores preenchidos em `origem.physical_test_sessions.data` |
| `sql/03_fisioterapia_medidas.sql` | Valores não nulos nas 14 medidas numéricas de fisioterapia |
| `sql/04_arquivos_origem.sql` | Nove colunas de caminho e referências de arquivo |
| `sql/05_creditos_origem.sql` | Saldos materializados, extrato e saldo reconstruível por renovação |

## Estado real do projeto

O banco possui tabelas de controle em `novo` e `novo_pre_ensaio_geral`, incluindo `carga_execucao`, `carga_gabarito`, `carga_rejeitado` e `v_resumo_carga`. Elas foram consultadas apenas para entender o histórico da carga; não são usadas pelas consultas desta pasta para calcular os valores esperados.

O comentário de `novo.arquivo` confirma as nove referências: `student_files.storage_path`, `nutritionist_files.storage_path`, `physio_evolutions.storage_path`, `specialist_evolutions.file_path`, `training_reports.file_path`, `training_reports.pdf_storage_path`, `physical_test_comparisons.file_path`, `physio_assessments.file_path` e `student_tests.file_path`. A consulta 04 calcula preenchimento e caminhos distintos exclusivamente na origem.

### Créditos

A regra confirmada para os três serviços é não acumular créditos: cada renovação reinicia o saldo do serviço correspondente em 10 créditos. O saldo esperado é 10 mais a soma dos lançamentos posteriores à última renovação identificada; a própria renovação não é somada novamente. A view `novo.vw_saldo_credito` expressa uma regra de soma desde a renovação, mas a consulta desta pasta calcula o gabarito exclusivamente em `origem`.

Os motivos genericos de renovacao, como `Renovacao mensal (08/2026)` e `Renovacao mensal (10/2026)`, permanecem sem classificacao porque a origem nao identifica se pertencem a treino, fisioterapia ou nutricao. A consulta mantem separados o saldo materializado, a soma historica de `delta`, o saldo reconstruido e a diferenca entre eles. Motivos especificos sao classificados somente quando o texto fornece evidencia suficiente.

## Resultados validados

- `origem.physical_test_sessions`: 59 sessões; 59 JSONs com conteúdo; nenhum `NULL`, objeto vazio ou array vazio.
- `origem.physio_assessments`: 4 avaliações; 12 das 14 medidas possuem valor não nulo; `quadril_dir` e `quadril_esq` estão totalmente nulos.
- `origem.credit_transactions`: 1.155 lançamentos; as renovações genéricas somam 3 lançamentos em agosto e 105 em outubro, sem serviço identificável.
- Com a classificação textual atual e reinício em 10, foram reconstruídos 104 saldos de treino, 21 de fisioterapia e 71 de nutrição; a comparação produziu divergências em 195 de 196 saldos classificados. Isso indica que a classificação textual não deve ser tratada como prova de equivalência dos campos materializados.

## Pendências

- Confirmar com o grupo se objetos e arrays JSON vazios devem ser considerados preenchidos; a consulta os separa explicitamente e não os confunde com `NULL`.
- A regra de não acumulação para treino, fisioterapia e nutrição foi confirmada no contexto da tarefa.
- Confirmar o parser oficial de serviço para motivos ambíguos ou inconsistentes, especialmente renovações mensais genéricas e lançamentos com marcador divergente.
- A conexão remota não permitiu confirmar `origin/main` nesta sessão (`git ls-remote` falhou por conexão ao GitHub); o branch local ainda aponta para o commit `244ac9f` registrado como `origin/main` no clone.
- Os resultados de validação não são armazenados neste repositório para evitar dados de produção.
