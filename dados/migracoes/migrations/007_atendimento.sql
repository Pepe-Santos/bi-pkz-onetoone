-- =============================================================================
-- 007_atendimento.sql
-- Domínio 5 · Atendimento especializado (diagrama modelo-conceitual/05-atendimento)
-- Dono: Micael (Frente 1). Pré-requisito: 006_avaliacao.sql.
--
-- Cria: atendimento, evolucao, anamnese, view vw_anamnese_vigente.
--
-- Escolhas:
--   * A especialização ATENDIMENTO -> {FISIOTERAPIA, NUTRIÇÃO, PSICOLOGIA}
--     (parcial) é a coluna servico_id; um trigger exige serviço especializado.
--   * EVOLUÇÃO é entidade fraca de ATENDIMENTO, chave parcial = data.
--   * ANAMNESE: o conceitual prevê no máximo uma por atleta (0,1). Na origem há
--     um aluno com duas avaliações de fisioterapia, então aqui é UMA POR
--     AVALIAÇÃO DE FISIO (avaliacao_id único) e a vigente sai da view
--     vw_anamnese_vigente (a mais recente). Registrado no cabeçalho para a
--     Frente 2 revisar.
--   * Anamnese é dado clínico (de criança, no PKZ): confidencialidade fixa
--     'restrito'. Quem vê é a pendência 5 (Frente 3).
--   * CPF, e-mail, endereço, telefone, profissão e sexo da fisio NÃO têm coluna
--     aqui (pendência 4).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- ATENDIMENTO ("recebe": ATLETA 0,N; "realiza": PROFISSIONAL 0,N)
-- -----------------------------------------------------------------------------
create table novo.atendimento (
  id              uuid primary key,              -- = physio_evolutions.id / specialist_evolutions.id
  aluno_id        uuid not null references novo.aluno (id),
  profissional_id uuid not null references novo.profissional (id),
  servico_id      uuid not null references novo.servico (id),
  agendamento_id  uuid references novo.agendamento (id),
  unidade_id      uuid references novo.unidade (id),
  data            date not null,
  observacao      text,
  pendencia       text,
  criado_em       timestamptz not null default now(),
  atualizado_em   timestamptz not null default now()
);
create index atendimento_aluno_idx        on novo.atendimento (aluno_id, data);
create index atendimento_profissional_idx on novo.atendimento (profissional_id);
create index atendimento_servico_idx      on novo.atendimento (servico_id);
create index atendimento_agendamento_idx  on novo.atendimento (agendamento_id);
create index atendimento_unidade_idx      on novo.atendimento (unidade_id);
comment on table novo.atendimento is
  'Conceitual: ATENDIMENTO (especializações FISIOTERAPIA, NUTRIÇÃO, PSICOLOGIA em servico_id). Origem: physio_evolutions, specialist_evolutions.';

create or replace function novo.exigir_servico_especializado()
returns trigger
language plpgsql
as $$
begin
  if not exists (select 1 from novo.servico s where s.id = new.servico_id and s.especializado) then
    raise exception 'Atendimento exige serviço especializado (fisioterapia, nutrição ou psicologia).'
      using errcode = 'check_violation';
  end if;
  return new;
end;
$$;

create trigger tg_servico_especializado
before insert or update of servico_id on novo.atendimento
for each row execute function novo.exigir_servico_especializado();

-- -----------------------------------------------------------------------------
-- EVOLUÇÃO (entidade fraca; "evolui")
-- -----------------------------------------------------------------------------
create table novo.evolucao (
  id             uuid primary key default gen_random_uuid(),
  atendimento_id uuid not null references novo.atendimento (id),
  data           date not null,
  observacao     text,
  pendencia      text,
  criado_em      timestamptz not null default now(),
  atualizado_em  timestamptz not null default now(),
  unique (atendimento_id, data)
);
comment on table novo.evolucao is 'Conceitual: EVOLUÇÃO (entidade fraca de ATENDIMENTO, chave parcial = data).';

-- -----------------------------------------------------------------------------
-- ANAMNESE ("possui": ATLETA — ANAMNESE)
-- -----------------------------------------------------------------------------
create table novo.anamnese (
  id                    uuid primary key,         -- = physio_assessments.id
  aluno_id              uuid not null references novo.aluno (id),
  avaliacao_id          uuid unique references novo.avaliacao (id),
  profissional_id       uuid references novo.profissional (id),
  data                  date not null,
  queixa_principal      text,
  hda                   text,                     -- história da doença atual
  hpp_doencas           text,                     -- história patológica pregressa
  hpp_cirurgias         text,
  hpp_fraturas          text,
  hpp_entorses          text,
  hab_freq_treinos      text,                     -- hábitos
  hab_outras_atividades text,
  hab_alcool            text,
  hab_tabagista         text,
  hab_medicamentos      text,
  fam_materna           text,                     -- histórico familiar
  fam_paterna           text,
  diagnostico_clinico   text,
  diagnostico_funcional text,
  exames_complementares text,
  observacao            text,
  dados_complementares  jsonb,                    -- parte não numérica de pkz_data
  confidencialidade     text not null default 'restrito' check (confidencialidade = 'restrito'),
  pendencia             text,
  criado_em             timestamptz not null default now(),
  atualizado_em         timestamptz not null default now()
);
create index anamnese_aluno_idx        on novo.anamnese (aluno_id, data);
create index anamnese_profissional_idx on novo.anamnese (profissional_id);
comment on table novo.anamnese is
  'Conceitual: ANAMNESE (histórico clínico do atleta). Origem: physio_assessments (campos clínicos) e pkz_data. Confidencialidade máxima.';

create view novo.vw_anamnese_vigente
with (security_invoker = true)
as
select distinct on (a.aluno_id) a.*
from novo.anamnese a
order by a.aluno_id, a.data desc, a.criado_em desc;
comment on view novo.vw_anamnese_vigente is 'Anamnese mais recente de cada aluno.';

-- -----------------------------------------------------------------------------
-- atualizado_em automático + RLS
-- -----------------------------------------------------------------------------
do $$
declare t text;
begin
  foreach t in array array['atendimento', 'evolucao', 'anamnese']
  loop
    perform novo.instalar_atualizado_em(format('novo.%I', t)::regclass);
    execute format('alter table novo.%I enable row level security', t);
  end loop;
end;
$$;
