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
| `sql/05_creditos_origem.sql` | Saldos materializados, extrato e saldo reconstruído por renovação |

## Créditos

A regra confirmada é não cumulativa: uma renovação reinicia o saldo do serviço para o `delta` registrado naquele lançamento. Não há regra geral de reinício em 10 créditos. O saldo reconstruído usa a renovação identificável mais recente de cada atleta e serviço, inclui seu `delta` exatamente uma vez e soma os lançamentos posteriores do mesmo serviço. `created_at` ordena os eventos; `id` desempata timestamps iguais.

A classificação é conservadora. Renovação mensal genérica, como `Renovação mensal (08/2026)` e `Renovação mensal (10/2026)`, não é atribuída a treino, fisioterapia ou nutrição sem evidência. Lançamentos operacionais que citam fisioterapia ou nutrição não são classificados como treino apenas porque também contêm `[treino]`. Casos sem renovação identificável ou sem serviço seguro permanecem inconclusivos.

## Resultados validados em 20/10/2026

- A origem contém 106 atletas e 1.155 lançamentos em `origem.credit_transactions`.
- Foram comparados 104 saldos de treino, 21 de fisioterapia e 71 de nutrição: 196 comparações no total.
- Todas as 196 comparações coincidiram com os saldos materializados: 104/104, 21/21 e 71/71; divergências: 0; diferença absoluta total: 0.
- As 196 comparações exigiram renovação e serviço identificáveis; fora delas, existem 4 combinações atleta/serviço observadas sem renovação identificável (3 de fisioterapia e 1 de nutrição), apresentadas pela consulta como inconclusivas.
- A consulta também lista as renovações sem serviço, os motivos do extrato, a cobertura de renovação e as contagens para evidenciar cobertura. Cada lançamento posterior entra no `SUM` uma vez, e o lançamento de renovação aparece apenas como `delta_renovacao`.

## Limitações e pendências

- As 108 renovações mensais genéricas (3 em agosto e 105 em outubro) permanecem sem serviço identificável; seus `delta` não são inventados nem aplicados a um saldo. Além disso, 110 transações não receberam classificação segura pelo parser textual, incluindo 2 solicitações de psicologia marcadas indevidamente com `[treino]`; essas transações não entram nas comparações.
- Há 2 saldos positivos de treino sem renovação identificável; eles permanecem fora das comparações e exigem evidência adicional para reconstrução segura.
- Classificações textuais continuam limitadas quando o motivo mistura marcadores, embora os motivos operacionais de fisioterapia e nutrição sejam excluídos da regra de treino.
- A consulta não altera dados materializados e não declara homologação completa enquanto houver casos genéricos ou saldos sem renovação identificável.
- Os resultados de validação não são armazenados neste repositório para evitar dados de produção.