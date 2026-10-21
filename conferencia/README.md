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

## Task 2.3 — Destino

### Preflight operacional

O arquivo `sql/00_preflight_destino.sql` prepara a execução controlada da Task 2.3 em dez etapas numeradas: (1) identidade da sessão e confirmação independente do projeto Supabase; (2) schemas e privilégios básicos; (3) objetos essenciais; (4) colunas e tipos; (5) view de saldo; (6) snapshot do gabarito; (7) schema real e constraints de `carga_execucao`; (8) histórico dos oito scripts; (9) permissões e RLS; e (10) validação condicional do JSONB.

As etapas são exclusivamente de leitura e devem ser executadas manualmente, na ordem, sem executar a etapa seguinte quando a anterior apresentar ausência, incompatibilidade, permissão insuficiente ou resultado inconclusivo. A confirmação do ambiente exige um canal operacional independente, pois `current_database()` não identifica sozinho o projeto Supabase. As verificações de `SELECT` e RLS não comprovam visibilidade integral dos dados.

A etapa 10 só pode ser executada após confirmar o ambiente, a tabela `origem.physio_assessments`, a permissão de leitura e o tipo `jsonb` de `pkz_data`. O arquivo `sql/06_destino_carga.sql` não deve ser executado antes da revisão dos resultados do preflight e de autorização explícita. A Task 2.3 permanece não homologada; histórico sem chave de execução semanticamente validada, empate de rótulos do gabarito, snapshot ausente e demais estados inconclusivos bloqueiam a continuidade.

`sql/06_destino_carga.sql` reúne consultas exclusivamente de leitura para o schema `novo`. O preflight identifica o rótulo de congelamento mais recente em `novo.carga_gabarito`, mas bloqueia empates e exige confirmação operacional de que o rótulo corresponde ao ensaio. A consulta distingue `GABARITO_INEXISTENTE`, `SEM_TABELA_NO_GABARITO`, `DIVERGENCIA` e estados `INCONCLUSIVO` sem misturar snapshots.

### Conferências implementadas

- matriz dos mapeamentos reproduzíveis do ensaio geral, incluindo materiais, tecnologias, avaliações, anamneses e os dois domínios de atendimento;
- caminhos de arquivos distintos das fontes documentadas, incluindo `img_*`, `carimbo_path` e `laudo_path` extraídos de `physio_assessments.pkz_data`;
- rejeições por script, tabela e motivo, com ocorrências totais, `id_origem` nulo, IDs distintos e ocorrências `motivo LIKE 'chave %'` excluídas da reconciliação de linhas; quando uma origem alimenta vários destinos, a comparação fica `INCONCLUSIVO` e não reutiliza a mesma rejeição;
- pendências por tabela, histórico de execuções, incluindo `referencia`, quantidade de rodadas, datas da última e penúltima e comparação explícita das duas últimas, inclusive `INCONCLUSIVO` quando faltar penúltima;
- duplicações nas chaves de origem, matrículas, medidas, a constraint final de `renovacao(aluno_id, servico_id, periodicidade, competencia)` e a regra adicional mais restritiva sem `periodicidade`;
- FKs do DDL cobertas nas áreas de cadastro, comercial, agenda, atendimento, arquivos e auditoria, separando nulos permitidos, nulos obrigatórios e órfãos;
- saldos com renovação mais recente identificada por `criado_em` e `id`, usando o `delta` da renovação uma vez e somando os lançamentos posteriores.

### Resultados e interpretação

Os resultados históricos registrados anteriormente continuam sendo apenas evidência observada: duas execuções por script, zero rejeições registradas, 106 alunos, 152 perfis, 258 pessoas e as comparações parciais documentadas. As novas consultas ainda precisam ser executadas no destino para confirmar a cobertura completa.

A regra de rejeição `motivo LIKE 'chave %'` é deliberada: esses registros são reportados, mas não reduzem a contagem de linhas da reconciliação porque representam conferências de chave sem métrica, conforme a conferência geral da Frente 1. A ausência de rejeições não prova ausência de perdas ou duplicações; as consultas de chaves devem ser analisadas em conjunto.

Renovações sem lançamento e lançamentos de renovação sem `renovacao_id` são retornados em detalhe para investigação e exigem interpretação de negócio. Não são classificados automaticamente como defeitos. Na reconstrução, a renovação entra pelo próprio `delta` uma vez; movimentações posteriores são somadas uma vez. Todos os lançamentos com o mesmo timestamp da renovação selecionada são identificados, inclusive empates anteriores por `id`; divergências com empate são marcadas como potencialmente explicadas pelo empate e não como defeito automático. A consulta retorna `OK`, `DIVERGENCIA`, `SOMENTE_NA_RECONSTRUCAO` e `SOMENTE_NA_VIEW`.

### Limitações

- Os scripts de carga não foram executados nesta tarefa; o histórico de duas rodadas não é um novo ensaio controlado.
- A matriz cobre somente mapeamentos que podem ser reproduzidos com segurança a partir dos objetos e mapeamentos disponíveis. Mapeamentos sem destino contável seguro continuam pendentes e não são declarados como cobertura completa.
- A lista de FKs consultadas cobre cadastro, comercial, agenda, atendimento, arquivos e auditoria nas relações explicitadas no SQL. Permanecem pendentes as FKs não listadas do DDL, especialmente `bloqueio_grade`, `horario_grade`, `sessao_treino`, `lista_espera`, `avaliacao_medida`, `evolucao`, `consentimento`, `relatorio_emissao`, `relatorio_envio`, `notificacao` e `acesso_dado_sensivel`; elas não são consideradas homologadas pela consulta.
- A reconstrução expõe a renovação selecionada, `criado_em`, `delta`, quantidade de lançamentos considerados e todos os lançamentos com o mesmo timestamp, inclusive empates anteriores por `id`. A view `novo.vw_saldo_credito` usa o maior `criado_em` e não desempata por `id`, enquanto a reconstrução usa `criado_em` e `id`; divergências com empate são marcadas como potencialmente explicadas pelo empate e não como defeito automático.
- Pendências de negócio, renovações genéricas e classificações ambíguas de `dados/migracoes/PENDENCIAS.md` continuam exigindo decisão ou validação adicional.
- A Task 2.3 não está homologada: a execução das consultas e a análise dos resultados reais permanecem pendentes.
