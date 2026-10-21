-- =============================================================================
-- 004_agenda.sql
-- Domínio 3 · Agenda e treino, parte 1 (diagrama modelo-conceitual/03-agenda)
-- Dono: Micael (Frente 1). Pré-requisito: 003_comercial.sql.
--
-- Cria: horario_grade, bloqueio_agenda, bloqueio_grade, agendamento,
--       sessao_treino, lista_espera, feedback_treino,
--       coluna credito_lancamento.agendamento_id,
--       trigger de capacidade no agendamento.
--
-- Escolhas (decididas por Micael em 13/10/2026, seguindo o conceitual):
--   * Data, hora, serviço e PROFISSIONAL ficam no AGENDAMENTO ("conduz" liga
--     PROFISSIONAL a AGENDAMENTO). A proposta tinha uma tabela `sessao` agrupando
--     agendamentos; nos dados, 313/536 agendamentos não têm professor e 28 horários
--     têm professores diferentes, e o One to One é individual.
--   * SESSÃO DE TREINO (sessao_treino) é a realização de um agendamento (1:1).
--   * Capacidade: trigger conta os agendamentos ativos do mesmo horário
--     (unidade, serviço, data, hora) e compara com horario_grade.capacidade
--     ou, sem grade, com configuracao_unidade.capacidade_padrao.
--     Na carga (novo.em_modo_carga()) não confere.
--   * "suspende" (BLOQUEIO N:M GRADE) vira bloqueio_grade.
--   * training_slots não migra (morto); waitlist vazia: só estrutura.
--   * FEEDBACK (legado): 1 por agendamento.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- HORÁRIO DE GRADE ("oferece": UNIDADE 1:N GRADE)
-- -----------------------------------------------------------------------------
create table novo.horario_grade (
  id              uuid primary key default gen_random_uuid(),
  unidade_id      uuid not null references novo.unidade (id),
  servico_id      uuid not null references novo.servico (id),
  dia_semana      smallint not null check (dia_semana between 0 and 6),   -- 0 = domingo (extract(dow))
  hora_inicio     time not null,
  hora_fim        time not null,
  capacidade      int  not null check (capacidade > 0),
  vigencia_inicio date not null,
  vigencia_fim    date,
  pendencia       text,
  criado_em       timestamptz not null default now(),
  atualizado_em   timestamptz not null default now(),
  check (hora_fim > hora_inicio),
  check (vigencia_fim is null or vigencia_fim >= vigencia_inicio),
  unique (unidade_id, servico_id, dia_semana, hora_inicio, vigencia_inicio)
);
create index horario_grade_servico_idx on novo.horario_grade (servico_id);
comment on table novo.horario_grade is
  'Conceitual: HORÁRIO DE GRADE. Origem: regras das funções is_valid_slot e get_service_day (não há tabela na origem).';

-- -----------------------------------------------------------------------------
-- BLOQUEIO e "suspende"
-- -----------------------------------------------------------------------------
create table novo.bloqueio_agenda (
  id            uuid primary key,                 -- = schedule_blocks.id
  unidade_id    uuid references novo.unidade (id),   -- nulo = todas as unidades
  servico_id    uuid references novo.servico (id),   -- nulo = todos os serviços
  data          date not null,                     -- dia do bloqueio (ou início, se permanente)
  permanente    boolean not null default false,
  dia_semana    smallint check (dia_semana between 0 and 6),   -- para bloqueio permanente
  hora_inicio   time not null,
  hora_fim      time not null,
  motivo        text,
  criado_por    uuid references novo.perfil_usuario (usuario_id),
  pendencia     text,
  criado_em     timestamptz not null default now(),
  atualizado_em timestamptz not null default now(),
  check (hora_fim > hora_inicio)
);
create index bloqueio_agenda_unidade_idx    on novo.bloqueio_agenda (unidade_id);
create index bloqueio_agenda_servico_idx    on novo.bloqueio_agenda (servico_id);
create index bloqueio_agenda_criado_por_idx on novo.bloqueio_agenda (criado_por);
create index bloqueio_agenda_data_idx       on novo.bloqueio_agenda (data);
comment on table novo.bloqueio_agenda is 'Conceitual: BLOQUEIO. Origem: schedule_blocks.';

