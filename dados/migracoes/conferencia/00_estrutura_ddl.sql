-- =============================================================================
-- conferencia/00_estrutura_ddl.sql
-- Confere as regras do CONVENCOES.md sobre o DDL de novo.
-- Cada consulta deve voltar VAZIA (exceto a última, que é o inventário).
-- As tabelas novo.avulsa_* (ver ensaio/limpar_tabelas_avulsas.sql) ficam de fora.
-- =============================================================================

-- 1) Tabela sem RLS ligado
select c.relname as tabela_sem_rls
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'novo' and c.relkind = 'r' and not c.relrowsecurity
  and c.relname not like 'avulsa\_%';

-- 2) Chave estrangeira sem índice que comece pelas colunas dela
select con.conrelid::regclass as tabela, con.conname as fk_sem_indice
from pg_constraint con
where con.contype = 'f' and con.connamespace = 'novo'::regnamespace
  and con.conrelid::regclass::text not like 'novo.avulsa\_%'
  and not exists (
    select 1 from pg_index i
    where i.indrelid = con.conrelid
      and (i.indkey::int2[])[0:array_length(con.conkey, 1) - 1] = con.conkey
  );

-- 3) Tabela de negócio sem criado_em / atualizado_em, ou sem trigger de atualizado_em
select c.relname as tabela_sem_colunas_padrao
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'novo' and c.relkind = 'r' and c.relname not like 'carga\_%' and c.relname not like 'avulsa\_%'
  and (   not exists (select 1 from information_schema.columns k where k.table_schema = 'novo' and k.table_name = c.relname and k.column_name = 'criado_em')
       or not exists (select 1 from information_schema.columns k where k.table_schema = 'novo' and k.table_name = c.relname and k.column_name = 'atualizado_em')
       or not exists (select 1 from pg_trigger g where g.tgrelid = c.oid and g.tgname = 'tg_atualizado_em'));

-- 4) Tabela sem comentário de origem no modelo conceitual
select c.relname as tabela_sem_comentario
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'novo' and c.relkind = 'r' and c.relname not like 'carga\_%' and c.relname not like 'avulsa\_%'
  and obj_description(c.oid, 'pg_class') is null;

-- 5) Inventário: tabelas e views de novo
select c.relname as objeto, case c.relkind when 'r' then 'tabela' when 'v' then 'view' end as tipo,
       obj_description(c.oid, 'pg_class') as origem
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'novo' and c.relkind in ('r', 'v')
order by c.relkind, c.relname;
