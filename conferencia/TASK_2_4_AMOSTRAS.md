# Task 2.4 — Amostras de ponta a ponta por domínio

Status: documento consolidado com evidências de rodadas anteriores e da investigação read-only mais recente; nenhuma consulta adicional é executada nesta revisão.

## Regras de registro

- Registrar apenas identificadores técnicos, resultados e observações de transformação.
- Não registrar nome, CPF, telefone, e-mail, endereço, foto, texto livre de saúde ou qualquer outro dado pessoal.
- Para campos pessoais, conferir igualdade/transformação sem copiar o valor; usar `correspondente`, `nulo em ambos`, `divergente` ou `não conferido`.
- Os valores de origem/destino só devem ser registrados quando não forem pessoais e forem necessários para explicar a regra; caso contrário, registrar apenas o tipo de comparação e o resultado.
- `PENDENTE` significa que a seleção ou a conferência ainda não ocorreu. Não é resultado de uma consulta.
- Este documento não homologa a Task 2.3 nem a Task 2.4.

## Domínios e classificação dos mapeamentos

Os sete domínios abaixo aparecem no mapa de carga local. A classificação é por relação origem → destino, não apenas por domínio. `VALIDA` no mapa de carga significa que há uma regra de contagem no SQL; não significa que a correspondência campo a campo foi homologada.

| Domínio | Origem → destino confirmado | Situação do mapeamento | Evidência no repositório |
|---|---|---|---|
| Cadastro | `origem.profiles` → `novo.perfil_usuario`; `origem.athletes` → `novo.aluno` | `profiles` validável; atletas parcial | `conferencia/sql/06_destino_carga.sql`, linhas do mapeamento `cadastro` |
| Comercial e créditos | `origem.athletes` → `novo.matricula`; `origem.credit_transactions` → `novo.credito_lancamento`; saldo → `novo.vw_saldo_credito` | matrícula parcial; créditos validáveis por contagem/regra; view requer preflight | `conferencia/sql/05_creditos_origem.sql`, `00_preflight_destino.sql`, `06_destino_carga.sql` |
| Agenda | `origem.schedule_blocks` → `novo.bloqueio_agenda`; `origem.bookings` → `novo.agendamento`; `origem.waitlist` → `novo.lista_espera`; `origem.training_feedback` → `novo.feedback_treino` | validável por contagem no mapa existente; campo a campo ainda pendente | `conferencia/sql/06_destino_carga.sql` |
| Relatórios | `origem.training_report_materials` → `novo.catalogo_item` (`dominio='material'`); `origem.training_report_technologies` → `novo.catalogo_item` (`dominio='tecnologia'`); `origem.training_reports` → `novo.relatorio_treino` | validável por contagem; transformação de catálogo precisa ser conferida | `conferencia/sql/06_destino_carga.sql` |
| Avaliações | `origem.physical_test_sessions` → `novo.avaliacao` (`tipo='teste_fisico'`); `origem.weekly_evaluations` → `novo.avaliacao` (`tipo='semanal'`) | validável por tipo/contagem; JSON e medidas exigem conferência segura | `conferencia/sql/02_testes_fisicos_json.sql`, `06_destino_carga.sql` |
| Atendimento | `origem.physio_assessments` → `novo.avaliacao` (`tipo='fisioterapia'`) e `novo.anamnese`; `origem.physio_evolutions` → `novo.atendimento`; `origem.specialist_evolutions` → `novo.atendimento` | avaliações/anamneses parcial; evoluções marcadas válidas no mapa; `pkz_data` requer preflight | `conferencia/sql/03_fisioterapia_medidas.sql`, `00_preflight_destino.sql`, `06_destino_carga.sql` |
| Documentos e auditoria | caminhos de `student_files`, `nutritionist_files`, `physio_evolutions`, `specialist_evolutions`, `training_reports`, `physical_test_comparisons`, `physio_assessments`, `student_tests` → `novo.arquivo`; `activity_logs`/`booking_audit_logs` → `novo.evento_auditoria` | arquivos são origem derivada por caminho distinto; auditoria depende de tabelas de origem não listadas nas 28 conferidas | `conferencia/sql/04_arquivos_origem.sql`, `06_destino_carga.sql` |

### Classificação detalhada e chaves disponíveis