create table novo.bloqueio_grade (
  bloqueio_id      uuid not null references novo.bloqueio_agenda (id),
  horario_grade_id uuid not null references novo.horario_grade (id),
  criado_em        timestamptz not null default now(),
  atualizado_em    timestamptz not null default now(),
  primary key (bloqueio_id, horario_grade_id)
);
create index bloqueio_grade_grade_idx on novo.bloqueio_grade (horario_grade_id);
comment on table novo.bloqueio_grade is 'Conceitual: relacionamento "suspende" (BLOQUEIO N:M HORÁRIO DE GRADE).';

-- -----------------------------------------------------------------------------
-- AGENDAMENTO ("reserva", "é do tipo", "conduz", "origina")
-- -----------------------------------------------------------------------------
create table novo.agendamento (
  id                  uuid primary key,             -- = bookings.id
  aluno_id            uuid not null references novo.aluno (id),
  unidade_id          uuid not null references novo.unidade (id),
  servico_id          uuid not null references novo.servico (id),
  horario_grade_id    uuid references novo.horario_grade (id),
  profissional_id     uuid references novo.profissional (id),
  data                date not null,
  hora_inicio         time not null,
  hora_fim            time,
  status              text not null default 'agendado'
                      check (status in ('agendado', 'aguardando_confirmacao', 'presente', 'falta', 'cancelado')),
  criado_por          uuid references novo.perfil_usuario (usuario_id),
  confirmado_em       timestamptz,
  cancelado_em        timestamptz,
  motivo_cancelamento text,
  pendencia           text,
  criado_em           timestamptz not null default now(),
  atualizado_em       timestamptz not null default now(),
  check (hora_fim is null or hora_fim > hora_inicio)
);
create index agendamento_aluno_idx        on novo.agendamento (aluno_id);
create index agendamento_horario_idx      on novo.agendamento (unidade_id, servico_id, data, hora_inicio);
create index agendamento_servico_idx      on novo.agendamento (servico_id);
create index agendamento_grade_idx        on novo.agendamento (horario_grade_id);
create index agendamento_profissional_idx on novo.agendamento (profissional_id);
create index agendamento_criado_por_idx   on novo.agendamento (criado_por);
-- um aluno não tem dois agendamentos ativos no mesmo serviço e horário (origem: 0 casos)
create unique index agendamento_aluno_horario_ativo
  on novo.agendamento (aluno_id, servico_id, data, hora_inicio)
  where status <> 'cancelado';
comment on table novo.agendamento is 'Conceitual: AGENDAMENTO. Origem: bookings.';

-- Capacidade do horário: grade vigente na data; sem grade, a capacidade padrão da unidade.
create or replace function novo.capacidade_do_horario(p_unidade uuid, p_servico uuid, p_data date, p_hora time)
returns int
language sql
stable
as $$
  select coalesce(
    (select g.capacidade
       from novo.horario_grade g
      where g.unidade_id = p_unidade and g.servico_id = p_servico
        and g.dia_semana = extract(dow from p_data)
        and p_hora >= g.hora_inicio and p_hora < g.hora_fim
        and p_data >= g.vigencia_inicio and (g.vigencia_fim is null or p_data <= g.vigencia_fim)
      order by g.vigencia_inicio desc
      limit 1),
    (select c.capacidade_padrao from novo.configuracao_unidade c where c.unidade_id = p_unidade)
  );
$$;

create or replace function novo.conferir_capacidade_agendamento()
returns trigger
language plpgsql
as $$
declare
  v_cap    int;
  v_ocup   int;
begin
  if novo.em_modo_carga() or new.status in ('cancelado', 'falta') then
    return new;
  end if;
  -- só confere quando o agendamento passa a ocupar uma vaga ou muda de horário
  if tg_op = 'UPDATE'
     and old.status not in ('cancelado', 'falta')
     and (old.unidade_id, old.servico_id, old.data, old.hora_inicio)
         is not distinct from (new.unidade_id, new.servico_id, new.data, new.hora_inicio) then
    return new;
  end if;

  v_cap := novo.capacidade_do_horario(new.unidade_id, new.servico_id, new.data, new.hora_inicio);
  if v_cap is null then
    return new;   -- sem grade e sem configuração: nada a conferir
  end if;

  -- trava o horário para dois agendamentos simultâneos não passarem juntos
  perform pg_advisory_xact_lock(hashtextextended(
    new.unidade_id::text || new.servico_id::text || new.data::text || new.hora_inicio::text, 0));

  select count(*) into v_ocup
  from novo.agendamento a
  where a.unidade_id = new.unidade_id and a.servico_id = new.servico_id
    and a.data = new.data and a.hora_inicio = new.hora_inicio
    and a.status not in ('cancelado', 'falta')
    and a.id <> new.id;

  if v_ocup >= v_cap then
    raise exception 'Horário lotado: % de % vagas ocupadas (%, %).', v_ocup, v_cap, new.data, new.hora_inicio
      using errcode = 'check_violation';
  end if;
  return new;
