# Comercial e créditos

> Dicionário de dados do schema `novo` · migration 003 · gerado por `dicionario/gerar_dicionario.py`.

Sensibilidade: `clinico` (dado de saúde), `pessoal` (identifica alguém), `operacional` (rotina do negócio), `tecnico` (controle da carga).

## `plano`

Conceitual: PLANO. Origem: enum one_to_one_plan + plano padrão do PKZ (pendência).

Linhas no ensaio de 12/10: **7**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | — | gen_random_uuid() |  | tecnico | Chave primária. |
| `unidade_id` | uuid | sim | FK → novo.unidade | — | one_to_one para os planos do enum e para one_to_one_sem_plano; pkz para pkz_padrao |  | operacional | Unidade (PKZ ou One to One) a que o registro pertence. |
| `codigo` | text | sim |  | enum one_to_one_plan | os 5 valores do enum (express, one_move, one_power, one_power_legacy, be_the_one) + 'pkz_padrao' + 'one_to_one_sem_plano' (7 linhas) | be_the_one \| express \| one_move \| one_power \| one_power_legacy \| one_to_one_sem_plano \| pkz_padrao | operacional | Código curto e estável, usado nas regras e nos scripts. |
| `nome` | text | sim |  | — | constante: Express, One Move, One Power, One Power (legado), Be The One, PKZ padrão, One to One sem plano |  | operacional | Nome de exibição. |
| `ativo` | boolean | sim |  | — | true; false para one_power_legacy e one_to_one_sem_plano |  | operacional | Se o registro está ativo. |
| `pendencia` | text | não |  | — |  |  | tecnico | Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga. |
| `criado_em` | timestamp with time zone | sim |  | — | now() |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `plano_beneficio`

Conceitual: relacionamento "concede". Origem: funções plan_weekly_treino, plan_monthly_fisio, plan_monthly_nutri.

Linhas no ensaio de 12/10: **13**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | — | gen_random_uuid() |  | tecnico | Chave primária. |
| `plano_id` | uuid | sim | FK → novo.plano | — | busca novo.plano pelo codigo |  | operacional | Plano contratado. |
| `servico_id` | uuid | sim | FK → novo.servico | public.plan_weekly_treino / plan_monthly_fisio / plan_monthly_nutri (definição, pg_get_functiondef) | treino ← plan_weekly_treino; fisioterapia ← plan_monthly_fisio; nutricao ← plan_monthly_nutri; pkz_padrao: treino |  | operacional | Serviço a que o registro se refere. |
| `quantidade` | integer | sim |  | idem; pkz_padrao: origem.app_settings.monthly_credits | valor do CASE da função para cada plano; só entram as quantidades > 0 (12 linhas dos planos One to One + 1 do PKZ) |  | operacional | [revisar] |
| `periodicidade` | text | sim |  | — | treino: 'semana'; fisioterapia e nutricao: 'mes'; pkz_padrao: 'mes' | mes \| semana | operacional | [revisar] |
| `pendencia` | text | não |  | — |  |  | tecnico | Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga. |
| `criado_em` | timestamp with time zone | sim |  | — | now() |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `matricula`

Conceitual: relacionamento ternário "matrícula" (ATLETA × PLANO × UNIDADE). Origem: athletes (só a vigente; histórico foi apagado na origem).

Linhas no ensaio de 12/10: **106**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | — | gen_random_uuid() |  | tecnico | Chave primária. |
| `aluno_id` | uuid | sim | FK → novo.aluno | origem.athletes.id | direto (uma matrícula por aluno: só a vigente existe na origem) |  | operacional | Aluno a que o registro se refere. |
| `plano_id` | uuid | sim | FK → novo.plano | origem.athletes.plan \| origem.athletes.program | one_to_one: plan → novo.plano.codigo; one_to_one com plan nulo → 'one_to_one_sem_plano'; pkz → 'pkz_padrao' |  | operacional | Plano contratado. |
| `unidade_id` | uuid | sim | FK → novo.unidade | origem.athletes.program | program: pkz→pkz, one_to_one→one_to_one; busca novo.unidade.id pelo codigo |  | operacional | Unidade (PKZ ou One to One) a que o registro pertence. |
| `vigencia_inicio` | date | sim |  | origem.athletes.created_at | (created_at at time zone 'America/Sao_Paulo')::date |  | operacional | [revisar] |
| `vigencia_fim` | date | não |  | — | nulo (vigente) |  | operacional | [revisar] |
| `duracao_treino_min` | integer | não |  | origem.athletes.training_duration_min | direto |  | operacional | [revisar] |
| `experimental` | boolean | sim |  | origem.athletes.is_trial | direto |  | operacional | [revisar] |
| `renovacao_ativa` | boolean | sim |  | origem.athletes.auto_renew_enabled | direto |  | operacional | [revisar] |
| `renovacao_dia` | integer | não |  | origem.athletes.auto_renew_day | direto |  | operacional | [revisar] |
| `renovacao_quantidade` | integer | não |  | origem.athletes.auto_renew_amount | direto |  | operacional | [revisar] |
| `ultima_renovacao_em` | timestamp with time zone | não |  | origem.athletes.last_renewed_at | direto |  | operacional | Data e hora do evento que o nome indica. |
| `proxima_renovacao` | date | não |  | origem.athletes.next_renewal_date | direto |  | operacional | [revisar] |
| `proxima_renovacao_semanal` | date | não |  | origem.athletes.next_weekly_renewal | direto |  | operacional | [revisar] |
| `plano_mensal_origem` | integer | não |  | origem.athletes.monthly_plan | direto (valor bruto) |  | operacional | [revisar] |
| `pendencia` | text | não |  | origem.athletes.credits \| credits_fisio \| credits_nutri | compara o saldo guardado no aluno com novo.vw_saldo_credito por serviço (treino, fisioterapia, nutricao). Créditos NÃO são cumulativos: a renovação redefine o saldo (delta = cota), então o saldo é a soma dos lançamentos desde a última renovação, inclusive (migration 011). Antes de marcar, tira as marcas de execuções anteriores (update) |  | tecnico | Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga. |
| `criado_em` | timestamp with time zone | sim |  | origem.athletes.created_at | direto |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `renovacao`

