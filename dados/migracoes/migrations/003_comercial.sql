-- =============================================================================
-- 003_comercial.sql
-- Domínio 2 · Comercial e créditos (diagrama modelo-conceitual/02-comercial)
-- Dono: Micael (Frente 1). Pré-requisito: 002_fundacao.sql.
--
-- Cria: plano, plano_beneficio, matricula, renovacao, credito_lancamento,
--       views vw_matricula_vigente e vw_saldo_credito,
--       função novo.unidade_atual_do_aluno(aluno_id).
--
-- Escolhas:
--   * MATRÍCULA é a ternária ATLETA × PLANO × UNIDADE, datada (vigencia_inicio/fim).
--     Só uma matrícula vigente (vigencia_fim nula) por aluno.
--   * RENOVAÇÃO é entidade (conceitual) e "gera" lançamentos: credito_lancamento
--     tem renovacao_id. A proposta guardava só origem_tipo/origem_id.
--   * O SALDO é derivado (vw_saldo_credito); não existe coluna de saldo.
--   * credito_lancamento.agendamento_id é criado no 004_agenda (a tabela de
--     agendamento ainda não existe aqui).
--   * matricula.plano_mensal_origem guarda athletes.monthly_plan bruto:
--     significado a confirmar.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- PLANO e "concede" (PLANO N:M SERVIÇO com quantidade e periodicidade)
-- -----------------------------------------------------------------------------
create table novo.plano (
  id            uuid primary key default gen_random_uuid(),
  unidade_id    uuid not null references novo.unidade (id),
  codigo        text not null unique,          -- 'express', 'one_move', ..., 'pkz_padrao'
  nome          text not null,
  ativo         boolean not null default true,
  pendencia     text,
  criado_em     timestamptz not null default now(),
  atualizado_em timestamptz not null default now()
);
create index plano_unidade_idx on novo.plano (unidade_id);
comment on table novo.plano is 'Conceitual: PLANO. Origem: enum one_to_one_plan + plano padrão do PKZ (pendência).';

create table novo.plano_beneficio (
  id            uuid primary key default gen_random_uuid(),
  plano_id      uuid not null references novo.plano (id),
  servico_id    uuid not null references novo.servico (id),
  quantidade    int  not null check (quantidade >= 0),
  periodicidade text not null check (periodicidade in ('semana', 'mes')),
  pendencia     text,
  criado_em     timestamptz not null default now(),
  atualizado_em timestamptz not null default now(),
  unique (plano_id, servico_id, periodicidade)
);
create index plano_beneficio_servico_idx on novo.plano_beneficio (servico_id);
comment on table novo.plano_beneficio is
  'Conceitual: relacionamento "concede". Origem: funções plan_weekly_treino, plan_monthly_fisio, plan_monthly_nutri.';

-- -----------------------------------------------------------------------------
-- MATRÍCULA
-- -----------------------------------------------------------------------------
create table novo.matricula (
  id                        uuid primary key default gen_random_uuid(),
  aluno_id                  uuid not null references novo.aluno (id),
  plano_id                  uuid not null references novo.plano (id),
  unidade_id                uuid not null references novo.unidade (id),
  vigencia_inicio           date not null,
  vigencia_fim              date,                       -- nula = vigente
  duracao_treino_min        int check (duracao_treino_min > 0),
  experimental              boolean not null default false,  -- athletes.is_trial
  renovacao_ativa           boolean not null default false,
  renovacao_dia             int check (renovacao_dia between 1 and 31),
  renovacao_quantidade      int,
  ultima_renovacao_em       timestamptz,
  proxima_renovacao         date,
  proxima_renovacao_semanal date,
  plano_mensal_origem       int,                        -- athletes.monthly_plan, significado a confirmar
  pendencia                 text,
  criado_em                 timestamptz not null default now(),
  atualizado_em             timestamptz not null default now(),
  check (vigencia_fim is null or vigencia_fim >= vigencia_inicio),
  unique (aluno_id, plano_id, vigencia_inicio)          -- chave de reexecução
);
create index matricula_plano_idx   on novo.matricula (plano_id);
create index matricula_unidade_idx on novo.matricula (unidade_id);
create unique index matricula_uma_vigente on novo.matricula (aluno_id) where vigencia_fim is null;
comment on table novo.matricula is
  'Conceitual: relacionamento ternário "matrícula" (ATLETA × PLANO × UNIDADE). Origem: athletes (só a vigente; histórico foi apagado na origem).';

