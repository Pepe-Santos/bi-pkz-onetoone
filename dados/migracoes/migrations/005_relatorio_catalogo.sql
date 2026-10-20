-- =============================================================================
-- 005_relatorio_catalogo.sql
-- Domínio 3 · Agenda e treino, parte 2: relatório e catálogo
-- (diagrama modelo-conceitual/03-agenda)
-- Dono: Micael (Frente 1). Pré-requisito: 004_agenda.sql.
--
-- Cria: catalogo_item, relatorio_treino, relatorio_item.
--
-- Escolhas:
--   * "documenta": AGENDAMENTO (0,N) — RELATÓRIO (0,1). Há relatórios sem
--     agendamento e agendamentos com até 5 relatórios: NÃO há restrição de um
--     relatório por agendamento (duplicados entram com pendência).
--   * ITEM DE CATÁLOGO substitui as dimensões de texto livre do relatório
--     (materials, technologies, capacidades_*, objetivo_sessao, foco, conduta e
--     os campos *_other). "classificado por" vira relatorio_item.
--   * relatorio_item guarda o texto original de onde o item saiu.
--   * exercicio / relatorio_exercicio (proposta) NÃO foram criados: não estão no
--     conceitual e training_reports.exercicios está vazio em toda a origem.
--     Se o cliente pedir, entram numa migration nova.
--   * Os campos de dor do relatório (dor, dor_local, dor_intensidade,
--     dor_movimento) ficam aqui por enquanto; a Frente 3 decide a política.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- ITEM DE CATÁLOGO
-- -----------------------------------------------------------------------------
create table novo.catalogo_item (
  id            uuid primary key default gen_random_uuid(),
  dominio       text not null check (dominio in ('material', 'tecnologia', 'capacidade_fisica',
                                                 'capacidade_tecnica', 'capacidade_cognitiva',
                                                 'objetivo_sessao', 'foco', 'conduta')),
  codigo        text not null,
  nome          text not null,
  ativo         boolean not null default true,
  ordem         int not null default 0,
  id_origem     uuid,                              -- training_report_materials/technologies.id, quando houver
  pendencia     text,                              -- ex.: 'não classificado'
  criado_em     timestamptz not null default now(),
  atualizado_em timestamptz not null default now(),
  unique (dominio, codigo)
);
comment on table novo.catalogo_item is
  'Conceitual: ITEM DE CATÁLOGO. Origem: training_report_materials, training_report_technologies e valores distintos dos arrays de training_reports.';

-- -----------------------------------------------------------------------------
-- RELATÓRIO DE TREINO
-- -----------------------------------------------------------------------------
create table novo.relatorio_treino (
  id              uuid primary key,               -- = training_reports.id
  aluno_id        uuid not null references novo.aluno (id),
  agendamento_id  uuid references novo.agendamento (id),
  profissional_id uuid references novo.profissional (id),
  unidade_id      uuid not null references novo.unidade (id),
  tipo            text not null check (tipo in ('pkz', 'one_to_one')),   -- report_kind
  status          text not null default 'rascunho' check (status in ('rascunho', 'final')),
  data            date not null,
  hora_inicio     time,
  hora_fim        time,
  titulo          text,
  categoria       text,
  grupo           text,                           -- athlete_group
  local           text,
  tipo_treino     text,
  numero_sessao   int,
  intensidade     text,
  blocos          smallint,
  objetivos       text,
  analise_html    text,
  observacoes     text,
  evolucao        text,
  desempenho      text,
  notas           text,                           -- notes
  dor             text,
  dor_local       text,
  dor_intensidade smallint check (dor_intensidade between 0 and 10),
  dor_movimento   text,
  criado_por      uuid references novo.perfil_usuario (usuario_id),
  pendencia       text,
  criado_em       timestamptz not null default now(),
  atualizado_em   timestamptz not null default now()
);
create index relatorio_treino_aluno_idx        on novo.relatorio_treino (aluno_id, data);
create index relatorio_treino_agendamento_idx  on novo.relatorio_treino (agendamento_id);
create index relatorio_treino_profissional_idx on novo.relatorio_treino (profissional_id);
create index relatorio_treino_unidade_idx      on novo.relatorio_treino (unidade_id);
create index relatorio_treino_criado_por_idx   on novo.relatorio_treino (criado_por);
comment on table novo.relatorio_treino is 'Conceitual: RELATÓRIO. Origem: training_reports.';

-- -----------------------------------------------------------------------------
-- "classificado por": RELATÓRIO N:M ITEM DE CATÁLOGO
-- -----------------------------------------------------------------------------
create table novo.relatorio_item (
  relatorio_id     uuid not null references novo.relatorio_treino (id),
  catalogo_item_id uuid not null references novo.catalogo_item (id),
  texto_original   text,                          -- valor como estava no array / campo *_other
  criado_em        timestamptz not null default now(),
  atualizado_em    timestamptz not null default now(),
  primary key (relatorio_id, catalogo_item_id)
);
create index relatorio_item_item_idx on novo.relatorio_item (catalogo_item_id);
comment on table novo.relatorio_item is 'Conceitual: relacionamento "classificado por".';

-- -----------------------------------------------------------------------------
-- atualizado_em automático + RLS
-- -----------------------------------------------------------------------------
do $$
declare t text;
begin
  foreach t in array array['catalogo_item', 'relatorio_treino', 'relatorio_item']
  loop
    perform novo.instalar_atualizado_em(format('novo.%I', t)::regclass);
    execute format('alter table novo.%I enable row level security', t);
  end loop;
end;
$$;