| Relação | Classificação | Chave ou evidência disponível | Limite atual |
|---|---|---|---|
| `origem.profiles` → `novo.perfil_usuario` | `CONFIRMADO_NO_REPOSITORIO` | mapa de carga `cadastro/profiles`; destino usa `usuario_id` nas FKs | colunas equivalentes de perfil não estão documentadas localmente |
| `origem.athletes` → `novo.aluno` | `PARCIALMENTE_CONFIRMADO` | mapa de carga `cadastro/athletes`; destino usa `aluno.id` e relações técnicas | chave origem → destino e colunas de cadastro não estão explicitadas |
| `origem.athletes` → `novo.matricula` | `PARCIALMENTE_CONFIRMADO` | mapa `comercial/athletes`; `novo.matricula.aluno_id` é confirmado por FK | não há evidência de qual chave/critério cria a matrícula |
| `origem.credit_transactions` → `novo.credito_lancamento` | `CONFIRMADO_NO_REPOSITORIO` | mapa `comercial/credit_transactions`; regra de `athlete_id`, `delta`, `created_at`, `id` em `conferencia/sql/05_creditos_origem.sql:7-34`; FKs do destino em `06_destino_carga.sql:174-177` | associação de cada ID de origem ao ID de destino ainda depende da consulta real |
| `origem.schedule_blocks` → `novo.bloqueio_agenda` | `CONFIRMADO_NO_REPOSITORIO` | `573f2bb:dados/migracoes/mapeamento/agenda.csv:15-27`: `id` direto e transformações de programa, serviço e weekday | confirmar que o commit histórico é a versão autorizada da carga atual |
| `origem.bookings` → `novo.agendamento` | `CONFIRMADO_NO_REPOSITORIO` | `573f2bb:dados/migracoes/mapeamento/agenda.csv:32-48`: `id` direto e campos de atleta, serviço, data, horários e status | unidade, grade, duração e cancelamento são derivados por regras documentadas; falta validar a execução real |
| `origem.waitlist` → `novo.lista_espera` | `CONFIRMADO_NO_REPOSITORIO` | `573f2bb:dados/migracoes/mapeamento/agenda.csv:59-71`: `id` direto e `athlete_id/service/slot_date/start_time` | unidade é derivada de `novo.unidade_atual_do_aluno`; carga histórica registrava a origem como vazia |
| `origem.training_feedback` → `novo.feedback_treino` | `CONFIRMADO_NO_REPOSITORIO` | `573f2bb:dados/migracoes/mapeamento/agenda.csv:72-82`: `id` direto e `booking_id → agendamento_id` | exige agendamento correspondente; `athlete_id` da origem não é migrado (`agenda.csv:87`) |
| `origem.training_report_materials` → `novo.catalogo_item` | `PARCIALMENTE_CONFIRMADO` | filtro de destino `dominio='material'` e `id_origem` no mapa `relatorio` | regra de normalização e chave de origem não estão documentadas |
| `origem.training_report_technologies` → `novo.catalogo_item` | `PARCIALMENTE_CONFIRMADO` | filtro de destino `dominio='tecnologia'` e `id_origem` no mapa `relatorio` | regra de normalização e chave de origem não estão documentadas |
| `origem.training_reports` → `novo.relatorio_treino` | `CONFIRMADO_NO_REPOSITORIO` | mapa `relatorio/training_reports`; caminhos `file_path` e `pdf_storage_path` em `04_arquivos_origem.sql:12-13` | campos não relacionados a arquivo ainda precisam de evidência |
| `origem.physical_test_sessions` → `novo.avaliacao(tipo='teste_fisico')` | `PARCIALMENTE_CONFIRMADO` | mapa `avaliacao`; `data` JSONB da origem é confirmado em `02_testes_fisicos_json.sql:2-35` | chave e regra de expansão de cada campo JSON não estão documentadas |
| `origem.weekly_evaluations` → `novo.avaliacao(tipo='semanal')` | `PENDENTE_DE_EVIDENCIA` | somente o par e o filtro de tipo aparecem no mapa | nenhuma coluna de correspondência foi documentada |
| `origem.physio_assessments` → `novo.avaliacao`/`novo.anamnese` | `PARCIALMENTE_CONFIRMADO` | mapa `atendimento`; 14 medidas confirmadas em `03_fisioterapia_medidas.sql:6-30`; `pkz_data` exige preflight em `00_preflight_destino.sql:258-264` | relação entre ID da origem e cada destino não está explícita |
| `origem.physio_evolutions` → `novo.atendimento` | `CONFIRMADO_NO_REPOSITORIO` | mapa usa `EXISTS` por `o.id=a.id` em `06_destino_carga.sql:29` | igualdade de ID é evidência do SQL de contagem, não conferência campo a campo |
| `origem.specialist_evolutions` → `novo.atendimento` | `CONFIRMADO_NO_REPOSITORIO` | mapa usa `EXISTS` por `o.id=a.id` em `06_destino_carga.sql:30` | igualdade de ID é evidência do SQL de contagem, não conferência campo a campo |
| nove referências de arquivo → `novo.arquivo` | `PARCIALMENTE_CONFIRMADO` | nove colunas de caminho em `04_arquivos_origem.sql:7-16`; destino agrega caminhos distintos em `06_destino_carga.sql:58-78` | origem é derivada por caminho; não há chave única origem → arquivo para todos os casos |
| `origem.activity_logs`/`booking_audit_logs` → `novo.evento_auditoria` | `PENDENTE_DE_EVIDENCIA` | par aparece no mapa `documentos` e FKs do destino em `06_destino_carga.sql:198-199` | não há consulta local de colunas/chaves de origem para selecionar registros |

### Mapeamentos não confirmados

- Não há no repositório DDL, migrations ou código de carga completos que permitam confirmar todas as colunas campo a campo.
- As colunas de origem/destino e regras abaixo são confirmadas somente quando aparecem nas consultas existentes; o restante deve ser obtido por introspecção autorizada e documentação da carga.
- `activity_logs` e qualquer objeto não presente na relação de 28 tabelas de `origem` devem permanecer pendentes até confirmação do objeto.
- Não inferir correspondência de `origem.athletes` para toda a estrutura de cadastro/comercial além das linhas explicitamente mapeadas.

