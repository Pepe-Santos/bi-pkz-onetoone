# Relatório final — Frente 2

**Projeto de Business Intelligence — PKZ / OneToOne**
**Frente 2: validação, qualidade e homologação da migração**

| | |
|---|---|
| Repositório | `bi-pkz-onetoone` |
| Atualização | 21 de outubro de 2026 |
| Finalidade | consolidar os resultados reais das tasks 2.1 a 2.5, as evidências e o que falta para a aprovação da Frente 2 (Task 2.6) |
| Substitui | relatório de progresso de 21/10/2026 (versão anterior à execução no destino) |

## Resumo executivo

As conferências do destino (Task 2.3) foram **executadas no banco** em 21/10/2026, em sessão somente leitura, no Supabase da cópia (`jhspjkelmnbvrnleawwf`), contra o gabarito `congelamento-2026-10-12`. O preflight passou nas 10 etapas e as conferências de carga não encontraram divergência nos dados: contagens, rejeições, reexecução, duplicidades, integridade referencial e saldos de créditos bateram ou têm explicação documentada.

Os dois inconclusivos que o relatório anterior deixava em aberto foram tratados: a diferença de cardinalidade do caso COM-MUITOS é de classificação, não de volume (o total de lançamentos bate 1155/1155), e o atendimento tem explicação no código e nas contagens. A execução encontrou e corrigiu dois defeitos no próprio script de conferência, nenhum nos dados nem na carga.

**Não há divergência sem explicação nos 6 domínios.** Permanecem 14 pendências de negócio, todas registradas em `PENDENCIAS.md` e marcadas nos dados. A Frente 2 fecha com a aprovação deste relatório (seção 9).

A aprovação de PR e a aprovação dos dados continuam sendo etapas distintas: o merge dos PRs #7 e #8 integra o código; a aprovação deste relatório aprova o resultado da conferência do **ensaio geral**. A homologação do modelo (marco M2) e a execução definitiva do ENT-002 estão fora do escopo da Frente 2.

## 1. Estado geral por tarefa

| Tarefa | Estado | Resumo |
|---|---|---|
| 2.1 — Conferências da origem | Concluída (*shipped*) | Cinco scripts de valores esperados na origem. Créditos: 196 comparações identificáveis sem divergência (104 treino, 21 fisioterapia, 71 nutrição). |
| 2.2 — Revisão de DDL e mapeamentos | Concluída (*shipped*), integrada no PR #5 | Cobertura reproduzível: 365/365 colunas da origem e 451/451 do destino, 0 erros. Papéis × unidade: 135 globais e 18 por unidade, 0 violações. Ponte entre as duas conferências de saldo. |
| 2.3 — Conferências no destino | **Concluída (*shipped*) em 21/10** | Preflight 10/10 sem bloqueio; conferências de carga sem divergência nos dados; 2 defeitos do script corrigidos. Resultados no PR #8. |
| 2.4 — Amostras por domínio | Concluída (*shipped*) | 21 casos em sete agrupamentos. Os dois pontos em aberto (COM-MUITOS e atendimento) estão explicados na seção 3.2. |
| 2.5 — Pendências de significado | Concluída (*shipped*); PR #7 aberto | Altura, `slalom_wallball` e `notifications` documentados como pendências de negócio; catálogo de métricas 109/109 igual ao mapeamento. |
| 2.6 — Relatório final | **Este documento; aguardando aprovação** | Números esperados × encontrados, rejeições, reexecução, amostras, pendências e limitações, por domínio. |

## 2. Git, branches e Pull Requests

Estado conferido no GitHub em 21/10/2026.

