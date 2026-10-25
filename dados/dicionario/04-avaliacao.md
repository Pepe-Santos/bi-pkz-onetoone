# Avaliação e testes físicos

> Dicionário de dados do schema `novo` · migration 006 · gerado por `dicionario/gerar_dicionario.py`.

Sensibilidade: `clinico` (dado de saúde), `pessoal` (identifica alguém), `operacional` (rotina do negócio), `tecnico` (controle da carga).

## `metrica`

Conceitual: MÉTRICA. Origem: catálogo do app (src/lib/physical-test-schema.ts) e colunas de physio_assessments / weekly_evaluations.

Linhas no ensaio de 12/10: **109**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | — | gen_random_uuid() |  | tecnico | Chave primária. |
| `codigo` | text | sim |  | src/lib/physical-test-schema.ts, src/lib/physio-pkz-schema.ts, colunas de physio_assessments e weekly_evaluations | uma linha por métrica de avaliacao_metricas.csv (as de fisioterapia são criadas aqui também, para o script 70 usar) | antropometria_altura \| antropometria_peso \| banco_wells \| blazepod_foco \| blazepod_vel_reacao_hits \| blazepod_vel_reacao_legado \| blazepod_vel_reacao_ms \| cross_hop \| estabilidade_aquabag \| fisio_appley_inf \| fisio_appley_sup \| fisio_cotovelo_ext \| fisio_cotovelo_flex | operacional | Código curto e estável, usado nas regras e nos scripts. |
| `nome` | text | sim |  | idem | rótulo do app (avaliacao_metricas.csv) |  | operacional | Nome de exibição. |
| `dominio` | text | sim |  | — | avaliacao_metricas.csv | antropometria \| fisioterapia \| semanal \| teste_fisico | operacional | [revisar] |
| `unidade_medida` | text | não |  | src/lib/physical-test-schema.ts (unit) | avaliacao_metricas.csv | % \| cm \| desequilibrios \| escala_1_5 \| graus \| hits \| kg \| km/h \| m \| ms \| s | operacional | [revisar] |
| `tipo_dado` | text | sim |  | — | avaliacao_metricas.csv | escala \| numero \| texto | operacional | [revisar] |
| `direcao_desejada` | text | não |  | — | avaliacao_metricas.csv | maior \| menor \| nenhuma | operacional | [revisar] |
| `valor_min` | numeric | não |  | — | nulo (faixa plausível ainda não definida: pendência 2) |  | operacional | [revisar] |
| `valor_max` | numeric | não |  | — | nulo (pendência 2) |  | operacional | [revisar] |
| `usa_lado` | boolean | sim |  | — | avaliacao_metricas.csv |  | operacional | [revisar] |
| `ativo` | boolean | sim |  | — | true |  | operacional | Se o registro está ativo. |
| `ordem` | integer | sim |  | — | ordem de avaliacao_metricas.csv |  | operacional | Ordem de exibição na tela. |
| `pendencia` | text | não |  | — |  |  | tecnico | Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga. |
| `criado_em` | timestamp with time zone | sim |  | — | now() |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `avaliacao`

Conceitual: AVALIAÇÃO (especializações FÍSICA e SEMANAL em `tipo`). Origem: physical_test_sessions, physio_assessments, weekly_evaluations.