## Matriz de amostragem

Cada domínio precisa de três casos reais. Os IDs ficam em branco até consultas autorizadas. A seleção deve ser baseada em contagens, cardinalidade e sinais de transformação — nunca em escolha arbitrária. As consultas candidatas estão em `conferencia/sql/07_amostras_task_2_4.sql`; elas não conferem origem contra destino.

| ID do caso | Domínio | Perfil exigido | Critério objetivo de seleção | Origem | Destino | Status |
|---|---|---|---|---|---|---|
| CAD-MUITOS | Cadastro | muitos dados relacionados | atleta com maior cardinalidade combinada de serviços, créditos, agendamentos e relatórios entre os candidatos | `origem.athletes.id=45127afd-89b7-4bed-91f4-766a87795003` | `novo.aluno.id=45127afd-89b7-4bed-91f4-766a87795003` | PENDENTE |
| CAD-POUCOS | Cadastro | poucos dados relacionados | atleta com 1 serviço, 1 crédito, 1 agendamento e 0 relatórios | `origem.athletes.id=fef570ee-eb22-40ab-8d87-9595b04fb358` | `novo.aluno.id=fef570ee-eb22-40ab-8d87-9595b04fb358` | PENDENTE |
| CAD-ESTRANHO | Cadastro | limítrofe/inconsistente | categoria nula na origem e no destino, transformação documentada para nulo | `origem.athletes.id=01f145d0-0e50-4157-a316-08f52b99717b` | `novo.aluno.id=01f145d0-0e50-4157-a316-08f52b99717b` | PENDENTE |
| COM-MUITOS | Comercial e créditos | muitos dados relacionados | combinação com maior extrato e renovação identificável | `origem.credit_transactions.athlete_id=42a0cc27-9517-4162-80d5-e4de262d98ad`, serviço `treino` | `novo.credito_lancamento.aluno_id=42a0cc27-9517-4162-80d5-e4de262d98ad`, serviço `treino` | RESOLVIDA |
| COM-POUCOS | Comercial e créditos | poucos dados relacionados | combinação com 1 lançamento, sem renovação identificável | `origem.credit_transactions.athlete_id=99ef8a9b-c89a-41cf-8c95-0b6ae60457f1`, serviço `fisioterapia` | `novo.credito_lancamento.aluno_id=99ef8a9b-c89a-41cf-8c95-0b6ae60457f1`, serviço `fisioterapia` | PENDENTE |
| COM-ESTRANHO | Comercial e créditos | limítrofe/inconsistente | caso com renovação identificável e verificação da reconstrução sem reset fixo | `origem.credit_transactions.athlete_id=01f145d0-0e50-4157-a316-08f52b99717b`, serviço `treino` | `novo.credito_lancamento.aluno_id=01f145d0-0e50-4157-a316-08f52b99717b`, serviço `treino` | PENDENTE |
| AGE-MUITOS | Agenda | muitos dados relacionados | aluno/serviço com maior quantidade de bookings, mais feedbacks associados e, quando aplicável, sessão de treino; selecionado por IDs técnicos | origem.bookings.athlete_id=2b283058-f5fd-4113-b1fe-22bd88fce6b5, serviço treino | novo.agendamento.aluno_id=2b283058-f5fd-4113-b1fe-22bd88fce6b5, serviço treino | PENDENTE |
| AGE-POUCOS | Agenda | poucos dados relacionados | caso válido com um único booking e sem feedback/sessão relacionados | origem.bookings.athlete_id=098fc093-7696-4907-9d50-19e79ba23348, serviço treino | novo.agendamento.aluno_id=098fc093-7696-4907-9d50-19e79ba23348, serviço treino | PENDENTE |
| AGE-ESTRANHO | Agenda | limítrofe/inconsistente | agendamento especializado sem profissional, com grade presente e sem atendimento relacionado | origem.bookings.id=0772d2ff-6e95-4a6e-87d9-f554ab52a20f (chave documentada) | novo.agendamento.id=0772d2ff-6e95-4a6e-87d9-f554ab52a20f | PENDENTE |

### Seleção planejada — Agenda

Os três casos permanecem sem IDs e sem resultado até uma consulta autorizada. As chaves e campos abaixo são a estrutura esperada para a conferência, não evidência de execução.

