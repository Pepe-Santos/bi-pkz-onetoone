-- =============================================================================
-- ensaio/limpar_tabelas_avulsas.sql
-- Rodado UMA vez no ensaio, em 13/10/2026, antes da migration 002.
--
-- Por quê: em 13/10 o schema novo tinha 4 tabelas criadas fora das migrations
-- (unidade, servico, plano, plano_beneficio), com id bigint e dados de
-- referência (2 unidades, 4 serviços, 5 planos, 12 benefícios). O 002/003
-- recria as quatro no padrão do grupo (uuid, criado_em, pendencia, RLS), e os
-- dados voltam pelo script 10_carga_referencia.
--
-- O que foi feito: RENOMEAR (não apagar) as 4 tabelas e suas restrições,
-- índices e sequências para o prefixo avulsa_, liberando os nomes.
-- Os dados ficaram guardados em novo.avulsa_*.
--
-- Passo 2 (quando o grupo confirmar que não precisa mais delas): rodar o
-- bloco comentado no fim. O conector do Supabase pede confirmação para drop.
-- =============================================================================

-- Passo 1: renomear (executado em 13/10/2026)
alter table novo.unidade         rename to avulsa_unidade;
alter table novo.servico         rename to avulsa_servico;
alter table novo.plano           rename to avulsa_plano;
alter table novo.plano_beneficio rename to avulsa_plano_beneficio;

do $$
declare r record;
begin
  for r in
    select con.conrelid::regclass as tab, con.conname
    from pg_constraint con
    where con.connamespace = 'novo'::regnamespace
      and con.conrelid::regclass::text like 'novo.avulsa\_%'
      and con.conname not like 'avulsa\_%'
  loop
    execute format('alter table %s rename constraint %I to %I', r.tab, r.conname, 'avulsa_' || r.conname);
  end loop;
  for r in
    select c.relname, c.relkind from pg_class c
    where c.relnamespace = 'novo'::regnamespace and c.relkind in ('S', 'i')
      and c.relname not like 'avulsa\_%'
      and c.relname ~ '^(unidade|servico|plano|plano_beneficio)_'
  loop
    execute format('alter %s novo.%I rename to %I',
                   case r.relkind when 'S' then 'sequence' else 'index' end,
                   r.relname, 'avulsa_' || r.relname);
  end loop;
end;
$$;

-- Passo 2 (pendente): apagar as cópias
-- drop table novo.avulsa_plano_beneficio, novo.avulsa_plano, novo.avulsa_servico, novo.avulsa_unidade;
