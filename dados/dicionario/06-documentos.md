# Documentos, conformidade e comunicação

> Dicionário de dados do schema `novo` · migration 008 · gerado por `dicionario/gerar_dicionario.py`.

Sensibilidade: `clinico` (dado de saúde), `pessoal` (identifica alguém), `operacional` (rotina do negócio), `tecnico` (controle da carga).

## `arquivo`

Conceitual: ARQUIVO (relacionamentos "anexado a"). Origem: 9 colunas de caminho (student_files, nutritionist_files, physio_evolutions, specialist_evolutions, training_reports x2, physical_test_comparisons, physio_assessments, student_tests).

Linhas no ensaio de 12/10: **523**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | — | gen_random_uuid() |  | tecnico | Chave primária. |
| `storage_path` | text | sim |  | origem.student_files.storage_path \| origem.nutritionist_files.storage_path \| origem.physio_evolutions.storage_path \| origem.specialist_evolutions.file_path \| origem.training_reports.file_path \| origem.training_reports.pdf_storage_path \| origem.physical_test_comparisons.file_path \| origem.physio_assessments.file_path \| origem.physio_assessments.pkz_data (img_*, carimbo_path, laudo_path) \| origem.student_tests.file_path | um arquivo por caminho distinto não vazio (523 na foto); training_reports.file_path e pdf_storage_path são o mesmo caminho em 205/205 |  | operacional | [revisar] |
| `nome` | text | não |  | origem.student_files.file_name \| origem.nutritionist_files.file_name \| origem.physio_evolutions.file_name \| origem.specialist_evolutions.file_name | file_name quando existe; senão o último trecho do caminho |  | pessoal | Nome de exibição. |
| `mime` | text | não |  | origem.student_files.mime_type \| origem.nutritionist_files.mime_type | direto; sem mime: pela extensão (.pdf → application/pdf, .png → image/png, .jpg/.jpeg → image/jpeg) | application/pdf \| image/jpeg \| image/png | operacional | [revisar] |
| `bytes` | bigint | não |  | origem.student_files.size_bytes \| origem.nutritionist_files.size_bytes | direto; demais: nulo |  | operacional | [revisar] |
| `tipo` | text | não |  | origem.student_files.folder + origem de cada caminho | student_files: 02_Relatorios_de_Treino → relatorio_treino, 03_Evolucao_e_Comparativos → evolucao_comparativo, 04_Extrato_Geral_de_Relatorios → extrato, 05_Fisioterapia → fisioterapia; nutritionist_files → nutricao; physio/specialist_evolutions → evolucao; training_reports → relatorio_treino; physical_test_comparisons → comparativo_teste_fisico; physio_assessments.file_path → avaliacao_fisioterapia; img_anterior/img_lateral_*/img_posterior → imagem_postural; img_mob_* → imagem_mobilidade; carimbo_path → carimbo_profissional; laudo_path → laudo | avaliacao_fisioterapia \| carimbo_profissional \| comparativo_teste_fisico \| evolucao \| evolucao_comparativo \| extrato \| fisioterapia \| imagem_mobilidade \| imagem_postural \| relatorio_treino | operacional | [revisar] |
| `confidencialidade` | text | sim |  | origem de cada caminho | clinico: nutritionist_files, physio_evolutions, specialist_evolutions, physio_assessments (file_path e pkz_data), student_files da pasta 05_Fisioterapia; normal: o resto. Caminho com origem clínica e normal → clinico | clinico \| normal | clinico | Nível de sigilo: define quem pode ler (política 012). |
| `aluno_id` | uuid | não | FK → novo.aluno | origem.student_files.athlete_id \| origem.nutritionist_files.athlete_id \| origem.physio_evolutions.athlete_id \| origem.specialist_evolutions.athlete_id \| origem.training_reports.athlete_id \| origem.physical_test_comparisons.athlete_id \| origem.physio_assessments.athlete_id \| origem.student_tests.athlete_id | athlete_id de cada origem |  | operacional | Aluno a que o registro se refere. |
| `unidade_id` | uuid | não | FK → novo.unidade | — | novo.unidade_atual_do_aluno(aluno_id) |  | operacional | Unidade (PKZ ou One to One) a que o registro pertence. |
| `relatorio_id` | uuid | não | FK → novo.relatorio_treino | origem.training_reports.id | caminhos vindos de training_reports |  | operacional | Relatório a que o registro pertence. |
| `avaliacao_id` | uuid | não | FK → novo.avaliacao | origem.physio_assessments.id | caminhos vindos de physio_assessments (file_path, img_*, carimbo_path, laudo_path) |  | operacional | Avaliação a que o registro pertence. |
| `atendimento_id` | uuid | não | FK → novo.atendimento | origem.physio_evolutions.id \| origem.specialist_evolutions.id | caminhos vindos das evoluções |  | operacional | Atendimento a que o registro pertence. |
| `enviado_por` | uuid | não | FK → novo.perfil_usuario | origem.student_files.uploaded_by \| origem.nutritionist_files.uploaded_by \| origem.physio_evolutions.physio_id \| origem.specialist_evolutions.professional_id \| origem.training_reports.created_by \| origem.physical_test_comparisons.created_by \| origem.physio_assessments.created_by | direto; sem perfil → nulo |  | operacional | [revisar] |
| `pendencia` | text | não |  | origem.physical_test_comparisons.session_a_id \| session_b_id |  |  | tecnico | Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga. |
| `criado_em` | timestamp with time zone | sim |  | origem.student_files.created_at \| origem.nutritionist_files.created_at \| origem.physio_evolutions.created_at \| origem.specialist_evolutions.created_at \| origem.training_reports.created_at \| origem.physical_test_comparisons.created_at \| origem.physio_assessments.created_at | o menor created_at entre as origens do caminho |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `consentimento`