| Caso | Chave de origem | Chave de destino | Campos mínimos a comparar | Transformações/regras a verificar |
|---|---|---|---|---|
| `AGE-MUITOS` | `bookings.id`; relações por `training_feedback.booking_id` e, se aplicável, `waitlist.id`/`schedule_blocks.id` | `agendamento.id`; `feedback_treino.agendamento_id`; `lista_espera.id`; `bloqueio_agenda.id` | IDs, `athlete_id/aluno_id`, serviço, data, hora inicial/final, status, profissional e cardinalidades relacionadas | serviço por código; unidade por `unidade_atual_do_aluno`; duração por regras do app; `weekday % 7`; feedback ligado ao agendamento |
| `AGE-POUCOS` | `bookings.id` ou `waitlist.id`, conforme o vínculo selecionado | `agendamento.id` ou `lista_espera.id` | ID, aluno, serviço, data, horário, status e presença/ausência de feedback | valores diretos; nulos permitidos; rejeições não devem ser tratadas como caso válido |
| `AGE-ESTRANHO` | ID do registro rejeitado ou do `booking` com condição limítrofe | ID correspondente, ou ausência no destino com registro em `carga_rejeitado` | ID, motivo/status, campos nulos, horários, serviço, profissional e existência do destino/rejeição | rejeição por regra documentada; profissional deduzido de `specialist_evolutions`; ausência de grade/capacidade como pendência, não como divergência automática |

Evidência documental: `573f2bb:dados/migracoes/mapeamento/agenda.csv:15-29,32-48,59-82`; a execução histórica também descreve as rejeições e junções em `573f2bb:dados/migracoes/carga/40_carga_agenda.sql:65-120,250-288`.

Evidência da seleção real, somente leitura: 	ransaction_read_only=on, schemas origem/
ovo acessíveis. AGE-MUITOS foi selecionado com 17 registros de origem e destino, 14 ativos em ambos, 10 feedbacks e 10 sessões no destino. AGE-POUCOS foi selecionado com 1 registro de origem e destino, ativo, sem feedback e sem sessão. AGE-ESTRANHO foi selecionado com status presente, serviço isioterapia, profissional nulo, grade presente e sem atendimento relacionado. Nenhum caso foi validado.
### Resultados da comparação — Agenda

Consultas somente leitura realizadas com `transaction_read_only=on`. Os resultados abaixo não homologam o domínio inteiro; registram apenas os casos selecionados.

| Caso | Comparação | Resultado | Evidência técnica |
|---|---|---|---|
| `AGE-MUITOS` | `bookings.id` → `agendamento.id` | `OK` | 17/17 IDs presentes no destino; `aluno_id`, serviço transformado, status, data, hora inicial, profissional, criador, confirmação e criação corresponderam em 17/17. |
| `AGE-MUITOS` | `training_feedback.id` → `feedback_treino.id` | `OK` | 10/10 feedbacks presentes; `booking_id` → `agendamento_id` correspondeu em 10/10. |
| `AGE-MUITOS` | `bookings` presentes → `sessao_treino.agendamento_id` | `OK` | 10/10 bookings com status `presente` tiveram sessão; a relação por `agendamento_id` correspondeu em 10/10. |
| `AGE-POUCOS` | `bookings.id` → `agendamento.id` | `OK` | 1/1 ID presente; aluno, serviço transformado, status, data, hora inicial, profissional, criador, confirmação e criação corresponderam. `hora_fim` do destino estava preenchida. |
| `AGE-POUCOS` | `training_feedback` e sessão | `OK` | 0 feedbacks na origem/destino e 0 sessões para o caso selecionado. |
| `AGE-ESTRANHO` | `bookings.id` → `agendamento.id` | `OK` | ID presente; serviço `fisioterapeuta` → `fisioterapia`, status `presente` e profissional nulo corresponderam. |
| `AGE-ESTRANHO` | grade e atendimento | `INCONCLUSIVO` | `horario_grade_id` preenchido e grade existente; `hora_inicio=17:45`, `hora_fim=18:00`; não havia atendimento relacionado. A ausência de profissional/atendimento não foi classificada como erro sem regra adicional. |

