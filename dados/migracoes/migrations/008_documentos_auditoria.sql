-- =============================================================================
-- 008_documentos_auditoria.sql
-- Domínio 6 · Documentos, conformidade e comunicação
-- (diagrama modelo-conceitual/06-conformidade)
-- Dono: Micael (Frente 1). Pré-requisito: 007_atendimento.sql.
--
-- Cria: arquivo, consentimento, relatorio_emissao, relatorio_envio,
--       notificacao, evento_auditoria, acesso_dado_sensivel,
--       view vw_historico_aluno.
--
-- Escolhas (decididas por Micael em 13/10/2026, seguindo o conceitual):
--   * ARQUIVO "anexado a" ATLETA, RELATÓRIO, AVALIAÇÃO ou ATENDIMENTO, com FKs
--     reais: aluno_id + no máximo um entre relatorio_id, avaliacao_id e
--     atendimento_id. A proposta usava arquivo_vinculo (entidade + id, sem FK).
--     Um caminho = um arquivo (storage_path único). Caminho ligado a alunos
--     diferentes ou a dois "donos" diferentes na origem: rejeitado ou pendência
--     no script 80, nunca escolhido no chute.
--   * HISTÓRICO não é tabela: é a view vw_historico_aluno sobre os fatos
--     (student_timeline não migra).
--   * NOTIFICAÇÃO: só estrutura (pendência 6, proposta: não migrar).
--   * CONSENTIMENTO, EMISSÃO, ENVIO, acesso_dado_sensivel: só estrutura (não
--     existem na origem).
--   * ENVIO é entidade fraca de EMISSÃO, chave parcial = canal (+ destinatário).
--   * Auditoria: chave de reexecução (tabela_origem, id_origem).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- ARQUIVO
-- -----------------------------------------------------------------------------
create table novo.arquivo (
  id                uuid primary key default gen_random_uuid(),
  storage_path      text not null unique,          -- chave de reexecução
  nome              text,
  mime              text,
  bytes             bigint check (bytes >= 0),
  tipo              text,                          -- 'relatorio_treino', 'evolucao', 'fisioterapia', 'extrato', 'teste_fisico', 'nutricao' ...
  confidencialidade text not null default 'normal' check (confidencialidade in ('normal', 'clinico', 'restrito')),
  aluno_id          uuid references novo.aluno (id),
  unidade_id        uuid references novo.unidade (id),
  relatorio_id      uuid references novo.relatorio_treino (id),
  avaliacao_id      uuid references novo.avaliacao (id),
  atendimento_id    uuid references novo.atendimento (id),
  enviado_por       uuid references novo.perfil_usuario (usuario_id),
  pendencia         text,
  criado_em         timestamptz not null default now(),
  atualizado_em     timestamptz not null default now(),
  -- as pontas são exclusivas entre si (o aluno pode acompanhar qualquer uma)
  check (num_nonnulls(relatorio_id, avaliacao_id, atendimento_id) <= 1),
  check (num_nonnulls(aluno_id, relatorio_id, avaliacao_id, atendimento_id) >= 1)
);
create index arquivo_aluno_idx       on novo.arquivo (aluno_id);
create index arquivo_unidade_idx     on novo.arquivo (unidade_id);
create index arquivo_relatorio_idx   on novo.arquivo (relatorio_id);
create index arquivo_avaliacao_idx   on novo.arquivo (avaliacao_id);
create index arquivo_atendimento_idx on novo.arquivo (atendimento_id);
create index arquivo_enviado_por_idx on novo.arquivo (enviado_por);
comment on table novo.arquivo is
  'Conceitual: ARQUIVO (relacionamentos "anexado a"). Origem: 9 colunas de caminho (student_files, nutritionist_files, physio_evolutions, specialist_evolutions, training_reports x2, physical_test_comparisons, physio_assessments, student_tests).';