Linhas no ensaio de 12/10: **64**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | origem.physical_test_sessions.id \| origem.weekly_evaluations.id; origem.physio_assessments.id | direto; direto (tipo fisioterapia) |  | tecnico | Chave primária. |
| `aluno_id` | uuid | sim | FK → novo.aluno | origem.physical_test_sessions.athlete_id \| origem.weekly_evaluations.athlete_id; origem.physio_assessments.athlete_id | direto |  | operacional | Aluno a que o registro se refere. |
| `unidade_id` | uuid | sim | FK → novo.unidade | origem.physio_assessments.program; origem.weekly_evaluations.unit | novo.unidade_atual_do_aluno(aluno_id) (program só confere); teste físico: novo.unidade_atual_do_aluno(aluno_id); semanal: unit (program: pkz→pkz, one_to_one→one_to_one; busca novo.unidade.id pelo codigo) |  | operacional | Unidade (PKZ ou One to One) a que o registro pertence. |
| `tipo` | text | sim |  | — | 'fisioterapia'; 'teste_fisico' (physical_test_sessions); 'semanal' (weekly_evaluations) | fisioterapia \| semanal \| teste_fisico | operacional | [revisar] |
| `data` | date | sim |  | origem.physical_test_sessions.test_date \| origem.weekly_evaluations.week_start_date; origem.physio_assessments.assessment_date | direto |  | operacional | Data a que o registro se refere. |
| `avaliador_id` | uuid | não | FK → novo.profissional | origem.physical_test_sessions.evaluator_id; origem.physio_assessments.physio_id | direto; direto; semanal: nulo |  | operacional | Chave estrangeira; ver a coluna Chave. |
| `avaliador_nome` | text | não |  | origem.physical_test_sessions.evaluator_name; origem.physio_assessments.physio_name | só quando evaluator_id é nulo (0 na foto); só quando physio_id é nulo |  | pessoal | [revisar] |
| `status` | text | sim |  | origem.physio_assessments.status | 'consolidada'; final → consolidada; rascunho → rascunho | consolidada | operacional | Situação do registro. |
| `consolidada_em` | timestamp with time zone | não |  | origem.physical_test_sessions.created_at \| origem.weekly_evaluations.created_at; origem.physio_assessments.updated_at | direto; só para final: updated_at |  | operacional | Data e hora do evento que o nome indica. |
| `corrige_avaliacao_id` | uuid | não | FK → novo.avaliacao | — | nulo |  | operacional | Chave estrangeira; ver a coluna Chave. |
| `observacoes` | text | não |  | origem.physical_test_sessions.observacoes \| origem.weekly_evaluations.observations | direto; nulo (a observação da fisio vai para anamnese.observacao) |  | operacional | Texto livre escrito por quem registrou. |
| `criado_por` | uuid | não | FK → novo.perfil_usuario | origem.physical_test_sessions.created_by \| origem.weekly_evaluations.created_by; origem.physio_assessments.created_by | direto; sem perfil → nulo |  | operacional | Usuário que criou o registro na origem. |
| `pendencia` | text | não |  | — |  |  | tecnico | Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga. |
| `criado_em` | timestamp with time zone | sim |  | origem.physical_test_sessions.created_at \| origem.weekly_evaluations.created_at; origem.physio_assessments.created_at | direto |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |

## `avaliacao_medida`

Conceitual: MEDIDA (entidade fraca de AVALIAÇÃO). Origem: physical_test_sessions.data (jsonb), altura/peso, colunas numéricas de physio_assessments, notas de weekly_evaluations.

Linhas no ensaio de 12/10: **2908**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | uuid | sim | PK | — | gen_random_uuid() |  | tecnico | Chave primária. |
| `avaliacao_id` | uuid | sim | FK → novo.avaliacao | origem.physical_test_sessions.id \| origem.weekly_evaluations.id; origem.physio_assessments.id | direto |  | operacional | Avaliação a que o registro pertence. |
| `metrica_id` | uuid | sim | FK → novo.metrica | origem.physical_test_sessions.data \| altura \| peso \| origem.weekly_evaluations.rating_environment \| rating_evolution \| rating_quality \| rating_satisfaction \| rating_service; origem.physio_assessments.cotovelo_ext_dir \| origem.physio_assessments.cotovelo_ext_esq \| origem.physio_assessments.cotovelo_flex_dir \| origem.physio_assessments.cotovelo_flex_esq \| origem.physio_assessments.joelho_ext_dir \| origem.physio_assessments.joelho_ext_esq \| origem.physio_assessments.joelho_flex_dir \| origem.physio_assessments.joelho_flex_esq \| origem.physio_assessments.ombro_abd_dir \| origem.physio_assessments.ombro_abd_esq \| origem.physio_assessments.ombro_rot_ext_dir \| origem.physio_assessments.ombro_rot_ext_esq \| origem.physio_assessments.quadril_dir \| origem.physio_assessments.quadril_esq \| origem.physio_assessments.appley_dir_inf \| appley_dir_sup \| appley_esq_inf \| appley_esq_sup \| pkz_data | goniometria: cross join lateral (values ('cotovelo_ext','dir', a.cotovelo_ext_dir), …) → 'fisio_' \|\| medida; Appley → fisio_appley_sup / fisio_appley_inf; pkz_data: forca_<x>_<lado> → fisio_pkz_forca_<x>; forca_abdominal → fisio_pkz_forca_abdominal; ratio_<x>_<lado> → fisio_pkz_ratio_<x>; mob_<x>_<lado> → fisio_pkz_mob_<x>; post_<vista>_<campo>_valor → fisio_pkz_post_<vista>_<campo-sem-lado>; post_<vista>_<campo>_dir → fisio_pkz_post_<vista>_<campo-sem-lado>_direcao (vistas: anterior, lateral_dir, posterior, lateral_esq; ATENÇÃO: o sufixo final _dir é 'direção do desvio', não 'direito'); listas simples (banco_wells, sprint_10, sprint_20, illinois, slalom_wallball, estabilidade_aquabag, blazepod_foco) → métrica de mesmo nome; single_hop/cross_hop → métrica do bloco; saltos_vert e blazepod_vel_reacao (objeto) → bloco \|\| '_' \|\| subchave; teste_vo2 → 'teste_vo2_' \|\| campo; blazepod_vel_reacao em lista simples (4 sessões antigas) → 'blazepod_vel_reacao_legado'; altura → antropometria_altura; peso → antropometria_peso; rating_environment/evolution/quality/satisfaction/service → semanal_ambiente/evolucao/qualidade/satisfacao/atendimento |  | operacional | Métrica medida. |
| `lado` | text | não |  | chaves direita/esquerda de single_hop e cross_hop; nome da coluna / chave | direita → dir; esquerda → esq; demais → nulo; goniometria e Appley: _dir → dir, _esq → esq; pkz_data: forca_*/ratio_*/mob_* pelo sufixo _dir/_esq; post_*: lado só quando o campo termina em _dir/_esq ANTES do sufixo (eias_patela_dir, angulo_q_esq, tibia_dir, rotacao_pe_esq, pronacao_pe_dir …) | dir \| esq | operacional | [revisar] |
| `tentativa` | smallint | sim |  | posição na lista | 1; with ordinality (1, 2, 3); campos nominais, altura, peso, notas → 1 |  | operacional | [revisar] |
| `valor_num` | numeric | não |  | colunas numeric \| textos de pkz_data; origem.physical_test_sessions.data \| altura \| peso \| origem.weekly_evaluations.rating_environment \| rating_evolution \| rating_quality \| rating_satisfaction \| rating_service | goniometria: direto; pkz_data: novo.texto_para_numero(v); mob com símbolo de grau ('33º'): tira º/° antes de converter; nulos e vazios não geram linha; Appley 'Não avaliado' não gera linha; novo.texto_para_numero(v); teste_vo2_tempo_total e _tempo_vel_max: novo.mmss_para_segundos(v); altura e peso já são numeric; vazio ('') não gera linha; altura/peso nulos (21/18 na foto) não geram linha; notas semanais: direto |  | operacional | [revisar] |
| `valor_texto` | text | não |  | appley_* \| post_*_dir \| pkz_data não numérico; idem | Appley e direção postural: texto (Positivo/Negativo, Anterior, Interna …); número que não converteu: texto original; texto original quando a conversão dá nulo (ex.: aquabag antigo com 3 números no mesmo campo); legado do blazepod sempre aqui |  | operacional | [revisar] |
| `pendencia` | text | não |  | — |  |  | tecnico | Dúvidas que a carga marcou, separadas por `; `. Nunca bloqueia a carga. |
| `criado_em` | timestamp with time zone | sim |  | origem.physical_test_sessions.created_at \| origem.weekly_evaluations.created_at; origem.physio_assessments.created_at | direto |  | tecnico | Quando o registro entrou no banco novo; recebe o `created_at` da origem quando existe. |
| `atualizado_em` | timestamp with time zone | sim |  | — | now(); o on conflict do update grava now() |  | tecnico | Última atualização; o `on conflict do update` grava `now()`. |