-- -----------------------------------------------------------------------------
-- RENOVAÇÃO
-- -----------------------------------------------------------------------------
create table novo.renovacao (
  id            uuid primary key default gen_random_uuid(),
  aluno_id      uuid not null references novo.aluno (id),
  servico_id    uuid not null references novo.servico (id),
  matricula_id  uuid references novo.matricula (id),
  competencia   date not null,                    -- início do período renovado (semana ou mês)
  periodicidade text check (periodicidade in ('semana', 'mes')),
  executada_em  timestamptz,
  pendencia     text,
  criado_em     timestamptz not null default now(),
  atualizado_em timestamptz not null default now(),
  unique (aluno_id, servico_id, competencia)
);
create index renovacao_servico_idx   on novo.renovacao (servico_id);
create index renovacao_matricula_idx on novo.renovacao (matricula_id);
comment on table novo.renovacao is
  'Conceitual: RENOVAÇÃO. Origem: lançamentos de credit_transactions cujo motivo começa com "Renovação".';

-- -----------------------------------------------------------------------------
-- LANÇAMENTO DE CRÉDITO (extrato; saldo = soma)
-- -----------------------------------------------------------------------------
create table novo.credito_lancamento (
  id            uuid primary key,                 -- = credit_transactions.id
  aluno_id      uuid not null references novo.aluno (id),
  servico_id    uuid not null references novo.servico (id),
  delta         int  not null,
  motivo        text not null,                    -- texto original de reason
  origem_tipo   text not null check (origem_tipo in ('renovacao', 'agendamento', 'estorno', 'ajuste_manual', 'outro')),
  renovacao_id  uuid references novo.renovacao (id),
  ator_id       uuid references novo.perfil_usuario (usuario_id),
  pendencia     text,
  criado_em     timestamptz not null default now(),
  atualizado_em timestamptz not null default now()
);
create index credito_lancamento_aluno_idx     on novo.credito_lancamento (aluno_id, servico_id);
create index credito_lancamento_servico_idx   on novo.credito_lancamento (servico_id);
create index credito_lancamento_renovacao_idx on novo.credito_lancamento (renovacao_id);
create index credito_lancamento_ator_idx      on novo.credito_lancamento (ator_id);
comment on table novo.credito_lancamento is
  'Conceitual: LANÇAMENTO DE CRÉDITO. Origem: credit_transactions (serviço e origem lidos do texto de reason).';

-- -----------------------------------------------------------------------------
-- Views e função de apoio
-- -----------------------------------------------------------------------------
create view novo.vw_matricula_vigente
with (security_invoker = true)
as
select m.*
from novo.matricula m
where m.vigencia_fim is null or m.vigencia_fim >= current_date;
comment on view novo.vw_matricula_vigente is 'Matrículas vigentes hoje.';

create view novo.vw_saldo_credito
with (security_invoker = true)
as
select l.aluno_id, l.servico_id, sum(l.delta)::int as saldo, max(l.criado_em) as ultimo_lancamento_em
from novo.credito_lancamento l
group by l.aluno_id, l.servico_id;
comment on view novo.vw_saldo_credito is 'Saldo de créditos por aluno e serviço (derivado do extrato).';

-- Unidade da matrícula vigente (ou da mais recente, se nenhuma estiver vigente).
-- Útil para scripts de carga e para as políticas de RLS por unidade (Frente 3).
create or replace function novo.unidade_atual_do_aluno(p_aluno_id uuid)
returns uuid
language sql
stable
as $$
  select m.unidade_id
  from novo.matricula m
  where m.aluno_id = p_aluno_id
  order by (m.vigencia_fim is null) desc, m.vigencia_inicio desc
  limit 1;
$$;

-- -----------------------------------------------------------------------------
-- atualizado_em automático + RLS
-- -----------------------------------------------------------------------------
do $$
declare t text;
begin
  foreach t in array array['plano', 'plano_beneficio', 'matricula', 'renovacao', 'credito_lancamento']
  loop
    perform novo.instalar_atualizado_em(format('novo.%I', t)::regclass);
    execute format('alter table novo.%I enable row level security', t);
  end loop;
end;
$$;
