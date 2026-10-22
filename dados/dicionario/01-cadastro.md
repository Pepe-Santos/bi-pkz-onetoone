# Cadastro e identidade

> Dicionário de dados do schema `novo` · migration 002 · gerado por `dicionario/gerar_dicionario.py`.

Sensibilidade: `clinico` (dado de saúde), `pessoal` (identifica alguém), `operacional` (rotina do negócio), `tecnico` (controle da carga).

## `unidade`

Conceitual: UNIDADE. Origem: enum student_program.

Linhas no ensaio de 12/10: **2**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | — | gen_random_uuid() |  | tecnico | Chave primária. |
| `codigo` | text | sim |  | enum student_program | valores do enum: pkz, one_to_one (2 linhas) | one_to_one \| pkz | operacional | Código curto e estável, usado nas regras e nos scripts. |
| `nome` | text | sim |  | — | constante: 'PKZ Lab / Playmakerz' (pkz), 'Studio One to One' (one_to_one) |  | pessoal | Nome de exibição. |
| `endereco` | text | não |  | — | nulo (o endereço de contato fica em configuracao_unidade) |  | pessoal | [revisar] |
| `ativo` | boolean | sim |  | — | true |  | operacional | Se o registro está ativo. |
| `criado_em` | timestamp with time zone | sim |  | — | now() |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `servico`

Conceitual: SERVIÇO. Origem: enum service_type.

Linhas no ensaio de 12/10: **4**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | — | gen_random_uuid() |  | tecnico | Chave primária. |
| `codigo` | text | sim |  | enum service_type | treino→treino, fisioterapeuta→fisioterapia, nutricionista→nutricao, psicologo→psicologia (4 linhas) | fisioterapia \| nutricao \| psicologia \| treino | operacional | Código curto e estável, usado nas regras e nos scripts. |
| `nome` | text | sim |  | — | constante: Treino, Fisioterapia, Nutrição, Psicologia |  | pessoal | Nome de exibição. |
| `especializado` | boolean | sim |  | — | codigo <> 'treino' |  | operacional | [revisar] |
| `ativo` | boolean | sim |  | — | true |  | operacional | Se o registro está ativo. |
| `ordem` | integer | sim |  | — | 1 treino, 2 fisioterapia, 3 nutricao, 4 psicologia |  | operacional | Ordem de exibição na tela. |
| `criado_em` | timestamp with time zone | sim |  | — | now() |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `configuracao_unidade`

Fora do conceitual (parâmetro operacional). Origem: app_settings (1 linha, copiada para as duas unidades com pendência).

Linhas no ensaio de 12/10: **2**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `unidade_id` | uuid | sim | PK | origem.app_settings (1 linha) | a única linha é copiada para as 2 unidades (cross join com novo.unidade) |  | operacional | Unidade (PKZ ou One to One) a que o registro pertence. |
| `prazo_cancelamento_horas` | integer | sim |  | origem.app_settings.cancel_deadline_hours | direto |  | operacional | [revisar] |
| `capacidade_padrao` | integer | sim |  | origem.app_settings.default_capacity | direto |  | operacional | [revisar] |
| `limite_credito_baixo` | integer | sim |  | origem.app_settings.low_credit_threshold | direto |  | operacional | [revisar] |
| `creditos_mensais` | integer | sim |  | origem.app_settings.monthly_credits | direto |  | operacional | [revisar] |
| `renovacao_dia` | integer | sim |  | origem.app_settings.renewal_day | direto |  | operacional | [revisar] |
| `renovacao_dia_semana` | integer | sim |  | origem.app_settings.renewal_weekday | renewal_weekday % 7: a origem usa ISO (1 = segunda … 7 = domingo); o destino usa dow (0 = domingo), igual à grade e ao bloqueio |  | operacional | [revisar] |
| `renovacao_ativa` | boolean | sim |  | origem.app_settings.renewal_enabled | direto |  | operacional | [revisar] |
| `ultima_renovacao_em` | timestamp with time zone | não |  | origem.app_settings.last_renewal_at | direto |  | operacional | Data e hora do evento que o nome indica. |
| `espera_aceite_horas` | integer | sim |  | origem.app_settings.waitlist_accept_hours | direto |  | operacional | [revisar] |
| `liberacao_automatica` | boolean | sim |  | origem.app_settings.auto_release_enabled | direto |  | operacional | [revisar] |
| `liberacao_intervalo_min` | integer | sim |  | origem.app_settings.auto_release_interval_minutes | direto |  | operacional | [revisar] |
| `contato_endereco` | text | não |  | origem.app_settings.contact_address | direto |  | operacional | [revisar] |
| `contato_instagram` | text | não |  | origem.app_settings.contact_instagram | direto |  | operacional | [revisar] |
| `contato_telefone` | text | não |  | origem.app_settings.contact_phone | direto (telefone comercial do centro, não é dado pessoal) |  | operacional | [revisar] |
| `contato_site` | text | não |  | origem.app_settings.contact_website | direto |  | operacional | [revisar] |
| `pendencia` | text | não |  | — |  |  | tecnico | Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga. |
| `criado_em` | timestamp with time zone | sim |  | — | now() |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |
| `creditos_fisio_padrao` | integer | não |  | origem.app_settings.credits_fisio_standard | direto (coluna criada no 009) |  | operacional | Origem: app_settings.credits_fisio_standard. |
| `creditos_nutri_padrao` | integer | não |  | origem.app_settings.credits_nutri_standard | direto (coluna criada no 009) |  | operacional | Origem: app_settings.credits_nutri_standard. |