Conceitual: CONSENTIMENTO (LGPD). Não existe na origem: só estrutura.

Linhas no ensaio de 12/10: **0**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | — | sem origem: só estrutura |  | tecnico | Chave primária. |
| `pessoa_id` | uuid | sim | FK → novo.pessoa | — | sem origem: só estrutura |  | operacional | Pessoa a que o registro se refere. |
| `aluno_id` | uuid | sim | FK → novo.aluno | — | sem origem: só estrutura |  | operacional | Aluno a que o registro se refere. |
| `finalidade` | text | sim |  | — | sem origem: só estrutura |  | operacional | [revisar] |
| `canal` | text | não |  | — | sem origem: só estrutura |  | operacional | [revisar] |
| `versao_termo` | text | não |  | — | sem origem: só estrutura |  | operacional | [revisar] |
| `concedido_em` | timestamp with time zone | sim |  | — | sem origem: só estrutura |  | operacional | Data e hora do evento que o nome indica. |
| `revogado_em` | timestamp with time zone | não |  | — | sem origem: só estrutura |  | operacional | Data e hora do evento que o nome indica. |
| `criado_em` | timestamp with time zone | sim |  | — | sem origem: só estrutura |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | sem origem: só estrutura |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `relatorio_emissao`

Conceitual: EMISSÃO DE RELATÓRIO. Não existe na origem: só estrutura.

Linhas no ensaio de 12/10: **0**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | — | sem origem: só estrutura |  | tecnico | Chave primária. |
| `aluno_id` | uuid | sim | FK → novo.aluno | — | sem origem: só estrutura |  | operacional | Aluno a que o registro se refere. |
| `tipo` | text | sim |  | — | sem origem: só estrutura |  | operacional | [revisar] |
| `competencia` | date | sim |  | — | sem origem: só estrutura |  | operacional | [revisar] |
| `gerado_em` | timestamp with time zone | sim |  | — | sem origem: só estrutura |  | operacional | Data e hora do evento que o nome indica. |
| `gerado_por` | uuid | não | FK → novo.perfil_usuario | — | sem origem: só estrutura |  | operacional | [revisar] |
| `arquivo_id` | uuid | não | FK → novo.arquivo | — | sem origem: só estrutura |  | operacional | Arquivo ligado ao registro. |
| `criado_em` | timestamp with time zone | sim |  | — | sem origem: só estrutura |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | sem origem: só estrutura |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `relatorio_envio`

Conceitual: ENVIO (entidade fraca de EMISSÃO). Só estrutura.

Linhas no ensaio de 12/10: **0**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `emissao_id` | uuid | sim | PK | — | sem origem: só estrutura |  | operacional | Emissão de relatório a que o envio pertence. |
| `canal` | text | sim | PK | — | sem origem: só estrutura |  | operacional | [revisar] |
| `destinatario_id` | uuid | sim | PK | — | sem origem: só estrutura |  | operacional | Chave estrangeira; ver a coluna Chave. |
| `estado` | text | sim |  | — | sem origem: só estrutura |  | operacional | [revisar] |
| `erro` | text | não |  | — | sem origem: só estrutura |  | operacional | [revisar] |
| `enviado_em` | timestamp with time zone | não |  | — | sem origem: só estrutura |  | operacional | Data e hora do evento que o nome indica. |
| `criado_em` | timestamp with time zone | sim |  | — | sem origem: só estrutura |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | sem origem: só estrutura |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `notificacao`

Conceitual: NOTIFICAÇÃO. Origem: notifications NÃO migra (pendência 6).

Linhas no ensaio de 12/10: **0**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | — | sem origem: só estrutura |  | tecnico | Chave primária. |
| `usuario_id` | uuid | sim | FK → novo.perfil_usuario | — | sem origem: só estrutura |  | operacional | Usuário de login dono do registro. |
| `tipo` | text | sim |  | — | sem origem: só estrutura |  | operacional | [revisar] |
| `mensagem` | text | sim |  | — | sem origem: só estrutura |  | operacional | [revisar] |
| `lida` | boolean | sim |  | — | sem origem: só estrutura |  | operacional | [revisar] |
| `criado_em` | timestamp with time zone | sim |  | — | sem origem: só estrutura |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | sem origem: só estrutura |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `evento_auditoria`