end;
$$;

create trigger tg_capacidade
before insert or update of status, unidade_id, servico_id, data, hora_inicio on novo.agendamento
for each row execute function novo.conferir_capacidade_agendamento();

-- -----------------------------------------------------------------------------
-- SESSÃO DE TREINO ("produz": AGENDAMENTO 1:1 SESSÃO)
-- -----------------------------------------------------------------------------
create table novo.sessao_treino (
  id              uuid primary key default gen_random_uuid(),
  agendamento_id  uuid not null unique references novo.agendamento (id),
  profissional_id uuid references novo.profissional (id),
  data            date not null,
  hora_inicio     time,
  hora_fim        time,
  observacao      text,
  pendencia       text,
  criado_em       timestamptz not null default now(),
  atualizado_em   timestamptz not null default now(),
  check (hora_fim is null or hora_inicio is null or hora_fim > hora_inicio)
);
create index sessao_treino_profissional_idx on novo.sessao_treino (profissional_id);
comment on table novo.sessao_treino is
  'Conceitual: SESSÃO DE TREINO (realização do agendamento). Origem: bookings com status presente.';

-- -----------------------------------------------------------------------------
-- LISTA DE ESPERA (fora do conceitual; proposta. Origem vazia: só estrutura)
-- -----------------------------------------------------------------------------
create table novo.lista_espera (
  id             uuid primary key,                -- = waitlist.id
  aluno_id       uuid not null references novo.aluno (id),
  unidade_id     uuid not null references novo.unidade (id),
  servico_id     uuid not null references novo.servico (id),
  data           date not null,
  hora_inicio    time not null,
  solicitante_id uuid references novo.perfil_usuario (usuario_id),
  status         text not null default 'aguardando',
  notificado_em  timestamptz,
  expira_em      timestamptz,
  pendencia      text,
  criado_em      timestamptz not null default now(),
  atualizado_em  timestamptz not null default now()
);
create index lista_espera_aluno_idx       on novo.lista_espera (aluno_id);
create index lista_espera_horario_idx     on novo.lista_espera (unidade_id, servico_id, data, hora_inicio);
create index lista_espera_servico_idx     on novo.lista_espera (servico_id);
create index lista_espera_solicitante_idx on novo.lista_espera (solicitante_id);
comment on table novo.lista_espera is 'Fora do conceitual (proposta). Origem: waitlist (vazia).';

-- -----------------------------------------------------------------------------
-- FEEDBACK (legado) ("avalia": AGENDAMENTO 0,1 — FEEDBACK 1,1)
-- -----------------------------------------------------------------------------
create table novo.feedback_treino (
  id              uuid primary key,               -- = training_feedback.id
  agendamento_id  uuid not null unique references novo.agendamento (id),
  nota_treino     smallint check (nota_treino between 1 and 5),
  nota_professor  smallint check (nota_professor between 1 and 5),
  gostou          text[] not null default '{}',
  comentario      text,
  pulado          boolean not null default false,
  criado_por      uuid references novo.perfil_usuario (usuario_id),
  pendencia       text,
  criado_em       timestamptz not null default now(),
  atualizado_em   timestamptz not null default now()
);
create index feedback_treino_criado_por_idx on novo.feedback_treino (criado_por);
comment on table novo.feedback_treino is
  'Conceitual: FEEDBACK (legado). Origem: training_feedback. O aluno vem do agendamento.';

-- -----------------------------------------------------------------------------
-- Crédito consumido/estornado por agendamento
-- -----------------------------------------------------------------------------
alter table novo.credito_lancamento
  add column agendamento_id uuid references novo.agendamento (id);
create index credito_lancamento_agendamento_idx on novo.credito_lancamento (agendamento_id);

-- -----------------------------------------------------------------------------
-- atualizado_em automático + RLS
-- -----------------------------------------------------------------------------
do $$
declare t text;
begin
  foreach t in array array['horario_grade', 'bloqueio_agenda', 'bloqueio_grade', 'agendamento',
                           'sessao_treino', 'lista_espera', 'feedback_treino']
  loop
    perform novo.instalar_atualizado_em(format('novo.%I', t)::regclass);
    execute format('alter table novo.%I enable row level security', t);
  end loop;
end;
$$;