## `pessoa`

Conceitual: PESSOA. Origem: athletes (alunos), profiles (usuários), responsavel_secundario_* (texto).

Linhas no ensaio de 12/10: **258**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | origem.athletes.id \| origem.profiles.id | aluno: = athletes.id; usuário: = profiles.id (sem colisão na foto: 0 ids repetidos) |  | tecnico | Chave primária. |
| `nome` | text | sim |  | origem.athletes.name \| origem.profiles.full_name; origem.athletes.responsavel_secundario_nome | (secundário só em texto) btrim; btrim; perfil com full_name vazio: username |  | pessoal | Nome de exibição. |
| `data_nascimento` | date | não |  | origem.athletes.birth_date | direto (usuários: nulo) |  | pessoal | [revisar] |
| `cpf` | text | não |  | — | nulo |  | pessoal | [revisar] |
| `telefone` | text | não |  | origem.athletes.phone \| origem.profiles.phone; origem.athletes.responsavel_secundario_telefone | (secundário só em texto) btrim; btrim; vazio → nulo |  | pessoal | [revisar] |
| `foto_url` | text | não |  | origem.athletes.photo_url \| origem.profiles.avatar_url | direto |  | pessoal | [revisar] |
| `origem_tabela` | text | não |  | — | 'athletes' ou 'profiles' | athletes \| profiles | tecnico | Tabela da origem de onde o registro veio. |
| `origem_id` | uuid | não |  | origem.athletes.id \| origem.profiles.id | direto |  | tecnico | Id do registro na tabela de origem. |
| `pendencia` | text | não |  | — |  |  | tecnico | Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga. |
| `criado_em` | timestamp with time zone | sim |  | origem.athletes.created_at \| origem.profiles.created_at | direto |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `perfil_usuario`

Conceitual: USUÁRIO. Origem: profiles.

Linhas no ensaio de 12/10: **152**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `usuario_id` | uuid | sim | PK | origem.profiles.id | direto (= id do login) |  | operacional | Usuário de login dono do registro. |
| `pessoa_id` | uuid | sim | FK → novo.pessoa | origem.profiles.id | = pessoa.id do próprio perfil |  | operacional | Pessoa a que o registro se refere. |
| `username` | text | sim |  | origem.profiles.username | direto (único na origem: 0 repetidos) |  | pessoal | [revisar] |
| `email` | text | não |  | — | nulo: o e-mail do login está em auth.users, fora da foto |  | pessoal | [revisar] |
| `status` | text | sim |  | origem.profiles.status | direto | ativo | operacional | Situação do registro. |
| `ativo` | boolean | sim |  | origem.profiles.active | direto |  | operacional | Se o registro está ativo. |
| `trocar_senha` | boolean | sim |  | origem.profiles.must_change_password | direto |  | operacional | [revisar] |
| `pode_agendar` | boolean | sim |  | origem.profiles.can_schedule | direto |  | operacional | [revisar] |
| `pode_treinar` | boolean | sim |  | origem.profiles.can_train | coalesce(can_train, false) |  | operacional | [revisar] |
| `pendencia` | text | não |  | — |  |  | tecnico | Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga. |
| `criado_em` | timestamp with time zone | sim |  | origem.profiles.created_at | direto |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `papel`

Conceitual: PAPEL. Origem: enum app_role (9 valores -> catálogo menor).

Linhas no ensaio de 12/10: **5**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | — | gen_random_uuid() |  | tecnico | Chave primária. |
| `codigo` | text | sim |  | enum app_role | 9 valores → 5 códigos: admin; professor (professor, professor_pkz, professor_one_to_one); especialista (nutricionista, psicologo, fisioterapeuta); responsavel; recepcao | admin \| especialista \| professor \| recepcao \| responsavel | operacional | Código curto e estável, usado nas regras e nos scripts. |
| `nome` | text | sim |  | — | constante: Administrador, Professor, Especialista, Responsável, Recepção |  | pessoal | Nome de exibição. |
| `ativo` | boolean | sim |  | — | true |  | operacional | Se o registro está ativo. |
| `criado_em` | timestamp with time zone | sim |  | — | now() |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `papel_usuario`

Conceitual: relacionamentos "exerce" e "atua em". Origem: user_roles.

Linhas no ensaio de 12/10: **153**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | — | gen_random_uuid() |  | tecnico | Chave primária. |
| `usuario_id` | uuid | sim | FK → novo.perfil_usuario | origem.user_roles.user_id | direto (0 fora de profiles) |  | operacional | Usuário de login dono do registro. |
| `papel_id` | uuid | sim | FK → novo.papel | origem.user_roles.role | role → codigo de novo.papel (ver referencia.csv) |  | operacional | Papel do usuário. |
| `unidade_id` | uuid | não | FK → novo.unidade | origem.user_roles.role | professor_pkz → pkz; professor_one_to_one → one_to_one; demais → nulo (todas) |  | operacional | Unidade (PKZ ou One to One) a que o registro pertence. |
| `desde` | date | não |  | origem.user_roles.created_at | created_at::date (o menor, se agrupar) |  | operacional | [revisar] |
| `papel_origem` | text | não |  | origem.user_roles.role | agrupa por (usuario, papel, unidade): string_agg dos roles originais, ex.: 'nutricionista,psicologo' | admin \| fisioterapeuta \| nutricionista \| professor \| professor_one_to_one \| professor_pkz \| psicologo \| recepcao \| responsavel | operacional | [revisar] |
| `pendencia` | text | não |  | — |  |  | tecnico | Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga. |
| `criado_em` | timestamp with time zone | sim |  | origem.user_roles.created_at | min(created_at) do grupo |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `aluno`

Conceitual: ATLETA. Origem: athletes. A unidade vem da matrícula (003_comercial).

Linhas no ensaio de 12/10: **106**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | origem.athletes.id | direto |  | tecnico | Chave primária. |
| `pessoa_id` | uuid | sim | FK → novo.pessoa | origem.athletes.id | = pessoa.id do aluno |  | operacional | Pessoa a que o registro se refere. |
| `status` | text | sim |  | origem.athletes.status | enum athlete_status → texto (só 'ativo' na foto) | ativo | operacional | Situação do registro. |
| `data_entrada` | date | não |  | origem.athletes.created_at | (created_at at time zone 'America/Sao_Paulo')::date |  | operacional | [revisar] |
| `data_saida` | date | não |  | — | nulo (a origem não guarda saída) |  | operacional | [revisar] |
| `categoria` | text | não |  | origem.athletes.category | c = lower(btrim(espaços múltiplos → 1)); 'sub 10' / 'sub10' → 'sub_10'; só número ('13') → 'sub_13'; esportes sem acento ('natação' → 'natacao'); vazio → nulo | hipismo \| natacao \| sub_10 \| sub_11 \| sub_12 \| sub_13 \| sub_8 \| sub_9 | operacional | [revisar] |
| `categoria_original` | text | não |  | origem.athletes.category | direto (sem normalizar) |  | operacional | [revisar] |
| `observacao` | text | não |  | origem.athletes.notes | direto |  | operacional | Texto livre escrito por quem registrou. |
| `pendencia` | text | não |  | — |  |  | tecnico | Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga. |
| `criado_em` | timestamp with time zone | sim |  | origem.athletes.created_at | direto |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `aluno_servico`

Fora do conceitual (regra operacional). Origem: athletes.allowed_services (array normalizado).

Linhas no ensaio de 12/10: **254**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `aluno_id` | uuid | sim | PK | origem.athletes.id | direto |  | operacional | Aluno a que o registro se refere. |
| `servico_id` | uuid | sim | PK | origem.athletes.allowed_services | unnest(allowed_services) → valor: treino→treino, fisioterapeuta→fisioterapia, nutricionista→nutricao, psicologo→psicologia; busca novo.servico.id pelo codigo |  | operacional | Serviço a que o registro se refere. |
| `criado_em` | timestamp with time zone | sim |  | origem.athletes.created_at | direto |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `responsavel_aluno`

Conceitual: relacionamento "responde por" (deixou de ser entidade). Origem: athletes.responsavel_id e responsavel_secundario_*.

Linhas no ensaio de 12/10: **106**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `aluno_id` | uuid | sim | PK | origem.athletes.id | direto |  | operacional | Aluno a que o registro se refere. |
| `pessoa_id` | uuid | sim | PK | origem.athletes.responsavel_id \| origem.athletes.responsavel_secundario_id | principal: pessoa do perfil responsavel_id; secundário: pessoa do perfil responsavel_secundario_id; secundário só em texto: pessoa nova (origem_tabela 'athletes.responsavel_secundario', origem_id = athletes.id) |  | operacional | Pessoa a que o registro se refere. |
| `tipo_vinculo` | text | sim |  | — | 'responsavel'; 'proprio' quando pessoa.pendencia indica aluno = responsável | responsavel | operacional | [revisar] |
| `principal` | boolean | sim |  | — | true para responsavel_id; false para o secundário |  | operacional | [revisar] |
| `pode_agendar` | boolean | sim |  | — | true (a origem não tem a regra por vínculo; can_schedule é do usuário) |  | operacional | [revisar] |
| `pendencia` | text | não |  | — |  |  | tecnico | Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga. |
| `criado_em` | timestamp with time zone | sim |  | origem.athletes.created_at | direto |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `profissional`

Conceitual: PROFISSIONAL. Origem: profiles com papel de professor ou especialista. id = profiles.id.

Linhas no ensaio de 12/10: **31**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | origem.profiles.id | usuários com papel professor*, nutricionista, psicologo ou fisioterapeuta + quem aparece como bookings.professor_id, training_reports.professor_id, physical_test_sessions.evaluator_id, physio_assessments.physio_id, physio_evolutions.physio_id ou specialist_evolutions.professional_id |  | tecnico | Chave primária. |
| `registro_conselho` | text | não |  | — | nulo (a origem não tem) |  | pessoal | [revisar] |
| `especialidade` | text | não |  | origem.user_roles.role | string_agg dos serviços habilitados (treino, fisioterapia, nutricao, psicologia) | fisioterapia \| fisioterapia, treino \| nutricao \| psicologia \| treino | operacional | [revisar] |
| `ativo` | boolean | sim |  | origem.profiles.active | direto |  | operacional | Se o registro está ativo. |
| `pendencia` | text | não |  | — |  |  | tecnico | Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga. |
| `criado_em` | timestamp with time zone | sim |  | origem.profiles.created_at | direto |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `profissional_servico`

Conceitual: relacionamento "habilitado em". Origem: user_roles.

Linhas no ensaio de 12/10: **32**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `profissional_id` | uuid | sim | PK | origem.user_roles.user_id | direto |  | operacional | Profissional responsável pelo registro. |
| `servico_id` | uuid | sim | PK | origem.user_roles.role \| origem.bookings.service | professor/professor_pkz/professor_one_to_one → treino; fisioterapeuta → fisioterapia; nutricionista → nutricao; psicologo → psicologia; admin atuando: bookings.service dos agendamentos em que aparece, treino se aparece em training_reports ou physical_test_sessions, fisioterapia se aparece em physio_assessments ou physio_evolutions, specialist_evolutions.service |  | operacional | Serviço a que o registro se refere. |
| `criado_em` | timestamp with time zone | sim |  | origem.user_roles.created_at | min(created_at) |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |
