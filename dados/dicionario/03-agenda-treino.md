# Agenda e treino

> Dicionário de dados do schema `novo` · migration 004 e 005 · gerado por `dicionario/gerar_dicionario.py`.

Sensibilidade: `clinico` (dado de saúde), `pessoal` (identifica alguém), `operacional` (rotina do negócio), `tecnico` (controle da carga).

## `horario_grade`

Conceitual: HORÁRIO DE GRADE. Origem: regras das funções is_valid_slot e get_service_day (não há tabela na origem).

Linhas no ensaio de 12/10: **37**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | — | gen_random_uuid() |  | tecnico | Chave primária. |
| `unidade_id` | uuid | não | FK → novo.unidade | public.get_service_day (definição) | treino: uma grade por unidade; fisioterapia, nutricao, psicologia: nulo (grade compartilhada, 009) |  | operacional | Nulo = grade compartilhada entre as unidades (a vaga é a mesma para PKZ e One to One). Divergência registrada do conceitual ("oferece" é 1,1). |
| `servico_id` | uuid | sim | FK → novo.servico | public.get_service_day (definição) | os 4 serviços |  | operacional | Serviço a que o registro se refere. |
| `dia_semana` | smallint | sim |  | public.is_valid_slot (definição) | segunda a sexta (1–5) e sábado (6), em extract(dow); domingo não tem grade |  | operacional | [revisar] |
| `hora_inicio` | time without time zone | sim |  | public.is_valid_slot + get_service_day (definição) | seg–sex: treino PKZ 08:00; treino One to One 06:00; fisioterapia 07:00; nutrição/psicologia 08:00. Sábado: 08:00 para todos (treino: uma faixa 08:00 e outra a partir de 09:00, ver capacidade) |  | operacional | Hora de início. |
| `hora_fim` | time without time zone | sim |  | idem | último início + intervalo. Seg–sex: treino 21:00 (último início 20:00); fisioterapia 20:15; nutrição/psicologia 20:30. Sábado: treino PKZ 12:00; treino One to One 11:30; fisioterapia 11:15; nutrição/psicologia 11:30 |  | operacional | Hora de término. |
| `capacidade` | integer | sim |  | public.service_capacity (definição) | treino 6; treino sábado 08:00 = 10 em faixa própria: PKZ 08:00–09:00 (intervalo 60), One to One 08:00–08:30 (intervalo 30), para que só o início das 08:00 tenha 10, como em service_capacity; fisioterapia, nutrição, psicologia 1 |  | operacional | [revisar] |
| `vigencia_inicio` | date | sim |  | origem.bookings.slot_date | min(slot_date) da origem (início do histórico) |  | operacional | [revisar] |
| `vigencia_fim` | date | não |  | — | nulo |  | operacional | [revisar] |
| `pendencia` | text | não |  | — |  |  | tecnico | Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga. |
| `criado_em` | timestamp with time zone | sim |  | — | now() |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |
| `intervalo_min` | smallint | sim |  | idem | treino PKZ 60; treino One to One: 30 antes das 17:00 e 60 a partir das 17:00 (duas faixas); fisioterapia 15; nutrição/psicologia 30 |  | operacional | Minutos entre os inícios de horário: 15 (fisio), 30 (nutri, psico, One to One antes das 17h) ou 60. |

## `bloqueio_agenda`

Conceitual: BLOQUEIO. Origem: schedule_blocks.

Linhas no ensaio de 12/10: **36**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | origem.schedule_blocks.id | direto |  | tecnico | Chave primária. |
| `unidade_id` | uuid | não | FK → novo.unidade | origem.schedule_blocks.program | nulo → nulo (todas as unidades; 36/36 na foto); senão program: pkz→pkz, one_to_one→one_to_one; busca novo.unidade.id pelo codigo |  | operacional | Unidade (PKZ ou One to One) a que o registro pertence. |
| `servico_id` | uuid | não | FK → novo.servico | origem.schedule_blocks.service | nulo → nulo (todos); senão service: treino→treino, fisioterapeuta→fisioterapia, nutricionista→nutricao, psicologo→psicologia; busca novo.servico.id pelo codigo |  | operacional | Serviço a que o registro se refere. |
| `data` | date | sim |  | origem.schedule_blocks.block_date | direto (no permanente, é a data a partir da qual vale) |  | operacional | Data a que o registro se refere. |
| `permanente` | boolean | sim |  | origem.schedule_blocks.is_permanent | direto |  | operacional | [revisar] |
| `dia_semana` | smallint | não |  | origem.schedule_blocks.weekday | weekday % 7 (a origem usa ISO: 1 = segunda … 7 = domingo; o destino usa dow: 0 = domingo) |  | operacional | [revisar] |
| `hora_inicio` | time without time zone | sim |  | origem.schedule_blocks.start_time | direto |  | operacional | Hora de início. |
| `hora_fim` | time without time zone | sim |  | origem.schedule_blocks.end_time | direto |  | operacional | Hora de término. |
| `motivo` | text | não |  | origem.schedule_blocks.reason | direto |  | operacional | [revisar] |
| `criado_por` | uuid | não | FK → novo.perfil_usuario | origem.schedule_blocks.created_by | direto; sem perfil → nulo |  | operacional | Usuário que criou o registro na origem. |
| `pendencia` | text | não |  | — |  |  | tecnico | Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga. |
| `criado_em` | timestamp with time zone | sim |  | origem.schedule_blocks.created_at | direto |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `bloqueio_grade`

Conceitual: relacionamento "suspende" (BLOQUEIO N:M HORÁRIO DE GRADE).

Linhas no ensaio de 12/10: **34**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `bloqueio_id` | uuid | sim | PK | — | novo.bloqueio_agenda.id |  | operacional | Chave estrangeira; ver a coluna Chave. |
| `horario_grade_id` | uuid | sim | PK | — | grades do mesmo serviço (ou todas) e unidade (ou todas), no dia da semana do bloqueio (permanente: dia_semana ou todos; avulso: dow(data)), com sobreposição de horário e vigência que cubra a data |  | operacional | Chave estrangeira; ver a coluna Chave. |
| `criado_em` | timestamp with time zone | sim |  | — | now() |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `agendamento`

Conceitual: AGENDAMENTO. Origem: bookings.

Linhas no ensaio de 12/10: **536**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | origem.bookings.id | direto |  | tecnico | Chave primária. |
| `aluno_id` | uuid | sim | FK → novo.aluno | origem.bookings.athlete_id | direto (0 fora de athletes) |  | operacional | Aluno a que o registro se refere. |
| `unidade_id` | uuid | sim | FK → novo.unidade | — | novo.unidade_atual_do_aluno(aluno_id) |  | operacional | Unidade (PKZ ou One to One) a que o registro pertence. |
| `servico_id` | uuid | sim | FK → novo.servico | origem.bookings.service | service: treino→treino, fisioterapeuta→fisioterapia, nutricionista→nutricao, psicologo→psicologia; busca novo.servico.id pelo codigo |  | operacional | Serviço a que o registro se refere. |
| `horario_grade_id` | uuid | não | FK → novo.horario_grade | — | grade da unidade ou compartilhada, mesmo serviço, dow(slot_date), start_time dentro da faixa, vigência cobrindo a data (novo.grade_do_horario) |  | operacional | Chave estrangeira; ver a coluna Chave. |
| `profissional_id` | uuid | não | FK → novo.profissional | origem.bookings.professor_id \| origem.specialist_evolutions.professional_id | direto (313/536 nulos na foto); serviço especializado sem professor (69/69 na foto): professional_id da evolução do mesmo agendamento, quando houver (15) |  | operacional | Profissional responsável pelo registro. |
| `data` | date | sim |  | origem.bookings.slot_date | direto |  | operacional | Data a que o registro se refere. |
| `hora_inicio` | time without time zone | sim |  | origem.bookings.start_time | direto |  | operacional | Hora de início. |
| `hora_fim` | time without time zone | não |  | origem.bookings.start_time + origem.athletes.plan / program / training_duration_min | start_time + duração da regra do app (get_service_day): treino One to One com início >= 17:00 → 60 min; treino com plano express → 30 min; treino → athletes.training_duration_min (ou 60); fisioterapia com plano be_the_one → 60 min; fisioterapia → 15 min; nutrição e psicologia → 60 min |  | operacional | Hora de término. |
| `status` | text | sim |  | origem.bookings.status | enum booking_status → texto | agendado \| cancelado \| falta \| presente | operacional | Situação do registro. |
| `criado_por` | uuid | não | FK → novo.perfil_usuario | origem.bookings.created_by | direto; sem perfil → nulo |  | operacional | Usuário que criou o registro na origem. |
| `confirmado_em` | timestamp with time zone | não |  | origem.bookings.confirmed_at | direto |  | operacional | Data e hora do evento que o nome indica. |
| `cancelado_em` | timestamp with time zone | não |  | origem.activity_logs.created_at | status cancelado: created_at do último activity_logs com action = 'cancel_booking' e entity_id = bookings.id |  | operacional | Data e hora do evento que o nome indica. |
| `motivo_cancelamento` | text | não |  | — | nulo: a origem não guarda motivo (o payload de cancel_booking só tem refund) |  | operacional | [revisar] |
| `pendencia` | text | não |  | — |  |  | tecnico | Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga. |
| `criado_em` | timestamp with time zone | sim |  | origem.bookings.created_at | direto |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `sessao_treino`

Conceitual: SESSÃO DE TREINO (realização do agendamento). Origem: bookings com status presente.

Linhas no ensaio de 12/10: **224**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | — | gen_random_uuid() |  | tecnico | Chave primária. |
| `agendamento_id` | uuid | sim | FK → novo.agendamento | origem.bookings.id | só bookings com status 'presente' e service 'treino' (no especializado, a realização é o atendimento, script 70) |  | operacional | Agendamento que originou o registro. |
| `profissional_id` | uuid | não | FK → novo.profissional | origem.bookings.professor_id | direto |  | operacional | Profissional responsável pelo registro. |
| `data` | date | sim |  | origem.bookings.slot_date | direto |  | operacional | Data a que o registro se refere. |
| `hora_inicio` | time without time zone | não |  | origem.bookings.start_time | direto |  | operacional | Hora de início. |
| `hora_fim` | time without time zone | não |  | — | = agendamento.hora_fim |  | operacional | Hora de término. |
| `observacao` | text | não |  | — | nulo |  | operacional | Texto livre escrito por quem registrou. |
| `pendencia` | text | não |  | — |  |  | tecnico | Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga. |
| `criado_em` | timestamp with time zone | sim |  | origem.activity_logs.created_at | created_at do último mark_attendance do agendamento; sem registro (0 na foto) → agendamento.criado_em |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `lista_espera`

Fora do conceitual (proposta). Origem: waitlist (vazia).

Linhas no ensaio de 12/10: **0**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | origem.waitlist.id | direto (0 linhas na foto: só estrutura) |  | tecnico | Chave primária. |
| `aluno_id` | uuid | sim | FK → novo.aluno | origem.waitlist.athlete_id | direto |  | operacional | Aluno a que o registro se refere. |
| `unidade_id` | uuid | sim | FK → novo.unidade | — | novo.unidade_atual_do_aluno(aluno_id) |  | operacional | Unidade (PKZ ou One to One) a que o registro pertence. |
| `servico_id` | uuid | sim | FK → novo.servico | origem.waitlist.service | service: treino→treino, fisioterapeuta→fisioterapia, nutricionista→nutricao, psicologo→psicologia; busca novo.servico.id pelo codigo |  | operacional | Serviço a que o registro se refere. |
| `data` | date | sim |  | origem.waitlist.slot_date | direto |  | operacional | Data a que o registro se refere. |
| `hora_inicio` | time without time zone | sim |  | origem.waitlist.start_time | direto |  | operacional | Hora de início. |
| `solicitante_id` | uuid | não | FK → novo.perfil_usuario | origem.waitlist.responsavel_id | direto |  | operacional | Chave estrangeira; ver a coluna Chave. |
| `status` | text | sim |  | origem.waitlist.status | direto |  | operacional | Situação do registro. |
| `notificado_em` | timestamp with time zone | não |  | origem.waitlist.notified_at | direto |  | operacional | Data e hora do evento que o nome indica. |
| `expira_em` | timestamp with time zone | não |  | origem.waitlist.expires_at | direto |  | operacional | Data e hora do evento que o nome indica. |
| `pendencia` | text | não |  | — |  |  | tecnico | Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga. |
| `criado_em` | timestamp with time zone | sim |  | origem.waitlist.created_at | direto |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `feedback_treino`

Conceitual: FEEDBACK (legado). Origem: training_feedback. O aluno vem do agendamento.

Linhas no ensaio de 12/10: **169**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | origem.training_feedback.id | direto |  | tecnico | Chave primária. |
| `agendamento_id` | uuid | sim | FK → novo.agendamento | origem.training_feedback.booking_id | direto (1 por agendamento na foto) |  | operacional | Agendamento que originou o registro. |
| `nota_treino` | smallint | não |  | origem.training_feedback.rating_treino | direto (3 a 5 na foto) |  | operacional | [revisar] |
| `nota_professor` | smallint | não |  | origem.training_feedback.rating_professor | direto |  | operacional | [revisar] |
| `gostou` | text[] | sim |  | origem.training_feedback.liked | direto (array de texto) |  | operacional | [revisar] |
| `comentario` | text | não |  | origem.training_feedback.comentario | direto |  | operacional | [revisar] |
| `pulado` | boolean | sim |  | origem.training_feedback.skipped | direto |  | operacional | [revisar] |
| `criado_por` | uuid | não | FK → novo.perfil_usuario | origem.training_feedback.created_by | direto; sem perfil → nulo |  | operacional | Usuário que criou o registro na origem. |
| `pendencia` | text | não |  | — |  |  | tecnico | Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga. |
| `criado_em` | timestamp with time zone | sim |  | origem.training_feedback.created_at | direto |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `catalogo_item`

Conceitual: ITEM DE CATÁLOGO. Origem: training_report_materials, training_report_technologies e valores distintos dos arrays de training_reports.

Linhas no ensaio de 12/10: **72**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | — | gen_random_uuid() |  | tecnico | Chave primária. |
| `dominio` | text | sim |  | origem.training_report_materials \| origem.training_report_technologies \| arrays de origem.training_reports | materials → material; technologies → tecnologia; capacidades_fisicas/tecnicas/cognitivas → capacidade_*; objetivo_sessao, foco, conduta → o próprio nome | capacidade_cognitiva \| capacidade_fisica \| capacidade_tecnica \| conduta \| foco \| material \| objetivo_sessao \| tecnologia | operacional | [revisar] |
| `codigo` | text | sim |  | origem.training_report_materials.name \| origem.training_report_technologies.name \| valores distintos dos arrays | slug: lower, sem acento, espaços → '_' (ex.: 'Coordenação motora' → 'coordenacao_motora'); textos de materials_other/technologies_other: 'outro_' \|\| slug. ATENÇÃO: material e tecnologia vêm SÓ das tabelas de catálogo (os arrays apontam para elas, 100% casados na foto); os arrays só criam itens nos 6 domínios sem tabela (capacidade_fisica, capacidade_tecnica, capacidade_cognitiva, objetivo_sessao, foco, conduta). Valor de materials/technologies sem item no catálogo: item novo com pendência (0 na foto). Gere uma linha por (dominio, codigo) antes do insert, senão o on conflict falha | acquabag \| agilidade \| argolas \| atencao \| bands \| barreiras \| bastao_estabilidade \| blazepod \| bola_suica \| bosu \| camera_para_analise \| cinto_tracao \| colchao_de_instabilidade | operacional | Código curto e estável, usado nas regras e nos scripts. |
| `nome` | text | sim |  | idem | o texto original |  | pessoal | Nome de exibição. |
| `ativo` | boolean | sim |  | origem.training_report_materials.active \| origem.training_report_technologies.active | direto; valores dos arrays: true |  | operacional | Se o registro está ativo. |
| `ordem` | integer | sim |  | origem.training_report_materials.sort_order \| origem.training_report_technologies.sort_order | direto; valores dos arrays: ordem alfabética |  | operacional | Ordem de exibição na tela. |
| `id_origem` | uuid | não |  | origem.training_report_materials.id \| origem.training_report_technologies.id | direto; valores dos arrays: nulo |  | tecnico | Id da linha na origem, usado para reexecutar a carga sem duplicar. |
| `pendencia` | text | não |  | origem.training_reports.materials_other \| origem.training_reports.technologies_other |  |  | tecnico | Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga. |
| `criado_em` | timestamp with time zone | sim |  | origem.training_report_materials.created_at \| origem.training_report_technologies.created_at | direto; valores dos arrays: now() |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `relatorio_treino`

Conceitual: RELATÓRIO. Origem: training_reports.

Linhas no ensaio de 12/10: **228**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | origem.training_reports.id | direto |  | tecnico | Chave primária. |
| `aluno_id` | uuid | sim | FK → novo.aluno | origem.training_reports.athlete_id | direto |  | operacional | Aluno a que o registro se refere. |
| `agendamento_id` | uuid | não | FK → novo.agendamento | origem.training_reports.booking_id | direto (18 nulos na foto); agendamento de outro aluno → nulo |  | operacional | Agendamento que originou o registro. |
| `profissional_id` | uuid | não | FK → novo.profissional | origem.training_reports.professor_id | direto |  | operacional | Profissional responsável pelo registro. |
| `unidade_id` | uuid | sim | FK → novo.unidade | — | novo.unidade_atual_do_aluno(aluno_id) |  | operacional | Unidade (PKZ ou One to One) a que o registro pertence. |
| `tipo` | text | sim |  | origem.training_reports.report_kind | direto (pkz, one_to_one) | one_to_one \| pkz | operacional | [revisar] |
| `status` | text | sim |  | origem.training_reports.status | direto (rascunho, final) | final \| rascunho | operacional | Situação do registro. |
| `data` | date | sim |  | origem.training_reports.report_date | direto |  | operacional | Data a que o registro se refere. |
| `hora_inicio` | time without time zone | não |  | origem.training_reports.start_time | direto |  | operacional | Hora de início. |
| `hora_fim` | time without time zone | não |  | origem.training_reports.end_time | direto; fim <= início → nulo |  | operacional | Hora de término. |
| `titulo` | text | não |  | origem.training_reports.title | direto |  | operacional | [revisar] |
| `categoria` | text | não |  | origem.training_reports.category | direto |  | operacional | [revisar] |
| `grupo` | text | não |  | origem.training_reports.athlete_group | direto |  | operacional | [revisar] |
| `local` | text | não |  | origem.training_reports.local | direto |  | operacional | [revisar] |
| `tipo_treino` | text | não |  | origem.training_reports.training_type | direto (vazio em toda a foto) |  | operacional | [revisar] |
| `numero_sessao` | integer | não |  | origem.training_reports.session_number | direto |  | operacional | [revisar] |
| `intensidade` | text | não |  | origem.training_reports.intensidade | direto | Alta \| Leve \| Moderada | operacional | [revisar] |
| `blocos` | smallint | não |  | origem.training_reports.blocos | direto |  | operacional | [revisar] |
| `objetivos` | text | não |  | origem.training_reports.objetivos | direto |  | operacional | [revisar] |
| `analise_html` | text | não |  | origem.training_reports.analise_html | direto |  | operacional | [revisar] |
| `observacoes` | text | não |  | origem.training_reports.observacoes | direto |  | operacional | Texto livre escrito por quem registrou. |
| `evolucao` | text | não |  | origem.training_reports.evolucao | direto |  | operacional | [revisar] |
| `desempenho` | text | não |  | origem.training_reports.desempenho | direto |  | operacional | [revisar] |
| `notas` | text | não |  | origem.training_reports.notes | direto |  | operacional | [revisar] |
| `dor` | text | não |  | origem.training_reports.dor | direto |  | clinico | [revisar] |
| `dor_local` | text | não |  | origem.training_reports.dor_local | direto |  | clinico | [revisar] |
| `dor_intensidade` | smallint | não |  | origem.training_reports.dor_intensidade | direto (3 a 8 na foto) |  | clinico | [revisar] |
| `dor_movimento` | text | não |  | origem.training_reports.dor_movimento | direto |  | clinico | [revisar] |
| `criado_por` | uuid | não | FK → novo.perfil_usuario | origem.training_reports.created_by | direto; sem perfil → nulo |  | operacional | Usuário que criou o registro na origem. |
| `pendencia` | text | não |  | — |  |  | tecnico | Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga. |
| `criado_em` | timestamp with time zone | sim |  | origem.training_reports.created_at | direto |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `relatorio_item`

Conceitual: relacionamento "classificado por".

Linhas no ensaio de 12/10: **912**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `relatorio_id` | uuid | sim | PK | origem.training_reports.id | direto |  | operacional | Relatório a que o registro pertence. |
| `catalogo_item_id` | uuid | sim | PK | origem.training_reports.materials \| technologies \| capacidades_fisicas \| capacidades_tecnicas \| capacidades_cognitivas \| objetivo_sessao \| foco \| conduta \| materials_other \| technologies_other | unnest de cada array → item pelo (dominio, nome); materials_other/technologies_other → item 'outro_' do texto |  | operacional | Item de catálogo que classifica o registro. |
| `texto_original` | text | não |  | idem | valor como estava |  | operacional | [revisar] |
| `criado_em` | timestamp with time zone | sim |  | origem.training_reports.created_at | direto |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |
