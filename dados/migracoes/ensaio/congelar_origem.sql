-- =============================================================================
-- ensaio/congelar_origem.sql
-- Tira uma "foto" das tabelas de public para o schema origem.
--
-- Por quê: a cópia do banco continua mudando (rotinas automáticas de renovação
-- de créditos rodam todo dia às 00:00 e 00:15 de Brasília e mexem em athletes,
-- credit_transactions, notifications e student_timeline). Os scripts de carga
-- leem de origem, que fica parado; a conferência compara com o gabarito
-- registrado aqui.
--
-- O que faz, numa transação só (todas as tabelas no mesmo instante):
--   1. cria o schema origem com uma cópia de cada tabela de public
--      (colunas, defaults, checks, PK/unique e índices; sem FKs nem triggers);
--   2. liga RLS e tira qualquer acesso de anon/authenticated;
--   3. registra o gabarito com o rótulo 'congelamento-AAAA-MM-DD'.
--
-- Se origem já existir, NÃO faz nada (foto é foto). Para tirar outra foto:
--   drop schema origem cascade;   -- e rodar este arquivo de novo
-- Pré-requisito: migrations/001_infra_carga.sql aplicado.
-- Não grava nada em public.
-- =============================================================================
do $$
declare
  r      record;
  rotulo text := 'congelamento-' || to_char(now() at time zone 'America/Sao_Paulo', 'YYYY-MM-DD');
begin
  if exists (select 1 from pg_namespace where nspname = 'origem') then
    raise notice 'Schema origem já existe: nada foi feito. Para refazer a foto: drop schema origem cascade;';
    return;
  end if;

  create schema origem;
  revoke all on schema origem from public;

  for r in
    select table_name
    from information_schema.tables
    where table_schema = 'public' and table_type = 'BASE TABLE'
    order by table_name
  loop
    execute format(
      'create table origem.%1$I (like public.%1$I including defaults including constraints including indexes)',
      r.table_name);
    execute format('insert into origem.%1$I select * from public.%1$I', r.table_name);
    execute format('alter table origem.%I enable row level security', r.table_name);
    execute format('revoke all on origem.%I from public', r.table_name);
    if exists (select 1 from pg_roles where rolname = 'anon') then
      execute format('revoke all on origem.%I from anon, authenticated', r.table_name);
    end if;
  end loop;

  comment on schema origem is
    'Foto congelada de public para os scripts de carga do Projeto BI. Somente leitura por convenção.';

  perform novo.registrar_gabarito(rotulo, 'origem');
  raise notice 'Origem congelada. Gabarito: %', rotulo;
end;
$$;

-- Conferência rápida da foto
select tabela, linhas, registrado_em
from novo.carga_gabarito
where rotulo = (select max(rotulo) from novo.carga_gabarito)
order by tabela;