Não foram encontrados `AUSENTE_NO_DESTINO` ou `AUSENTE_NA_ORIGEM` nesses três casos. `AGE-MUITOS` e `AGE-POUCOS` não foram marcados como divergentes nos campos comparados; a hora final foi tratada como transformação derivada e apenas sua presença foi verificada, não recalculada independentemente.
| REL-MUITOS | Relatórios | muitos dados relacionados | relatório com maior cardinalidade de itens e referências de arquivo | `origem.training_reports.id=aa6d5e7e-9afc-4dfc-86f4-6368373a85c0` | `novo.relatorio_treino.id=aa6d5e7e-9afc-4dfc-86f4-6368373a85c0` | PENDENTE |
| REL-POUCOS | Relatórios | poucos dados relacionados | relatório com menor cardinalidade de itens, sem vínculo de agendamento | `origem.training_reports.id=2cee422b-a66b-47ac-9e83-a755db41755f` | `novo.relatorio_treino.id=2cee422b-a66b-47ac-9e83-a755db41755f` | PENDENTE |
| REL-ESTRANHO | Relatórios | limítrofe/inconsistente | cinco relatórios para o mesmo agendamento, todos com pendência documentada | `origem.training_reports.id=37d5a063-c358-45f2-ac77-0d5ba85578e1`; `booking_id=3d7d7197-1883-4ab5-87e9-575321a157cd` | `novo.relatorio_treino.id=37d5a063-c358-45f2-ac77-0d5ba85578e1`; `agendamento_id=3d7d7197-1883-4ab5-87e9-575321a157cd` | PENDENTE |
| AVA-MUITOS | Avaliações | muitos dados relacionados | atleta com maior número de sessões/testes e medidas não nulas | `PENDENTE` | `PENDENTE` | `PENDENTE` |
| AVA-POUCOS | Avaliações | poucos dados relacionados | avaliação com menor número de campos/medidas preenchidos, sem ser inválida | `PENDENTE` | `PENDENTE` | `PENDENTE` |
| AVA-ESTRANHO | Avaliações | limítrofe/inconsistente | JSON vazio/não objeto, valor implausível, nulo ou duplicidade de avaliação | `PENDENTE` | `PENDENTE` | `PENDENTE` |
| ATD-MUITOS | Atendimento | muitos dados relacionados | avaliação/evolução com maior conjunto de medidas e arquivos relacionados | `PENDENTE` | `PENDENTE` | `PENDENTE` |
| ATD-POUCOS | Atendimento | poucos dados relacionados | registro válido com menor conjunto de medidas/relacionamentos | `PENDENTE` | `PENDENTE` | `PENDENTE` |
| ATD-ESTRANHO | Atendimento | limítrofe/inconsistente | `pkz_data` não objeto, medida nula/implausível, caminho duplicado ou relação ausente | `PENDENTE` | `PENDENTE` | `PENDENTE` |
| DOC-MUITOS | Documentos e auditoria | muitos dados relacionados | entidade com maior quantidade de caminhos distintos e eventos relacionados | `PENDENTE` | `PENDENTE` | `PENDENTE` |
| DOC-POUCOS | Documentos e auditoria | poucos dados relacionados | entidade com um único caminho/evento conferível | `PENDENTE` | `PENDENTE` | `PENDENTE` |
| DOC-ESTRANHO | Documentos e auditoria | limítrofe/inconsistente | caminho vazio/duplicado, referência sem destino ou tabela de auditoria não confirmada | `PENDENTE` | `PENDENTE` | `PENDENTE` |

### Resultados da comparação — Relatórios

Consultas somente leitura realizadas com `transaction_read_only=on`. Os resultados abaixo não homologam o domínio inteiro.

| Caso | Comparação | Resultado | Evidência técnica |
|---|---|---|---|
| `REL-MUITOS` | `training_reports.id → relatorio_treino.id`, aluno, agendamento, tipo, status, data, hora inicial, criador e criação | `OK` | ID presente; campos comparáveis corresponderam; 17 itens de origem e 17 `relatorio_item`; 0 itens sem catálogo; 1 arquivo no destino para 2 referências de origem. |
| `REL-MUITOS` | arrays de itens → `relatorio_item`/`catalogo_item` | `OK` | 17/17 itens materializados e catalogados. |
| `REL-POUCOS` | `training_reports.id → relatorio_treino.id`, aluno, agendamento nulo, tipo, status, data, criador e criação | `OK` | ID presente; campos comparáveis corresponderam; agendamento nulo em ambos; 1 item de origem e 1 `relatorio_item`; sem item sem catálogo. |
| `REL-POUCOS` | hora inicial/final | `INCONCLUSIVO` | hora inicial nula na origem/destino; hora final não preenchida no destino. Não foi classificado como divergência sem regra adicional. |
| `REL-ESTRANHO` | `training_reports.id → relatorio_treino.id`, aluno, agendamento, tipo, status, data, hora inicial, criador e criação | `OK` | ID presente e campos comparáveis correspondentes; 3 itens de origem e 3 `relatorio_item`; 0 itens sem catálogo. |
| `REL-ESTRANHO` | múltiplos relatórios por agendamento | `INCONCLUSIVO` | 5 relatórios na origem e 5 no destino para o mesmo agendamento; todos os 5 destinos têm pendência. A migration prevê essa situação, sem tratá-la automaticamente como erro. |

Não foram encontrados `AUSENTE_NO_DESTINO` ou `AUSENTE_NA_ORIGEM` nos três IDs selecionados. Arquivos foram comparados apenas por cardinalidade/presença: 2 referências de origem contra 1 arquivo destino nos casos com arquivos; a regra direciona os caminhos ao domínio Documentos.

### Resultados da comparação — Cadastro

Consultas somente leitura realizadas com `transaction_read_only=on`. Foram comparados apenas campos com regra documentada em `dados/migracoes/mapeamento/cadastro.csv` (commit histórico `573f2bb`).

| Caso | Comparação | Resultado | Evidência técnica |
|---|---|---|---|
| `CAD-MUITOS` | `athletes.id → aluno.id` e `pessoa_id` | `OK` | ID e `pessoa_id` corresponderam; `status` e `criado_em` também corresponderam; `data_saida` nula conforme regra. Cardinalidades: 3 serviços, 28 créditos, 24 agendamentos e 6 relatórios em origem/destino. |
| `CAD-POUCOS` | `athletes.id → aluno.id` e `pessoa_id` | `OK` | ID e `pessoa_id` corresponderam; `status` e `criado_em` corresponderam; `data_saida` nula conforme regra. Cardinalidades: 1 serviço, 1 crédito, 1 agendamento e 0 relatórios em origem/destino. |
| `CAD-ESTRANHO` | `athletes.category` → `aluno.categoria` | `OK` | Categoria nula na origem e no destino; a regra documenta vazio → nulo. |
| `CAD-ESTRANHO` | `athletes.id → aluno.id` e campos estruturais` | `OK` | ID, `pessoa_id`, `status`, `criado_em` e `data_saida` corresponderam à regra documentada. |

Não foram encontrados `AUSENTE_NO_DESTINO` ou `AUSENTE_NA_ORIGEM` nos três casos. Não foram copiados campos pessoais; os campos de identidade da `pessoa` não foram expostos.

### Resultados da comparação — Comercial e créditos

Consultas somente leitura realizadas com `transaction_read_only=on`. A regra aplicada foi a da Task 2.1: última renovação identificável por aluno/serviço, `delta` da renovação uma vez e lançamentos posteriores ordenados por `(created_at,id)`; sem reset fixo para 10.

| Caso | Comparação | Resultado | Evidência técnica |
|---|---|---|---|
| `COM-MUITOS` | lançamentos origem → `credito_lancamento.id` e serviço/aluno | `INCONCLUSIVO` | 19 lançamentos e 13 renovações identificáveis na origem contra 21 e 15 no destino para o par selecionado; a correspondência individual dos lançamentos adicionais não foi comprovada nesta consulta. |
| `COM-MUITOS` | saldo reconstruído → `vw_saldo_credito` | `OK` | última renovação identificável `ae647662-7de6-4391-b309-59c4de533fe5`; saldo reconstruído `6` e saldo destino `6`; 0 lançamentos posteriores. |
| `COM-POUCOS` | lançamento origem → destino | `OK` | 1/1 lançamento com mesmo ID e delta; serviço `fisioterapia`. |
| `COM-POUCOS` | saldo reconstruído | `INCONCLUSIVO` | não há renovação identificável; a regra histórica não autoriza reconstrução por reset fixo. O saldo destino observado foi `-1`, sem classificação de erro. |
| `COM-ESTRANHO` | saldo reconstruído → `vw_saldo_credito` | `OK` | última renovação identificável `43883105-b79b-4683-b6de-5932ae0c76b6`; saldo reconstruído `8` e saldo destino `8`; 0 lançamentos posteriores. |

Não foram encontrados lançamentos de renovação sem `renovacao_id` nem renovações sem lançamento no destino nas verificações realizadas. Nenhum saldo foi corrigido.

### Complemento — COM-MUITOS

Consulta somente leitura confirmada com `transaction_read_only=on`. A comparação dos conjuntos de IDs técnicos, restrita ao aluno e ao serviço `treino` pela regra documentada, encontrou `0` lançamentos na origem sem destino e `0` lançamentos no destino sem origem. Os registros exibidos como adicionais no destino correspondem a IDs técnicos existentes na origem; portanto, não há evidência de duplicação ou geração sem origem. A diferença agregada `19/13` contra `21/15` permanece `INCONCLUSIVA`: falta reproduzir a mesma classificação de serviço e de renovação usada em cada contagem e explicar a agregação das competências. Saldo reconstruído e view destino continuam `6`; nenhum dado foi alterado.

### Resultados da comparação — Avaliações

Consultas somente leitura realizadas com `transaction_read_only=on`. Foram usados os mapeamentos `physical_test_sessions.id → avaliacao.id`, `athlete_id → aluno_id`, `test_date → data`, `evaluator_id → avaliador_id`, `created_by → criado_por`, com `tipo='teste_fisico'`; medidas seguem a regra de `avaliacao_metricas.csv` e `006_avaliacao.sql`.

| Caso | Comparação | Resultado | Evidência técnica |
|---|---|---|---|
| `AVA-MUITOS` | sessões físicas → avaliações | `OK` | aluno técnico `182b7b64-0894-4c6a-bd33-8328eff88d79`: 5 sessões, 5 IDs correspondentes, 5 datas, 5 avaliadores e 5 criadores correspondentes; destino com 230 medidas. |
| `AVA-POUCOS` | sessão física → avaliação | `OK` | aluno técnico `098fc093-7696-4907-9d50-19e79ba23348`: 1 sessão, 1 ID correspondente, data/avaliador/criador correspondentes; destino com 54 medidas. |
| `AVA-ESTRANHO` | nulos de altura/peso → medidas | `OK` | sessão `79c56c69-7d32-499f-af8d-d046ef14c914`: `altura` e `peso` nulos na origem; regra documentada não gera medidas para esses campos; avaliação correspondente consolidada com 43 medidas. |

As medidas JSON dos casos ainda não foram comparadas campo a campo; a conclusão acima cobre somente as chaves, campos escalares e a regra documentada de nulidade. Não foram expostos dados pessoais.
### Comparação campo a campo — Avaliações

Consultas somente leitura confirmadas com `transaction_read_only=on`. A comparação aplicou as regras documentadas de nomenclatura, lados, tentativas, conversão decimal e `mm:ss` para segundos.

| Caso | Medidas numéricas de origem | Correspondentes no destino | Ausentes no destino | Divergências de valor | Medidas no destino | Resultado |
|---|---:|---:|---:|---:|---:|---|
| `AVA-MUITOS` | 230 | 230 | 0 | 0 | 230 | `OK` |
| `AVA-POUCOS` | 54 | 54 | 0 | 0 | 54 | `OK` |
| `AVA-ESTRANHO` | 43 | 43 | 0 | 0 | 43 | `OK` |

Evidência técnica: correspondência por `(avaliacao.id, metrica.codigo, lado, tentativa)`; valores comparados após a transformação documentada. No caso `AVA-ESTRANHO`, altura e peso nulos não geraram medidas, conforme a regra. Não foram expostos valores pessoais.

### Resultados da comparação — Atendimento

Consultas somente leitura confirmadas com `transaction_read_only=on`. O mapeamento permite `physio_evolutions.id` e `specialist_evolutions.id` diretamente para `novo.atendimento.id`, além de aluno, profissional, serviço e data/evolução.

| Caso | Comparação | Resultado | Evidência técnica |
|---|---|---|---|
| `ATD-MUITOS` | evoluções → atendimentos/evoluções | `INCONCLUSIVO` | 6/6 IDs, alunos, profissionais e datas de evolução correspondentes; 5/6 serviços correspondentes. 1 serviço de origem não foi identificado pelo valor disponível. |
| `ATD-POUCOS` | evolução → atendimento/evolução | `INCONCLUSIVO` | 1/1 ID, aluno, profissional e data de evolução correspondentes; serviço de origem não identificado. |
| `ATD-ESTRANHO` | serviço incomum → atendimento/evolução | `INCONCLUSIVO` | 2/2 IDs, alunos, profissionais e datas correspondentes; serviço de origem desconhecido em 2/2, enquanto o destino materializa `fisioterapia`. O código atual rejeita serviço nulo/desconhecido; a consulta read-only atual não reproduziu a materialização como fisioterapia. A causa não foi comprovada; faltam os IDs dos registros da amostra e o snapshot/execução correspondente. |

Pendência: identificar os registros e o snapshot/execução correspondente à amostra histórica e confirmar como o destino materializou `fisioterapia`. O código atual rejeita serviço nulo/desconhecido; não há fallback comprovado.

### Conclusão específica — COM-MUITOS

A divergência de cardinalidade está resolvida quanto à causa. Os IDs `7c294b06-d447-400c-a06e-f6c4788b7160` e `d115b4ef-53a7-46ac-ad57-30bcbf148c37` existem na origem, mas ficaram fora do recorte de `treino` explicitamente identificado. A carga os classifica como `treino` pelo bucket padrão, explicando a diferença entre 19/13 na origem e 21/15 no destino. A diferença é de recorte/classificação; o saldo coincidente em 6 não elimina a diferença de cardinalidade.

### Resultados da comparação — Documentos e auditoria

Consultas somente leitura confirmadas com `transaction_read_only=on`. A regra aplicada foi um arquivo por `storage_path` distinto não vazio, com vínculo técnico por caminho e `aluno_id`. As tabelas de auditoria existem na origem, mas não foram usadas como amostras porque suas colunas de negócio não foram comparadas nesta etapa.

| Caso | Comparação | Resultado | Evidência técnica |
|---|---|---|---|
| `DOC-MUITOS` | caminhos de arquivos → `novo.arquivo` | `OK` | aluno técnico `34159ea4-17e7-4128-a189-ea436b48c175`: 28 caminhos distintos e 42 referências na origem; 28/28 arquivos correspondentes no destino, todos vinculados ao mesmo aluno. 28 caminhos tiveram referências duplicadas, conforme a regra de deduplicação por caminho. |
| `DOC-POUCOS` | caminho de arquivo → `novo.arquivo` | `OK` | aluno técnico `098fc093-7696-4907-9d50-19e79ba23348`: 1 caminho e 1 referência na origem; 1/1 arquivo correspondente e vínculo técnico ao aluno. |
| `DOC-ESTRANHO` | caminho compartilhado por referências | `OK` | hash técnico `0032a853c66a580b3c1a4ca594ceee01`: 2 referências de origem, 1 fonte lógica e 1 arquivo correspondente no destino, com vínculo técnico preservado; deduplicação por `storage_path` comprovada. |

Não foram comparados conteúdos, URLs, nomes ou dados pessoais. Auditoria (`activity_logs`/`booking_audit_logs` → `novo.evento_auditoria`) permanece pendente de conferência campo a campo.
### Complemento — DOC-ESTRANHO e Auditoria

Consulta somente leitura confirmada com `transaction_read_only=on`.

`DOC-ESTRANHO`: um caminho compartilhado foi identificado apenas pelo hash técnico `0032a853c66a580b3c1a4ca594ceee01`, sem expor o caminho. Havia 2 referências de origem provenientes de 1 fonte lógica e 1 arquivo no destino, com vínculo a 1 aluno e 1 dono técnico. A cardinalidade e a deduplicação por `storage_path` estão comprovadas; o conteúdo e os vínculos pessoais não foram selecionados. Resultado: `OK` para deduplicação/correspondência técnica.

Atendimento: a regra documentada resolve `physio_evolutions` como `fisioterapia` e valores conhecidos de `specialist_evolutions.service` (`treino`, `fisioterapeuta`, `nutricionista`, `psicologo`). A amostra histórica registrou serviço de origem desconhecido e `fisioterapia` no destino, mas a consulta read-only mais recente não reproduziu esse resultado. A causa não foi comprovada; faltam os IDs técnicos dos registros e a identificação do snapshot/execução correspondente. O caso permanece `INCONCLUSIVO`.

### Resultados da comparação — Auditoria

O mapeamento comprova a chave `(tabela_origem, id_origem)` e as transformações de `entity`, `booking_id`, ações padronizadas, ator e data. Três casos técnicos foram comparados, sem dados pessoais:

| Caso | Origem | Destino | Resultado | Evidência técnica |
|---|---|---|---|---|
| `AUD-ATV-01` | `activity_logs.id` | `evento_auditoria.tabela_origem/id_origem` | `OK` | ID, tabela de origem, ação, entidade, entidade_id e timestamp correspondentes; `booking` foi normalizado para `agendamento`. |
| `AUD-ATV-02` | `activity_logs.id` | `evento_auditoria.tabela_origem/id_origem` | `OK` | ID e campos técnicos correspondentes; evento de sistema sem ator permaneceu com ator nulo e entidade_id nulo conforme regra. |
| `AUD-BOOK-01` | `booking_audit_logs.id` | `evento_auditoria.tabela_origem/id_origem` | `OK` | ID, booking_id→entidade_id, ação e timestamp correspondentes; ação `professor_assigned` foi normalizada para `assign_professor`. |

Os casos de auditoria foram comparados por IDs, flags de nulidade, entidades, ações e timestamps; payloads e valores potencialmente pessoais não foram expostos. A cobertura integral do domínio de auditoria não foi declarada.

## Instrumento de conferência campo a campo

Uma linha representa um campo conferido. Repetir a linha para cada campo relevante do caso; não preencher com nomes ou conteúdos pessoais.

| Caso | Domínio | Categoria | Tabela origem | ID origem | Tabela destino | ID destino | Campo origem | Campo destino | Regra esperada | Evidência/consulta | Resultado | Observação técnica |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `CAD-MUITOS` | Cadastro | `MUITOS` | `PENDENTE` | `PENDENTE` | `PENDENTE` | `PENDENTE` | `PENDENTE` | `PENDENTE` | `PENDENTE` | `PENDENTE` | `PENDENTE` | `PENDENTE` |

Resultados permitidos: `OK`, `DIVERGENTE`, `AUSENTE_NO_DESTINO`, `AUSENTE_NA_ORIGEM`, `INCONCLUSIVO`, `PENDENTE`.

Para campos pessoais, não registrar valores de origem/destino. Usar apenas `PRESENTE`, `AUSENTE`, `NULO_EM_AMBOS`, `CORRESPONDENTE_SEM_VALOR` ou `NƒO_CONFERIDO`, junto do resultado e da referência da consulta.

## Consultas necessárias — somente após autorização

Nenhum item desta seção foi executado. As consultas devem retornar somente IDs, contagens, flags de nulidade, cardinalidades, tipos e status; não devem selecionar colunas pessoais.

1. **Identidade e pré-condições:** executar manualmente `conferencia/sql/00_preflight_destino.sql`, em ordem, apenas após autorização. Bloqueia qualquer ausência, tipo incompatível, permissão insuficiente, empate de snapshot ou estado inconclusivo.
2. **Seleção por cardinalidade:** executar `conferencia/sql/07_amostras_task_2_4.sql` somente após autorização; a saída retorna candidatos, não amostras validadas.
3. **Correspondência de IDs:** usar `origem_id`, `origem_tabela`, chaves técnicas, `id`, ou relações confirmadas no mapeamento; não usar nome, CPF, telefone ou e-mail para registrar o caso.
4. **Campo a campo:** comparar tipos, nulidade, flags, datas/quantidades não pessoais, referências de arquivo e JSON/medidas somente quando seguros; registrar a regra aplicada e o status, não o dado sensível.
5. **Créditos:** reproduzir a regra de `conferencia/sql/05_creditos_origem.sql`: renovação identificável reinicia pelo `delta`, incluindo-o uma vez, e lançamentos posteriores são somados; tratar empates e ausência de renovação como `INCONCLUSIVO` quando aplicável.
6. **Arquivos:** comparar caminhos apenas por presença, cardinalidade, correspondência técnica ou hash não persistido; não copiar URLs/token/conteúdo.
7. **Auditoria:** não selecionar casos de `activity_logs` ou `booking_audit_logs` enquanto as colunas e chaves de origem não forem confirmadas por evidência local ou consulta autorizada de metadados.

## Próxima execução controlada

- Obter autorização explícita para consultas somente leitura e confirmar o projeto/conexão por canal independente.
- Executar o preflight antes de qualquer seleção; se bloqueado, registrar a pendência sem consultar o restante.
- Gerar os 21 candidatos técnicos e revisar se cada domínio realmente está confirmado.
- Conferir pelo menos três casos reais por domínio, preenchendo o instrumento linha a linha.
- Registrar somente o relatório sanitizado; resultados de produção não devem ser commitados sem aprovação e devem seguir a política do repositório.