Conceitual: RENOVAÇÃO. Origem: lançamentos de credit_transactions cujo motivo começa com "Renovação".

Linhas no ensaio de 12/10: **968**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | — | gen_random_uuid() |  | tecnico | Chave primária. |
| `aluno_id` | uuid | sim | FK → novo.aluno | origem.credit_transactions.athlete_id | lançamentos com reason começando por 'Renovação' |  | operacional | Aluno a que o registro se refere. |
| `servico_id` | uuid | sim | FK → novo.servico | origem.credit_transactions.reason | bucket do crédito: colchete no fim do texto [treino]/[fisio]/[nutri] → treino/fisioterapia/nutricao; sem colchete: 'Renovação semanal treino' → treino; 'Renovação mensal ... fisio' → fisioterapia; '... nutri' → nutricao; 'Renovação mensal PKZ' e 'Renovação mensal (N/N)' → treino; outro texto com fisio/nutri → esse serviço; resto → treino |  | operacional | Serviço a que o registro se refere. |
| `matricula_id` | uuid | não | FK → novo.matricula | — | matrícula vigente do aluno (novo.matricula) |  | operacional | Matrícula a que o registro pertence. |
| `competencia` | date | sim |  | origem.credit_transactions.created_at | semanal: date_trunc('week', created_at at time zone 'America/Sao_Paulo')::date; mensal: date_trunc('month', ...)::date. O '(N/N)' de 'Renovação mensal (N/N)' é a competência MM/AAAA e bate com created_at em 173 de 173 lançamentos |  | operacional | [revisar] |
| `periodicidade` | text | sim |  | origem.credit_transactions.reason | 'semanal' no texto → 'semana'; 'mensal' → 'mes' (obrigatória desde o 009) | mes \| semana | operacional | [revisar] |
| `executada_em` | timestamp with time zone | não |  | origem.credit_transactions.created_at | min(created_at) do grupo |  | operacional | Data e hora do evento que o nome indica. |
| `pendencia` | text | não |  | — |  |  | tecnico | Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga. |
| `criado_em` | timestamp with time zone | sim |  | origem.credit_transactions.created_at | min(created_at) do grupo |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `credito_lancamento`

Conceitual: LANÇAMENTO DE CRÉDITO. Origem: credit_transactions (serviço e origem lidos do texto de reason).

Linhas no ensaio de 12/10: **1155**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | origem.credit_transactions.id | direto |  | tecnico | Chave primária. |
| `aluno_id` | uuid | sim | FK → novo.aluno | origem.credit_transactions.athlete_id | direto |  | operacional | Aluno a que o registro se refere. |
| `servico_id` | uuid | sim | FK → novo.servico | origem.credit_transactions.reason | bucket do crédito: colchete no fim do texto [treino]/[fisio]/[nutri] → treino/fisioterapia/nutricao; sem colchete: 'Renovação semanal treino' → treino; 'Renovação mensal ... fisio' → fisioterapia; '... nutri' → nutricao; 'Renovação mensal PKZ' e 'Renovação mensal (N/N)' → treino; outro texto com fisio/nutri → esse serviço; resto → treino |  | operacional | Serviço a que o registro se refere. |
| `delta` | integer | sim |  | origem.credit_transactions.delta | direto (0 lançamentos com delta 0) |  | operacional | Movimento do crédito. Em origem_tipo = renovacao, é a COTA que passa a valer (a renovação redefine o saldo, não soma). |
| `motivo` | text | sim |  | origem.credit_transactions.reason | direto (texto original) |  | operacional | [revisar] |
| `origem_tipo` | text | sim |  | origem.credit_transactions.reason | começo do texto: Renovação → renovacao; Agendamento / Solicitação → agendamento; Cancelamento → estorno; Adição / Remoção / Ajuste manual → ajuste_manual; resto → outro |  | operacional | [revisar] |
| `renovacao_id` | uuid | não | FK → novo.renovacao | — | renovação do mesmo (aluno, serviço, competência), só para origem_tipo = renovacao |  | operacional | Chave estrangeira; ver a coluna Chave. |
| `ator_id` | uuid | não | FK → novo.perfil_usuario | origem.credit_transactions.actor_id | direto; sem perfil no destino → nulo |  | operacional | Chave estrangeira; ver a coluna Chave. |
| `pendencia` | text | não |  | — |  |  | tecnico | Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga. |
| `criado_em` | timestamp with time zone | sim |  | origem.credit_transactions.created_at | direto |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |
| `agendamento_id` | uuid | não | FK → novo.agendamento | — | nulo: a origem não liga o lançamento ao agendamento |  | operacional | Agendamento que originou o registro. |
