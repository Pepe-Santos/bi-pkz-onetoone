-- =============================================================================
-- 006_avaliacao.sql
-- Domínio 4 · Avaliação e testes físicos (diagrama modelo-conceitual/04-avaliacao)
-- Dono: Micael (Frente 1). Pré-requisito: 005_relatorio_catalogo.sql.
--
-- Cria: metrica, avaliacao, avaliacao_medida, trigger de imutabilidade.
--
-- Escolhas:
--   * A especialização AVALIAÇÃO -> {FÍSICA, SEMANAL} (total, disjunta) vira uma
--     tabela só com a coluna `tipo`; as subclasses não têm atributos próprios.
--     O tipo 'fisioterapia' (physio_assessments) não está no conceitual: entra
--     porque as medidas de goniometria são MEDIDAs de uma avaliação.
--   * MEDIDA é entidade fraca: a chave é (avaliacao, métrica, lado, tentativa).
--   * Avaliação `consolidada` não pode ser alterada nem apagada (nem suas
--     medidas). Correção = nova avaliação com corrige_avaliacao_id.
--     Exceção: modo de carga (novo.em_modo_carga()).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- MÉTRICA
-- -----------------------------------------------------------------------------
create table novo.metrica (
  id                uuid primary key default gen_random_uuid(),
  codigo            text not null unique,          -- 'sprint_10', 'fisio_joelho_flex', 'semanal_ambiente' ...
  nome              text not null,
  dominio           text not null check (dominio in ('teste_fisico', 'antropometria', 'fisioterapia', 'semanal')),
  unidade_medida    text,                          -- 'cm', 's', 'kg', 'graus', 'escala_1_5' ...
  tipo_dado         text not null default 'numero' check (tipo_dado in ('numero', 'texto', 'escala')),
  direcao_desejada  text check (direcao_desejada in ('maior', 'menor', 'nenhuma')),
  valor_min         numeric,                       -- faixa plausível
  valor_max         numeric,
  usa_lado          boolean not null default false,
  ativo             boolean not null default true,
  ordem             int not null default 0,
  pendencia         text,
  criado_em         timestamptz not null default now(),
  atualizado_em     timestamptz not null default now(),
  check (valor_min is null or valor_max is null or valor_max >= valor_min)
);
comment on table novo.metrica is
  'Conceitual: MÉTRICA. Origem: catálogo do app (src/lib/physical-test-schema.ts) e colunas de physio_assessments / weekly_evaluations.';

-- -----------------------------------------------------------------------------
-- AVALIAÇÃO ("realiza": ATLETA 1:N; "aplica": PROFISSIONAL 0,N)
-- -----------------------------------------------------------------------------
create table novo.avaliacao (
  id                   uuid primary key,          -- = physical_test_sessions.id / physio_assessments.id / weekly_evaluations.id
  aluno_id             uuid not null references novo.aluno (id),
  unidade_id           uuid not null references novo.unidade (id),
  tipo                 text not null check (tipo in ('teste_fisico', 'fisioterapia', 'semanal')),
  data                 date not null,
  avaliador_id         uuid references novo.profissional (id),
  avaliador_nome       text,                       -- nome digitado na origem quando não há avaliador_id
  status               text not null default 'rascunho' check (status in ('rascunho', 'consolidada')),
  consolidada_em       timestamptz,
  corrige_avaliacao_id uuid references novo.avaliacao (id),
  observacoes          text,
  criado_por           uuid references novo.perfil_usuario (usuario_id),
  pendencia            text,
  criado_em            timestamptz not null default now(),
  atualizado_em        timestamptz not null default now(),
  check (status <> 'consolidada' or consolidada_em is not null),
  check (corrige_avaliacao_id is null or corrige_avaliacao_id <> id)
);
create index avaliacao_aluno_idx      on novo.avaliacao (aluno_id, tipo, data);
create index avaliacao_unidade_idx    on novo.avaliacao (unidade_id);
create index avaliacao_avaliador_idx  on novo.avaliacao (avaliador_id);
create index avaliacao_corrige_idx    on novo.avaliacao (corrige_avaliacao_id);
create index avaliacao_criado_por_idx on novo.avaliacao (criado_por);
comment on table novo.avaliacao is
  'Conceitual: AVALIAÇÃO (especializações FÍSICA e SEMANAL em `tipo`). Origem: physical_test_sessions, physio_assessments, weekly_evaluations.';

-- -----------------------------------------------------------------------------
-- MEDIDA (entidade fraca; "registra" e "refere-se a")
-- -----------------------------------------------------------------------------
create table novo.avaliacao_medida (
  id            uuid primary key default gen_random_uuid(),
  avaliacao_id  uuid not null references novo.avaliacao (id),
  metrica_id    uuid not null references novo.metrica (id),
  lado          text check (lado in ('dir', 'esq')),
  tentativa     smallint not null default 1 check (tentativa >= 1),
  valor_num     numeric,
  valor_texto   text,                             -- valor que não converteu (formato antigo etc.)
  pendencia     text,
  criado_em     timestamptz not null default now(),
  atualizado_em timestamptz not null default now(),
  check (valor_num is not null or valor_texto is not null),
  unique nulls not distinct (avaliacao_id, metrica_id, lado, tentativa)
);
create index avaliacao_medida_metrica_idx on novo.avaliacao_medida (metrica_id);
comment on table novo.avaliacao_medida is
  'Conceitual: MEDIDA (entidade fraca de AVALIAÇÃO). Origem: physical_test_sessions.data (jsonb), altura/peso, colunas numéricas de physio_assessments, notas de weekly_evaluations.';

-- -----------------------------------------------------------------------------
-- Imutabilidade da avaliação consolidada
-- -----------------------------------------------------------------------------
create or replace function novo.proteger_avaliacao_consolidada()
returns trigger
language plpgsql
as $$
begin
  if novo.em_modo_carga() then
    return coalesce(new, old);
  end if;
  if old.status = 'consolidada' then
    raise exception 'Avaliação % está consolidada e não pode ser %. Para corrigir, crie uma nova com corrige_avaliacao_id.',
      old.id, case tg_op when 'DELETE' then 'apagada' else 'alterada' end
      using errcode = 'check_violation';
  end if;
  return coalesce(new, old);
end;
$$;

create trigger tg_imutavel
before update or delete on novo.avaliacao
for each row execute function novo.proteger_avaliacao_consolidada();

create or replace function novo.proteger_medida_consolidada()
returns trigger
language plpgsql
as $$
declare
  v_ids uuid[];
begin
  if novo.em_modo_carga() then
    return coalesce(new, old);
  end if;
  v_ids := case tg_op
             when 'INSERT' then array[new.avaliacao_id]
             when 'DELETE' then array[old.avaliacao_id]
             else array[old.avaliacao_id, new.avaliacao_id]
           end;
  if exists (select 1 from novo.avaliacao a where a.id = any (v_ids) and a.status = 'consolidada') then
    raise exception 'A avaliação está consolidada: suas medidas não podem ser incluídas, alteradas nem apagadas.'
      using errcode = 'check_violation';
  end if;
  return coalesce(new, old);
end;
$$;

create trigger tg_imutavel
before insert or update or delete on novo.avaliacao_medida
for each row execute function novo.proteger_medida_consolidada();

-- -----------------------------------------------------------------------------
-- atualizado_em automático + RLS
-- -----------------------------------------------------------------------------
do $$
declare t text;
begin
  foreach t in array array['metrica', 'avaliacao', 'avaliacao_medida']
  loop
    perform novo.instalar_atualizado_em(format('novo.%I', t)::regclass);
    execute format('alter table novo.%I enable row level security', t);
  end loop;
end;
$$;