-- -----------------------------------------------------------------------------
-- CONSENTIMENTO ("concede": PESSOA; "sobre": ATLETA) — só estrutura
-- -----------------------------------------------------------------------------
create table novo.consentimento (
  id            uuid primary key default gen_random_uuid(),
  pessoa_id     uuid not null references novo.pessoa (id),   -- quem concede
  aluno_id      uuid not null references novo.aluno (id),    -- sobre quem
  finalidade    text not null,                 -- 'uso_imagem', 'dado_saude', 'envio_relatorio' ...
  canal         text,                          -- 'app', 'papel', 'whatsapp' ...
  versao_termo  text,
  concedido_em  timestamptz not null,
  revogado_em   timestamptz,
  criado_em     timestamptz not null default now(),
  atualizado_em timestamptz not null default now(),
  check (revogado_em is null or revogado_em >= concedido_em)
);
create index consentimento_pessoa_idx on novo.consentimento (pessoa_id);
create index consentimento_aluno_idx  on novo.consentimento (aluno_id, finalidade);
comment on table novo.consentimento is 'Conceitual: CONSENTIMENTO (LGPD). Não existe na origem: só estrutura.';

-- -----------------------------------------------------------------------------
-- EMISSÃO DE RELATÓRIO e ENVIO — só estrutura
-- -----------------------------------------------------------------------------
create table novo.relatorio_emissao (
  id            uuid primary key default gen_random_uuid(),
  aluno_id      uuid not null references novo.aluno (id),
  tipo          text not null,                 -- 'mensal', 'avaliacao_fisica' ...
  competencia   date not null,
  gerado_em     timestamptz not null default now(),
  gerado_por    uuid references novo.perfil_usuario (usuario_id),
  arquivo_id    uuid references novo.arquivo (id),
  criado_em     timestamptz not null default now(),
  atualizado_em timestamptz not null default now(),
  unique (aluno_id, tipo, competencia)
);
create index relatorio_emissao_gerado_por_idx on novo.relatorio_emissao (gerado_por);
create index relatorio_emissao_arquivo_idx    on novo.relatorio_emissao (arquivo_id);
comment on table novo.relatorio_emissao is 'Conceitual: EMISSÃO DE RELATÓRIO. Não existe na origem: só estrutura.';

create table novo.relatorio_envio (
  emissao_id      uuid not null references novo.relatorio_emissao (id),
  canal           text not null,               -- 'email', 'whatsapp', 'app'
  destinatario_id uuid not null references novo.pessoa (id),
  estado          text not null default 'pendente' check (estado in ('pendente', 'enviado', 'falhou')),
  erro            text,
  enviado_em      timestamptz,
  criado_em       timestamptz not null default now(),
  atualizado_em   timestamptz not null default now(),
  primary key (emissao_id, canal, destinatario_id)
);
create index relatorio_envio_destinatario_idx on novo.relatorio_envio (destinatario_id);
comment on table novo.relatorio_envio is 'Conceitual: ENVIO (entidade fraca de EMISSÃO). Só estrutura.';

-- -----------------------------------------------------------------------------
-- NOTIFICAÇÃO — só estrutura (pendência 6)
-- -----------------------------------------------------------------------------
create table novo.notificacao (
  id            uuid primary key default gen_random_uuid(),
  usuario_id    uuid not null references novo.perfil_usuario (usuario_id),
  tipo          text not null,
  mensagem      text not null,
  lida          boolean not null default false,
  criado_em     timestamptz not null default now(),
  atualizado_em timestamptz not null default now()
);
create index notificacao_usuario_idx on novo.notificacao (usuario_id, lida);
comment on table novo.notificacao is 'Conceitual: NOTIFICAÇÃO. Origem: notifications NÃO migra (pendência 6).';

-- -----------------------------------------------------------------------------
-- AUDITORIA ("executa": USUÁRIO 0,N)
-- -----------------------------------------------------------------------------
create table novo.evento_auditoria (
  id             uuid primary key default gen_random_uuid(),
  ator_id        uuid references novo.perfil_usuario (usuario_id),
  acao           text not null,                -- padronizada: 'book_service', 'send_activation_link' ...
  acao_original  text,                         -- texto da origem quando foi padronizado
  entidade       text,                         -- 'aluno', 'agendamento', 'usuario', 'sistema' ...
  entidade_id    uuid,
  valor_anterior jsonb,
  valor_novo     jsonb,
  unidade_id     uuid references novo.unidade (id),
  ip             inet,
  tabela_origem  text,
  id_origem      uuid,
  pendencia      text,
  criado_em      timestamptz not null default now(),
  atualizado_em  timestamptz not null default now(),
  unique (tabela_origem, id_origem)
);
create index evento_auditoria_ator_idx     on novo.evento_auditoria (ator_id);
create index evento_auditoria_entidade_idx on novo.evento_auditoria (entidade, entidade_id);
create index evento_auditoria_unidade_idx  on novo.evento_auditoria (unidade_id);
create index evento_auditoria_data_idx     on novo.evento_auditoria (criado_em);
comment on table novo.evento_auditoria is 'Conceitual: AUDITORIA. Origem: activity_logs, booking_audit_logs.';

-- -----------------------------------------------------------------------------
-- Acesso a dado sensível (proposta; para a Frente 3) — só estrutura
-- -----------------------------------------------------------------------------
create table novo.acesso_dado_sensivel (
  id            uuid primary key default gen_random_uuid(),
  usuario_id    uuid not null references novo.perfil_usuario (usuario_id),
  aluno_id      uuid references novo.aluno (id),
  entidade      text not null,                 -- 'anamnese', 'arquivo', ...
  entidade_id   uuid,
  finalidade    text,
  acessado_em   timestamptz not null default now(),
  criado_em     timestamptz not null default now(),
  atualizado_em timestamptz not null default now()
);
create index acesso_dado_sensivel_usuario_idx on novo.acesso_dado_sensivel (usuario_id, acessado_em);
create index acesso_dado_sensivel_aluno_idx   on novo.acesso_dado_sensivel (aluno_id);
comment on table novo.acesso_dado_sensivel is 'Fora do conceitual (proposta): registro de leitura de dado clínico. Só estrutura.';

-- -----------------------------------------------------------------------------
-- HISTÓRICO do aluno (substitui student_timeline)
-- -----------------------------------------------------------------------------
create view novo.vw_historico_aluno
with (security_invoker = true)
as
select a.aluno_id, a.criado_em as quando, 'agendamento'::text as tipo_evento,
       'agendamento ' || a.status as descricao, a.id as ref_id, a.criado_por as ator_id
from novo.agendamento a
union all
select r.aluno_id, r.criado_em, 'relatorio_treino', 'relatório ' || r.status, r.id, r.criado_por
from novo.relatorio_treino r
union all
select v.aluno_id, v.criado_em, 'avaliacao', 'avaliação ' || v.tipo, v.id, v.criado_por
from novo.avaliacao v
union all
select t.aluno_id, t.criado_em, 'atendimento', 'atendimento', t.id, t.profissional_id
from novo.atendimento t
union all
select l.aluno_id, l.criado_em, 'credito', l.origem_tipo || ' (' || l.delta || ')', l.id, l.ator_id
from novo.credito_lancamento l
union all
select e.entidade_id, e.criado_em, 'auditoria', e.acao, e.id, e.ator_id
from novo.evento_auditoria e
where e.entidade = 'aluno' and e.entidade_id is not null;
comment on view novo.vw_historico_aluno is
  'Conceitual: HISTÓRICO, derivado dos fatos e da auditoria (substitui student_timeline, que não migra).';

-- -----------------------------------------------------------------------------
-- atualizado_em automático + RLS
-- -----------------------------------------------------------------------------
do $$
declare t text;
begin
  foreach t in array array['arquivo', 'consentimento', 'relatorio_emissao', 'relatorio_envio',
                           'notificacao', 'evento_auditoria', 'acesso_dado_sensivel']
  loop
    perform novo.instalar_atualizado_em(format('novo.%I', t)::regclass);
    execute format('alter table novo.%I enable row level security', t);
  end loop;
end;
$$;
