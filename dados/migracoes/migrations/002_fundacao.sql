-- =============================================================================
-- 002_fundacao.sql
-- Domínio 1 · Cadastro e identidade (diagrama modelo-conceitual/01-cadastro)
-- Dono: Micael (Frente 1). Pré-requisito: 001_infra_carga.sql.
--
-- Cria:
--   funções de apoio   novo.tocar_atualizado_em(), novo.instalar_atualizado_em(tabela)
--   referência         unidade, servico, configuracao_unidade
--   pessoas e acesso   pessoa, perfil_usuario, papel, papel_usuario
--   aluno              aluno, aluno_servico, responsavel_aluno
--   profissional       profissional, profissional_servico
--
-- Escolhas (onde conceitual e proposta divergem, vale o conceitual):
--   * PAPEL é entidade (catálogo) e "exerce" é N:M com atributo `desde`; a proposta
--     tinha o papel como texto em papel_usuario.
--   * O e-mail é do USUÁRIO (perfil_usuario), não da PESSOA. A pessoa tem `cpf`
--     (conceitual); ele NÃO é carregado agora (pendência 4).
--   * ALUNO não tem unidade_id: a unidade vem da MATRÍCULA (ternária e datada,
--     003_comercial). Use novo.unidade_atual_do_aluno(aluno_id), criada no 003.
--   * PROFISSIONAL: id = perfil_usuario.usuario_id = profiles.id (pendência 1,
--     fechada por Micael em 13/10/2026). Sem pessoa_id nem unidade_id próprios:
--     a pessoa vem do perfil e a unidade vem de papel_usuario ("atua em").
--   * SERVIÇO fica aqui (e não no comercial) porque agenda, crédito e atendimento
--     dependem dele. "habilitado em" vira profissional_servico.
--   * configuracao_unidade não está no conceitual: guarda app_settings por unidade.
--   * Chave de reexecução da pessoa: (origem_tabela, origem_id).
--   * Usuários não têm FK para auth.users: o projeto definitivo é outro
--     (pendência 7). O id é o mesmo do login.
-- =============================================================================

create extension if not exists pgcrypto;   -- gen_random_uuid (já vem no Supabase)

-- -----------------------------------------------------------------------------
-- Apoio: atualizado_em automático em qualquer update.
-- -----------------------------------------------------------------------------
create or replace function novo.tocar_atualizado_em()
returns trigger
language plpgsql
as $$
begin
  new.atualizado_em := now();
  return new;
end;
$$;

-- Instala o trigger acima numa tabela. Uso: select novo.instalar_atualizado_em('novo.aluno');
create or replace function novo.instalar_atualizado_em(p_tabela regclass)
returns void
language plpgsql
as $$
begin
  execute format(
    'create or replace trigger tg_atualizado_em before update on %s for each row execute function novo.tocar_atualizado_em()',
    p_tabela);
end;
$$;

-- -----------------------------------------------------------------------------
-- UNIDADE
-- -----------------------------------------------------------------------------
create table novo.unidade (
  id            uuid primary key default gen_random_uuid(),
  codigo        text not null unique,            -- 'pkz', 'one_to_one'
  nome          text not null,
  endereco      text,
  ativo         boolean not null default true,
  criado_em     timestamptz not null default now(),
  atualizado_em timestamptz not null default now()
);
comment on table novo.unidade is 'Conceitual: UNIDADE. Origem: enum student_program.';

-- -----------------------------------------------------------------------------
-- SERVIÇO
-- -----------------------------------------------------------------------------
create table novo.servico (
  id            uuid primary key default gen_random_uuid(),
  codigo        text not null unique,            -- 'treino', 'fisioterapia', 'nutricao', 'psicologia'
  nome          text not null,
  especializado boolean not null default false,  -- true = atendimento especializado (fisio, nutri, psico)
  ativo         boolean not null default true,
  ordem         int not null default 0,
  criado_em     timestamptz not null default now(),
  atualizado_em timestamptz not null default now()
);
comment on table novo.servico is 'Conceitual: SERVIÇO. Origem: enum service_type.';

-- -----------------------------------------------------------------------------
-- CONFIGURAÇÃO POR UNIDADE (app_settings)
-- -----------------------------------------------------------------------------
create table novo.configuracao_unidade (
  unidade_id                   uuid primary key references novo.unidade (id),
  prazo_cancelamento_horas     int  not null,
  capacidade_padrao            int  not null check (capacidade_padrao > 0),
  limite_credito_baixo         int  not null,
  creditos_mensais             int  not null,
  renovacao_dia                int  not null check (renovacao_dia between 1 and 31),
  renovacao_dia_semana         int  not null check (renovacao_dia_semana between 0 and 7),  -- 0 ou 7 = domingo (convenção do app a confirmar)
  renovacao_ativa              boolean not null,
  ultima_renovacao_em          timestamptz,
  espera_aceite_horas          int  not null,
  liberacao_automatica         boolean not null,
  liberacao_intervalo_min      int  not null,
  contato_endereco             text,
  contato_instagram            text,
  contato_telefone             text,
  contato_site                 text,
  pendencia                    text,
  criado_em                    timestamptz not null default now(),
  atualizado_em                timestamptz not null default now()
);
comment on table novo.configuracao_unidade is
  'Fora do conceitual (parâmetro operacional). Origem: app_settings (1 linha, copiada para as duas unidades com pendência).';

-- -----------------------------------------------------------------------------
-- PESSOA
-- -----------------------------------------------------------------------------
create table novo.pessoa (
  id              uuid primary key default gen_random_uuid(),
  nome            text not null,
  data_nascimento date,
  cpf             text unique,                    -- conceitual; não carregado (pendência 4)
  telefone        text,
  foto_url        text,
  origem_tabela   text,                           -- chave de reexecução: de onde a pessoa veio
  origem_id       uuid,
  pendencia       text,
  criado_em       timestamptz not null default now(),
  atualizado_em   timestamptz not null default now(),
  unique (origem_tabela, origem_id)
);
comment on table novo.pessoa is
  'Conceitual: PESSOA. Origem: athletes (alunos), profiles (usuários), responsavel_secundario_* (texto).';

-- -----------------------------------------------------------------------------
-- USUÁRIO (perfil de login)
-- -----------------------------------------------------------------------------
create table novo.perfil_usuario (
  usuario_id    uuid primary key,                 -- = id do login (profiles.id / auth.users.id)
  pessoa_id     uuid not null unique references novo.pessoa (id),   -- PESSOA (0,1) acessa USUÁRIO (1,1)
  username      text not null unique,
  email         text,
  status        text not null default 'ativo',
  ativo         boolean not null default true,
  trocar_senha  boolean not null default false,
  pode_agendar  boolean not null default false,
  pode_treinar  boolean not null default false,
  pendencia     text,
  criado_em     timestamptz not null default now(),
  atualizado_em timestamptz not null default now()
);
comment on table novo.perfil_usuario is 'Conceitual: USUÁRIO. Origem: profiles.';

-- -----------------------------------------------------------------------------
-- PAPEL e "exerce" (USUÁRIO N:M PAPEL, "atua em" UNIDADE)
-- -----------------------------------------------------------------------------
create table novo.papel (
  id            uuid primary key default gen_random_uuid(),
  codigo        text not null unique,             -- 'admin', 'professor', 'especialista', 'responsavel', ...
  nome          text not null,
  ativo         boolean not null default true,
  criado_em     timestamptz not null default now(),
  atualizado_em timestamptz not null default now()
);
comment on table novo.papel is 'Conceitual: PAPEL. Origem: enum app_role (9 valores -> catálogo menor).';

create table novo.papel_usuario (
  id            uuid primary key default gen_random_uuid(),
  usuario_id    uuid not null references novo.perfil_usuario (usuario_id),
  papel_id      uuid not null references novo.papel (id),
  unidade_id    uuid references novo.unidade (id), -- nulo = vale para todas as unidades
  desde         date,
  papel_origem  text,                              -- valor do enum app_role, para conferência
  pendencia     text,
  criado_em     timestamptz not null default now(),
  atualizado_em timestamptz not null default now(),
  unique nulls not distinct (usuario_id, papel_id, unidade_id)
);
create index papel_usuario_papel_idx   on novo.papel_usuario (papel_id);
create index papel_usuario_unidade_idx on novo.papel_usuario (unidade_id);
comment on table novo.papel_usuario is 'Conceitual: relacionamentos "exerce" e "atua em". Origem: user_roles.';

-- -----------------------------------------------------------------------------
-- ALUNO (ATLETA)
-- -----------------------------------------------------------------------------
create table novo.aluno (
  id                 uuid primary key,             -- = athletes.id
  pessoa_id          uuid not null unique references novo.pessoa (id),   -- PESSOA (0,1) é ATLETA (1,1)
  status             text not null default 'ativo' check (status in ('ativo', 'inativo', 'bloqueado')),
  data_entrada       date,
  data_saida         date,
  categoria          text,                         -- normalizada
  categoria_original text,                         -- como estava na origem
  observacao         text,
  pendencia          text,
  criado_em          timestamptz not null default now(),
  atualizado_em      timestamptz not null default now(),
  check (data_saida is null or data_entrada is null or data_saida >= data_entrada)
);
comment on table novo.aluno is
  'Conceitual: ATLETA. Origem: athletes. A unidade vem da matrícula (003_comercial).';

-- Serviços que o aluno pode agendar (athletes.allowed_services).
create table novo.aluno_servico (
  aluno_id      uuid not null references novo.aluno (id),
  servico_id    uuid not null references novo.servico (id),
  criado_em     timestamptz not null default now(),
  atualizado_em timestamptz not null default now(),
  primary key (aluno_id, servico_id)
);
create index aluno_servico_servico_idx on novo.aluno_servico (servico_id);
comment on table novo.aluno_servico is
  'Fora do conceitual (regra operacional). Origem: athletes.allowed_services (array normalizado).';

-- "responde por": PESSOA (0,N) N:M ATLETA (1,N)
create table novo.responsavel_aluno (
  aluno_id      uuid not null references novo.aluno (id),
  pessoa_id     uuid not null references novo.pessoa (id),
  tipo_vinculo  text not null default 'responsavel', -- 'responsavel', 'proprio' (adulto que responde por si) ...
  principal     boolean not null default false,
  pode_agendar  boolean not null default true,
  pendencia     text,
  criado_em     timestamptz not null default now(),
  atualizado_em timestamptz not null default now(),
  primary key (aluno_id, pessoa_id)
);
create index responsavel_aluno_pessoa_idx on novo.responsavel_aluno (pessoa_id);
create unique index responsavel_aluno_um_principal on novo.responsavel_aluno (aluno_id) where principal;
comment on table novo.responsavel_aluno is
  'Conceitual: relacionamento "responde por" (deixou de ser entidade). Origem: athletes.responsavel_id e responsavel_secundario_*.';

-- -----------------------------------------------------------------------------
-- PROFISSIONAL
-- -----------------------------------------------------------------------------
create table novo.profissional (
  id                uuid primary key references novo.perfil_usuario (usuario_id),  -- = profiles.id (pendência 1)
  registro_conselho text,
  especialidade     text,
  ativo             boolean not null default true,
  pendencia         text,
  criado_em         timestamptz not null default now(),
  atualizado_em     timestamptz not null default now()
);
comment on table novo.profissional is
  'Conceitual: PROFISSIONAL. Origem: profiles com papel de professor ou especialista. id = profiles.id.';

-- "habilitado em": PROFISSIONAL (1,N) N:M SERVIÇO (1,N)
create table novo.profissional_servico (
  profissional_id uuid not null references novo.profissional (id),
  servico_id      uuid not null references novo.servico (id),
  criado_em       timestamptz not null default now(),
  atualizado_em   timestamptz not null default now(),
  primary key (profissional_id, servico_id)
);
create index profissional_servico_servico_idx on novo.profissional_servico (servico_id);
comment on table novo.profissional_servico is 'Conceitual: relacionamento "habilitado em". Origem: user_roles.';

-- -----------------------------------------------------------------------------
-- atualizado_em automático + RLS (sem políticas: Frente 3)
-- -----------------------------------------------------------------------------
do $$
declare t text;
begin
  foreach t in array array['unidade', 'servico', 'configuracao_unidade', 'pessoa', 'perfil_usuario',
                           'papel', 'papel_usuario', 'aluno', 'aluno_servico', 'responsavel_aluno',
                           'profissional', 'profissional_servico']
  loop
    perform novo.instalar_atualizado_em(format('novo.%I', t)::regclass);
    execute format('alter table novo.%I enable row level security', t);
  end loop;
end;
$$;