Conceitual: AUDITORIA. Origem: activity_logs, booking_audit_logs.

Linhas no ensaio de 12/10: **1389**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | — | gen_random_uuid() |  | tecnico | Chave primária. |
| `ator_id` | uuid | não | FK → novo.perfil_usuario | origem.activity_logs.actor_id \| origem.booking_audit_logs.actor_id \| origem.booking_audit_logs.created_by | activity_logs: actor_id; booking_audit_logs: coalesce(actor_id, created_by); sem perfil no destino (ex.: usuário apagado) → nulo |  | operacional | Chave estrangeira; ver a coluna Chave. |
| `acao` | text | sim |  | origem.activity_logs.action \| origem.booking_audit_logs.action | direto; 'Link de ativação enviado via WhatsApp' → 'send_activation_link'; professor_assigned, assign_professor e assign_booking_professor → 'assign_professor' | adjust_credits \| admin_create_user \| admin_delete_user \| admin_reset_password \| admin_update_profile \| assign_professor \| book_service \| book_trial_class \| cancel_booking \| confirm_booking \| daily_renewal \| mark_attendance \| monthly_renewal | operacional | [revisar] |
| `acao_original` | text | não |  | idem | o texto original, só quando a ação foi padronizada | assign_booking_professor \| Link de ativação enviado via WhatsApp \| professor_assigned | operacional | [revisar] |
| `entidade` | text | não |  | origem.activity_logs.entity | athlete → aluno; booking → agendamento; user → usuario; system → sistema; nulo → nulo; booking_audit_logs → agendamento | agendamento \| aluno \| sistema \| usuario | operacional | [revisar] |
| `entidade_id` | uuid | não |  | origem.activity_logs.entity_id \| origem.booking_audit_logs.booking_id | direto (sem FK: pode apontar para registro apagado) |  | operacional | Chave estrangeira; ver a coluna Chave. |
| `valor_anterior` | jsonb | não |  | origem.booking_audit_logs.previous_professor_id \| old_value | activity_logs: nulo; booking_audit_logs: jsonb_strip_nulls(jsonb_build_object('professor_id', previous_professor_id, 'valor', old_value)) |  | operacional | [revisar] |
| `valor_novo` | jsonb | não |  | origem.activity_logs.payload \| origem.booking_audit_logs.new_professor_id \| new_value \| reason | activity_logs: payload SEM as chaves athlete_name, phone, full_name e username; booking_audit_logs: jsonb_strip_nulls(jsonb_build_object('professor_id', new_professor_id, 'valor', new_value, 'motivo', reason)) |  | operacional | [revisar] |
| `unidade_id` | uuid | não | FK → novo.unidade | — | entidade aluno: unidade atual do aluno (entity_id); entidade agendamento: novo.agendamento.unidade_id (pelo entity_id / booking_id); demais: nulo |  | operacional | Unidade (PKZ ou One to One) a que o registro pertence. |
| `ip` | inet | não |  | — | nulo (a origem não guarda) |  | operacional | [revisar] |
| `tabela_origem` | text | não |  | — | 'activity_logs' ou 'booking_audit_logs' |  | tecnico | Tabela da origem que gerou a linha. |
| `id_origem` | uuid | não |  | origem.activity_logs.id \| origem.booking_audit_logs.id | direto |  | tecnico | Id da linha na origem, usado para reexecutar a carga sem duplicar. |
| `pendencia` | text | não |  | — |  |  | tecnico | Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga. |
| `criado_em` | timestamp with time zone | sim |  | origem.activity_logs.created_at \| origem.booking_audit_logs.created_at | direto; booking_audit_logs com created_at nulo → bookings.created_at |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `acesso_dado_sensivel`

Fora do conceitual (proposta): registro de leitura de dado clínico. Só estrutura.

Linhas no ensaio de 12/10: **0**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | — | sem origem: só estrutura |  | tecnico | Chave primária. |
| `usuario_id` | uuid | sim | FK → novo.perfil_usuario | — | sem origem: só estrutura |  | operacional | Usuário de login dono do registro. |
| `aluno_id` | uuid | não | FK → novo.aluno | — | sem origem: só estrutura |  | operacional | Aluno a que o registro se refere. |
| `entidade` | text | sim |  | — | sem origem: só estrutura |  | operacional | [revisar] |
| `entidade_id` | uuid | não |  | — | sem origem: só estrutura |  | operacional | Chave estrangeira; ver a coluna Chave. |
| `finalidade` | text | não |  | — | sem origem: só estrutura |  | operacional | [revisar] |
| `acessado_em` | timestamp with time zone | sim |  | — | sem origem: só estrutura |  | operacional | Data e hora do evento que o nome indica. |
| `criado_em` | timestamp with time zone | sim |  | — | sem origem: só estrutura |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | sem origem: só estrutura |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |
