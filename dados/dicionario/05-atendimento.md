# Atendimento especializado

> Dicionário de dados do schema `novo` · migration 007 · gerado por `dicionario/gerar_dicionario.py`.

Sensibilidade: `clinico` (dado de saúde), `pessoal` (identifica alguém), `operacional` (rotina do negócio), `tecnico` (controle da carga).

## `atendimento`

Conceitual: ATENDIMENTO (especializações FISIOTERAPIA, NUTRIÇÃO, PSICOLOGIA em servico_id). Origem: physio_evolutions, specialist_evolutions.

Linhas no ensaio de 12/10: **22**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | origem.physio_evolutions.id \| origem.specialist_evolutions.id | direto |  | clinico | Chave primária. |
| `aluno_id` | uuid | sim | FK → novo.aluno | origem.physio_evolutions.athlete_id \| origem.specialist_evolutions.athlete_id | direto |  | clinico | Aluno a que o registro se refere. |
| `profissional_id` | uuid | sim | FK → novo.profissional | origem.physio_evolutions.physio_id \| origem.specialist_evolutions.professional_id | direto |  | clinico | Profissional responsável pelo registro. |
| `servico_id` | uuid | sim | FK → novo.servico | origem.specialist_evolutions.service | physio_evolutions: fisioterapia; specialist_evolutions: service: treino→treino, fisioterapeuta→fisioterapia, nutricionista→nutricao, psicologo→psicologia; busca novo.servico.id pelo codigo |  | clinico | Serviço a que o registro se refere. |
| `agendamento_id` | uuid | não | FK → novo.agendamento | origem.specialist_evolutions.booking_id | direto; physio_evolutions: nulo; agendamento de outro aluno → nulo |  | clinico | Agendamento que originou o registro. |
| `unidade_id` | uuid | não | FK → novo.unidade | — | novo.unidade_atual_do_aluno(aluno_id) |  | clinico | Unidade (PKZ ou One to One) a que o registro pertence. |
| `data` | date | sim |  | origem.bookings.slot_date \| origem.physio_evolutions.created_at | specialist: slot_date do agendamento; physio_evolutions: (created_at at time zone 'America/Sao_Paulo')::date |  | clinico | Data a que o registro se refere. |
| `observacao` | text | não |  | — | nulo (o conteúdo está no arquivo, script 80) |  | clinico | Texto livre escrito por quem registrou. |
| `pendencia` | text | não |  | — |  |  | clinico | Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga. |
| `criado_em` | timestamp with time zone | sim |  | origem.physio_evolutions.created_at \| origem.specialist_evolutions.created_at | direto |  | clinico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | clinico | Última atualização; o `on conflict do update` grava `now()`. |

## `evolucao`

Conceitual: EVOLUÇÃO (entidade fraca de ATENDIMENTO, chave parcial = data).

Linhas no ensaio de 12/10: **22**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | — | gen_random_uuid() |  | clinico | Chave primária. |
| `atendimento_id` | uuid | sim | FK → novo.atendimento | origem.physio_evolutions.id \| origem.specialist_evolutions.id | uma evolução por atendimento |  | clinico | Atendimento a que o registro pertence. |
| `data` | date | sim |  | — | = atendimento.data |  | clinico | Data a que o registro se refere. |
| `observacao` | text | não |  | — | nulo (o file_name não é copiado para cá: pode conter nome do aluno) |  | clinico | Texto livre escrito por quem registrou. |
| `pendencia` | text | não |  | — |  |  | clinico | Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga. |
| `criado_em` | timestamp with time zone | sim |  | origem.physio_evolutions.created_at \| origem.specialist_evolutions.created_at | direto |  | clinico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | clinico | Última atualização; o `on conflict do update` grava `now()`. |

## `anamnese`

Conceitual: ANAMNESE (histórico clínico do atleta). Origem: physio_assessments (campos clínicos) e pkz_data. Confidencialidade máxima.

Linhas no ensaio de 12/10: **4**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | origem.physio_assessments.id | direto |  | clinico | Chave primária. |
| `aluno_id` | uuid | sim | FK → novo.aluno | origem.physio_assessments.athlete_id | direto |  | clinico | Aluno a que o registro se refere. |
| `avaliacao_id` | uuid | não | FK → novo.avaliacao | origem.physio_assessments.id | = avaliacao.id |  | clinico | Avaliação a que o registro pertence. |
| `profissional_id` | uuid | não | FK → novo.profissional | origem.physio_assessments.physio_id | direto |  | clinico | Profissional responsável pelo registro. |
| `data` | date | sim |  | origem.physio_assessments.assessment_date | direto |  | clinico | Data a que o registro se refere. |
| `queixa_principal` | text | não |  | origem.physio_assessments.queixa_principal | direto; vazio → nulo |  | clinico | [revisar] |
| `hda` | text | não |  | origem.physio_assessments.hda | direto; vazio → nulo |  | clinico | [revisar] |
| `hpp_doencas` | text | não |  | origem.physio_assessments.hpp_doencas | direto; vazio → nulo |  | clinico | [revisar] |
| `hpp_cirurgias` | text | não |  | origem.physio_assessments.hpp_cirurgias | direto; vazio → nulo |  | clinico | [revisar] |
| `hpp_fraturas` | text | não |  | origem.physio_assessments.hpp_fraturas | direto; vazio → nulo |  | clinico | [revisar] |
| `hpp_entorses` | text | não |  | origem.physio_assessments.hpp_entorses | direto; vazio → nulo |  | clinico | [revisar] |
| `hab_freq_treinos` | text | não |  | origem.physio_assessments.hab_freq_treinos | direto; vazio → nulo |  | clinico | [revisar] |
| `hab_outras_atividades` | text | não |  | origem.physio_assessments.hab_outras_atividades | direto; vazio → nulo |  | clinico | [revisar] |
| `hab_alcool` | text | não |  | origem.physio_assessments.hab_alcool | direto; vazio → nulo |  | clinico | [revisar] |
| `hab_tabagista` | text | não |  | origem.physio_assessments.hab_tabagista | direto; vazio → nulo |  | clinico | [revisar] |
| `hab_medicamentos` | text | não |  | origem.physio_assessments.hab_medicamentos | direto; vazio → nulo |  | clinico | [revisar] |
| `fam_materna` | text | não |  | origem.physio_assessments.fam_materna | direto; vazio → nulo |  | clinico | [revisar] |
| `fam_paterna` | text | não |  | origem.physio_assessments.fam_paterna | direto; vazio → nulo |  | clinico | [revisar] |
| `diagnostico_clinico` | text | não |  | origem.physio_assessments.diagnostico_clinico | direto; vazio → nulo |  | clinico | [revisar] |
| `diagnostico_funcional` | text | não |  | origem.physio_assessments.diagnostico_funcional | direto; vazio → nulo |  | clinico | [revisar] |
| `exames_complementares` | text | não |  | origem.physio_assessments.exames_complementares | direto; vazio → nulo |  | clinico | [revisar] |
| `observacao` | text | não |  | origem.physio_assessments.observacao | direto; vazio → nulo |  | clinico | Texto livre escrito por quem registrou. |
| `dados_complementares` | jsonb | não |  | origem.physio_assessments.pkz_data | jsonb só com as chaves de texto clínico: rotina_acorda, rotina_escola, rotina_alimentacao, rotina_atividades, rotina_semana, rotina_dormir, rotina_fds, qualidade_sono, entorses_lado, cirurgias_sim, cirurgias_quais, fraturas_sim, fraturas_quais, laudo_apresentado, hpp_d_* e hpp_outros_desc; chaves vazias saem; pkz_data '{}' → nulo |  | clinico | [revisar] |
| `confidencialidade` | text | sim |  | — | 'restrito' | restrito | clinico | Nível de sigilo: define quem pode ler (política 012). |
| `pendencia` | text | não |  | — |  |  | clinico | Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga. |
| `criado_em` | timestamp with time zone | sim |  | origem.physio_assessments.created_at | direto |  | clinico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | clinico | Última atualização; o `on conflict do update` grava `now()`. |