- **`main`:** `30d0d66` (merge do PR #5).
- **PR #5:** integrado. Banco reestruturado, modelo conceitual v2, artefatos da Task 1.7 e respostas à revisão (`1607088`).
- **PR #8:** aberto, `feat/conferencias-origem` → `main`, head `ac499d4`, 2 commits, 5 arquivos:
  - `d429749` — preflight, conferência do destino e README (Task 2.3);
  - `ac499d4` — correção do `06_destino_carga.sql` e resultados da execução (`conferencia/resultados/`).
  A branch não contém a `main` atual, mas nenhum arquivo foi alterado dos dois lados: sem conflito previsto.
- **PR #7:** aberto, `docs/task-2.5-pendencias-significado-main` (`ffe815a`), documento da Task 2.5.
- **Task 2.4:** commit `700bc71`, já na `main`.

Integração na `main` não é aprovação dos dados. Nenhuma operação destrutiva foi feita; nenhum merge foi feito sem revisão.

## 3. Evidências das Tasks 2.1 e 2.4

### 3.1 Task 2.1 — conferências da origem

- `01_contagem_linhas.sql` — contagem das 28 tabelas da origem.
- `02_testes_fisicos_json.sql` — valores preenchidos no JSON dos testes físicos.
- `03_fisioterapia_medidas.sql` — valores não nulos nas 14 medidas de fisioterapia.
- `04_arquivos_origem.sql` — caminhos e referências de arquivo.
- `05_creditos_origem.sql` — saldos, extrato e saldo reconstruído por renovação.

Resultado: 196 comparações de crédito sem divergência. A regra confirmada é **não cumulativa** (a renovação reinicia o saldo pelo seu `delta`), a mesma da migration 011 e da conferência do destino. Renovações genéricas e lançamentos sem classificação segura ficaram fora desse universo; a ponte da 2.2 (`03_saldo_credito.sql`) mostra que, no universo de 318 pares da carga, as únicas 3 diferenças são a pendência 13.

### 3.2 Task 2.4 — amostras por domínio

21 casos, três por agrupamento (muitos dados, poucos dados, limítrofe): cadastro; comercial e créditos; agenda; relatórios; avaliações; atendimento; documentos e auditoria. Artefatos: `PLANO_TASK_2_4.md`, `TASK_2_4_AMOSTRAS.md`, `sql/07_amostras_task_2_4.sql`.

| Agrupamento | Resultado |
|---|---|
| Cadastro | 3/3 OK (IDs, `pessoa_id`, status, datas; categoria vazia → nula conforme regra) |
| Comercial e créditos | 3/3 OK no saldo e nos lançamentos; diferença de cardinalidade do COM-MUITOS explicada (abaixo) |
| Agenda | 3/3 OK (17/17 agendamentos, 10/10 feedbacks, 10/10 sessões no caso maior) |
| Relatórios | 3/3 OK (17/17 itens materializados e catalogados) |
| Avaliações | 3/3 OK; campo a campo 230/230, 54/54 e 43/43 medidas, 0 divergências de valor |
| Atendimento | 9/9 IDs, alunos, profissionais e datas; serviço explicado (abaixo) |
| Documentos e auditoria | arquivos 3/3 OK (inclusive caminho compartilhado deduplicado); auditoria 3/3 OK |

**COM-MUITOS — explicado.** No recorte da amostra, a origem tinha 19 lançamentos e 13 renovações; o destino, 21 e 15. As duas renovações a mais são renovações genéricas que existem na origem, mas não traziam o serviço no texto; a carga as atribui ao treino por regra documentada (`mapeamento/README.md`: renovação genérica = treino). É diferença de **classificação**, não de volume: na Task 2.3, `credit_transactions` → `credito_lancamento` bate em 1155/1155, com 0 rejeições e 0 renovações sem lançamento, e o saldo do caso é 6 nos dois lados.

**Atendimento — explicado.** Os três casos ficaram INCONCLUSIVOS na 2.4 só pelo serviço de origem, apresentado como desconhecido, com `fisioterapia` no destino. A causa está na estrutura da origem: `physio_evolutions` **não tem coluna de serviço** (só id, atleta, fisioterapeuta, arquivo, caminho e data), e a carga atribui `fisioterapia` pela própria tabela (`70_carga_atendimento.sql`). Em `specialist_evolutions`, serviço nulo ou desconhecido é rejeitado, e a Task 2.3 encontrou 0 rejeições com 7/7 atendimentos de fisio e 15/15 de especialista. Ressalva: a explicação vem do código e das contagens; a amostra não foi reexecutada.

As amostras confirmam a regra nos casos escolhidos; a cobertura do total vem das contagens da Task 2.3.

## 4. Task 2.3 — execução no destino

### 4.1 Pré-requisitos operacionais

| Pré-requisito | Situação |
|---|---|
| Confirmar o projeto de destino por canal independente | Feito: dashboard do Supabase, ref `jhspjkelmnbvrnleawwf`, org "Projeto BI org", última migration `pkzbi_eg_011_saldo_nao_cumulativo` |
| Sessão de leitura e privilégios em `novo` e `origem` | Feito: `supabase_read_only_user`, USAGE nos dois schemas, sem CREATE |
| Avaliar RLS | Feito: RLS ligado e nenhuma policy; o papel tem BYPASSRLS (sem superusuário), logo as contagens cobrem as tabelas inteiras |
| Confirmar o gabarito em `novo.carga_gabarito` | Feito: `congelamento-2026-10-12`, 28 tabelas, sem nulos nem duplicidade; registrado de novo no ensaio geral de 16/10, igual ao anterior |
| Ausência de empate, tabelas e tipos esperados | Feito: 1 rótulo no timestamp máximo; 39/39 objetos; 12 colunas OK e 1 não validada por desenho (`id_origem` é uuid, sem impacto) |
| Preflight antes da conferência, parando no primeiro bloqueio | Feito: 10/10 etapas sem bloqueio |
| Conferência de carga só depois do preflight, com saídas guardadas | Feito: `conferencia/resultados/destino_carga_2026-10-21.md` |

### 4.2 Resultados

| Bloco | Conferência | Resultado |
|---|---|---|
| 1 | Gabarito × destino (19 mapeamentos) | 15 OK; 4 INCONCLUSIVOS por desenho (origem que alimenta dois destinos), com números iguais |
| 1b | Arquivos | 523 caminhos distintos na origem = 523 arquivos no destino |
| 2 | Rejeições | `novo.carga_rejeitado` vazia |
| 3 | Pendências por tabela | informativo (ver seção 7) |
| 4 | Reexecução | 8/8 scripts com linhas carregadas e rejeitadas iguais nas duas rodadas de 16/10 |
| 5 | Duplicidades | 12/12 chaves sem duplicidade |
| 6 | Integridade referencial | 41 FKs: 0 órfãos, 0 nulos onde é obrigatório |
| 7 / 7b | Saldo de créditos | 201/201 pares: reconstrução não cumulativa = `vw_saldo_credito` |

### 4.3 Defeitos encontrados e corrigidos

| Onde | Defeito | Correção |
|---|---|---|
| `06_destino_carga.sql`, linhas 29–30 | parêntese fora do lugar (erro 42601) | movido, sem mudar a lógica (`ac499d4`) |
| `06_destino_carga.sql`, bloco 7b | resumo cumulativo, gerando 196 falsas divergências | passou a usar a reconstrução não cumulativa do bloco 7: 201/201 OK (`ac499d4`) |

Nenhum defeito nos dados carregados nem nos scripts de carga.

## 5. Evidências exigidas — checklist

| Evidência | Onde |
|---|---|
| Identidade do ambiente e usuário efetivo, sem segredos | preflight, etapa 1 e 9b |
| Saída completa do preflight (objetos, tipos, view, permissões, RLS, JSONB) | `preflight_2026-10-21.md` |
| Rótulo do gabarito, data de registro e tabelas do snapshot | preflight, etapa 6 |
| Histórico em `carga_execucao` e rejeições em `carga_rejeitado` | destino, blocos 2 e 4 |
| Resultados por estado (OK, DIVERGENCIA, INCONCLUSIVO) | destino, blocos 1 e 7 |
| Duplicidade, integridade referencial e saldos | destino, blocos 5, 6 e 7 |
| Divergências, justificativas e decisões pendentes | seções 3.2, 4.3, 6 e 7 deste relatório |
| Aprovação final | seção 9 (pendente) |

Critérios de bloqueio do relatório anterior: **não há** inconclusivo sem tratamento, divergência sem explicação, gabarito ambíguo nem evidência faltante.

## 6. Resultado por domínio

Os 6 domínios do modelo conceitual v2. "Esperado" é o gabarito; "Encontrado" é o destino.

| Domínio | Origem → destino | Esperado | Encontrado | Rej. | Resultado |
|---|---|---|---|---|---|
| Cadastro | `profiles` → `perfil_usuario` | 152 | 152 | 0 | OK |
| | `athletes` → `aluno` | 106 | 106 | 0 | Explicado (mesma origem de `matricula`) |
| Comercial | `athletes` → `matricula` | 106 | 106 | 0 | Explicado (mesma origem de `aluno`) |
| | `credit_transactions` → `credito_lancamento` | 1155 | 1155 | 0 | OK |
| | saldo: reconstrução × view | 201 | 201 | — | OK |
| Agenda | `schedule_blocks` → `bloqueio_agenda` | 36 | 36 | 0 | OK |
| | `bookings` → `agendamento` | 536 | 536 | 0 | OK |
| | `waitlist` → `lista_espera` | 0 | 0 | 0 | OK (origem vazia) |
| | `training_feedback` → `feedback_treino` | 169 | 169 | 0 | OK |
| | `training_reports` → `relatorio_treino` | 228 | 228 | 0 | OK |
| | materiais e tecnologias → `catalogo_item` | 40 | 40 | 0 | OK |
| Avaliação | `physical_test_sessions` → `avaliacao` | 59 | 59 | 0 | OK |
| | `weekly_evaluations` → `avaliacao` | 1 | 1 | 0 | OK |
| Atendimento | `physio_assessments` → `avaliacao` e `anamnese` | 4 + 4 | 4 + 4 | 0 | Explicado (uma origem, dois destinos) |
| | `physio_evolutions` → `atendimento` | 7 | 7 | 0 | OK |
| | `specialist_evolutions` → `atendimento` | 15 | 15 | 0 | OK |
| Conformidade | caminhos de arquivo → `arquivo` | 523 | 523 | 0 | OK |
| | `activity_logs` → `evento_auditoria` | 1163 | 1163 | 0 | OK |
| | `booking_audit_logs` → `evento_auditoria` | 226 | 226 | 0 | OK |

Outras tabelas do destino (contagem informativa): `pessoa` 258, `papel_usuario` 153, `responsavel_aluno` 106, `profissional` 31, `renovacao` 968, `sessao_treino` 224, `horario_grade` 37, `avaliacao_medida` 2908, `metrica` 109, `evolucao` 22.

## 7. Task 2.5 e pendências de negócio

A investigação da 2.5 registrou questões que não se resolvem por suposição técnica:

- **Altura** (pendência 2): lida sem conversão; valores ambíguos ficam sinalizados e fora dos indicadores de evolução.
- **`slalom_wallball`** (pendência 3): mantida no catálogo sem unidade, direção ou método inventados.
- **`notifications`** (pendência 6): fora da carga analítica inicial, sem descarte do histórico.

Tabelas com 100% das linhas marcadas com pendência, todas explicadas:

| Tabela | Linhas | Motivo |
|---|---|---|
| `aluno` | 106/106 | data de entrada aproximada (= criação do cadastro) — `20_carga_cadastro.sql` |
| `matricula` | 106/106 | início aproximado (= criação do cadastro) — `30_carga_comercial.sql` |
| `horario_grade` | 37/37 | grade reconstruída das regras do app, compartilhada entre unidades — `PENDENCIAS.md` |
| `configuracao_unidade` | 2/2 | tabela criada fora do conceitual para `app_settings` — `PENDENCIAS.md` |

Pendências de negócio em aberto (`dados/migracoes/PENDENCIAS.md`):

| # | Assunto | Quem decide |
|---|---|---|
| 2 | Unidades e faixas dos testes físicos; alturas ambíguas | Coordenação técnica esportiva |
| 3 | `slalom_wallball`: unidade e direção | Coordenação técnica esportiva |
| 4 | Destino de CPF, e-mail, endereço etc. da fisio | Direção |
| 5 | Quem vê anamnese e dado clínico | Direção, com respaldo jurídico |
| 6 | Migrar ou não `notifications` | Grupo, validar com o cliente |
| 7 | Nome do schema definitivo e quem cria o projeto | Grupo + coordenação |
| 8 | Grade de horários reconstruída | Coordenação |
| 9 | Regras de planos e créditos do PKZ | Comercial / direção |
| 10 | Admins atuando como profissional | Coordenação |
| 11 | Dados pessoais no `payload` da auditoria | Frente 3 |
| 12 | Agendamentos de especialista sem profissional | Coordenação |
| 13 | 3 saldos guardados diferentes do extrato | Comercial / coordenação |
| 14 | Agendamentos acima da capacidade; relatórios duplicados | Coordenação |
| 15 | Papel `professor` sem sufixo | Coordenação |

Os registros afetados entraram e estão marcados; nenhuma dessas pendências é divergência técnica.

## 8. Próximas ações

- Revisar e integrar o **PR #8** (Task 2.3) e o **PR #7** (Task 2.5).
- Aprovar este relatório (seção 9), o que fecha a Task 2.6 e a Frente 2.
- Levar as 14 pendências de negócio a quem decide; as decisões entram em `PENDENCIAS.md` antes de qualquer alteração na carga.
- Confirmar e apagar `novo_pre_ensaio_geral` (com as `avulsa_*`) pelo SQL Editor.
- Repetir as conferências (preflight + `06`) na execução definitiva do ENT-002, depois do marco M2.

## 9. Aprovação

| Papel | Nome | Decisão | Data |
|---|---|---|---|
| Dono da Frente 2 | Rafael | | |
| Revisão (Frente 1) | | | |
| Coordenação / gerência | | | |

## Limitações do relatório

- **Ensaio, não produção.** A origem é uma cópia descaracterizada da produção, que continua mudando; os números valem para a foto de 12/10.
- **FKs fora da lista do `06`** (`bloqueio_grade`, `horario_grade`, `sessao_treino`, `lista_espera`, `avaliacao_medida`, `evolucao`, `consentimento`, `relatorio_emissao`, `relatorio_envio`, `notificacao`, `acesso_dado_sensivel`) não foram conferidas por consulta de órfãos. Na auditoria de 24/10 (Frente 1), as 89 FKs do `novo` estavam todas validadas pelo banco (`convalidated`), o que impede órfãos.
- **`avaliacao_medida` (2908)** foi conferida por amostra campo a campo, não por contagem total contra os valores preenchidos da origem.
- **Blocos 5 e 7** rodaram em forma agregada para não expor uuids; desde a revisão de 25/10 (PR #8) o próprio `06_destino_carga.sql` usa essas formas agregadas.
- **Atendimento:** a explicação do serviço vem do código e das contagens, sem reexecução da amostra.
- **Descaracterização da cópia:** as ressalvas sobre a descaracterização da cópia de ensaio foram passadas à gerência pelo canal interno e não ficam no repositório (regra do README: achado de segurança sobre o dado do cliente não vai para PR, issue ou commit). Em `novo`, o acesso é definido pela migration 012 (Frente 3) e pela pendência 5.
- Este relatório não contém dados pessoais: só contagens, status e nomes de objetos.

**Evidências:** `conferencia/README.md`; `conferencia/resultados/preflight_2026-10-21.md` e `destino_carga_2026-10-21.md` (PR #8); `conferencia/TASK_2_4_AMOSTRAS.md`; `dados/migracoes/TASK-2.5-PENDENCIAS-SIGNIFICADO.md` (PR #7); `dados/migracoes/conferencia/`; `dados/migracoes/PENDENCIAS.md`; `dados/migracoes/mapeamento/README.md`.
