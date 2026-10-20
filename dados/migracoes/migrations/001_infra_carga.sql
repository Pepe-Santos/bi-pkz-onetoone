-- =============================================================================
-- 001_infra_carga.sql
-- Infraestrutura de carga, usada por todos os scripts em carga/.
-- Dono: Micael (padrão técnico). Mudanças aqui são combinadas com o grupo.
--
-- O que cria:
--   novo.carga_execucao   uma linha por execução de script (o "recibo" da carga)
--   novo.carga_rejeitado  registros da origem que não entraram, com o motivo
--   novo.carga_gabarito   contagens da origem no momento do congelamento
--   novo.registrar_gabarito(rotulo)  grava as contagens do schema origem
--   novo.juntar_pendencia(a, b)    soma uma pendência nova às que já existem
--   novo.texto_para_numero(t)      '12,50' -> 12.50 (nulo se não for número)
--   novo.mmss_para_segundos(t)     '03:25' -> 205   (nulo se não for mm:ss)
--   novo.v_resumo_carga            última execução de cada script
--
-- Pode rodar de novo sem erro (if not exists / create or replace).
-- =============================================================================

create schema if not exists novo;

-- -----------------------------------------------------------------------------
-- Registro das execuções
-- `script` é o nome do domínio, sem número: 'referencia', 'cadastro',
-- 'comercial', 'agenda', 'relatorio', 'avaliacao', 'atendimento', 'documentos'.
-- -----------------------------------------------------------------------------
create table if not exists novo.carga_execucao (
  id                bigint generated always as identity primary key,
  script            text not null,
  linhas_carregadas int,
  linhas_rejeitadas int,
  observacao        text,                 -- opcional: algo que valha registrar
  executado_em      timestamptz not null default now()
);

create index if not exists carga_execucao_script_idx
  on novo.carga_execucao (script, executado_em desc);

-- -----------------------------------------------------------------------------
-- Rejeitados: o que não entrou e por quê.
-- Cada script apaga os próprios rejeitados no início (where script = '<nome>'),
-- então rodar de novo não acumula linhas repetidas.
-- -----------------------------------------------------------------------------
create table if not exists novo.carga_rejeitado (
  id            bigint generated always as identity primary key,
  script        text not null,
  tabela_origem text not null,
  id_origem     uuid,
  motivo        text not null,
  registrado_em timestamptz not null default now()
);

create index if not exists carga_rejeitado_script_idx
  on novo.carga_rejeitado (script, tabela_origem);

-- -----------------------------------------------------------------------------
-- Gabarito: contagens da origem congelada.
-- A conferência compara com estes números, nunca com números de documentos
-- antigos (a cópia do banco continua mudando).
-- -----------------------------------------------------------------------------
create table if not exists novo.carga_gabarito (
  rotulo        text not null,            -- ex.: 'congelamento-2026-10-13'
  tabela        text not null,            -- tabela do schema origem
  linhas        bigint not null,
  registrado_em timestamptz not null default now(),
  primary key (rotulo, tabela)
);

-- Conta todas as tabelas do schema informado (padrão: origem, a foto congelada)
-- e grava com o rótulo informado.
-- Um rótulo que já existe NÃO é sobrescrito: o gabarito é uma foto.
-- Para tirar outra foto, use outro rótulo.
create or replace function novo.registrar_gabarito(p_rotulo text, p_schema text default 'origem')
returns int
language plpgsql
as $$
declare
  r      record;
  n      bigint;
  gravou int := 0;
begin
  if exists (select 1 from novo.carga_gabarito where rotulo = p_rotulo) then
    raise exception 'O gabarito "%" já existe. Use outro rótulo.', p_rotulo;
  end if;

  for r in
    select table_name
    from information_schema.tables
    where table_schema = p_schema and table_type = 'BASE TABLE'
    order by table_name
  loop
    execute format('select count(*) from %I.%I', p_schema, r.table_name) into n;
    insert into novo.carga_gabarito (rotulo, tabela, linhas)
    values (p_rotulo, r.table_name, n);
    gravou := gravou + 1;
  end loop;

  return gravou;
end;
$$;

-- -----------------------------------------------------------------------------
-- Pendência: texto livre, várias separadas por '; '. Nunca bloqueia a carga.
-- Uso: pendencia = novo.juntar_pendencia(pendencia, 'unidade ambígua')
-- Não repete uma pendência que já está lá (seguro para rodar de novo).
-- -----------------------------------------------------------------------------
create or replace function novo.juntar_pendencia(p_atual text, p_nova text)
returns text
language sql
immutable
as $$
  select case
    when p_nova is null or p_nova = '' then p_atual
    when p_atual is null or p_atual = '' then p_nova
    when p_nova = any (string_to_array(p_atual, '; ')) then p_atual
    else p_atual || '; ' || p_nova
  end;
$$;

-- -----------------------------------------------------------------------------
-- Conversões usadas na leitura dos JSON do app (valores gravados como texto).
-- Devolvem nulo quando o texto não está no formato: o script decide o que
-- fazer com o nulo (normalmente: guardar o texto original + pendência).
-- -----------------------------------------------------------------------------

-- '12,50' ou '12.50' ou '12' -> numeric. Aceita espaços nas pontas.
create or replace function novo.texto_para_numero(p text)
returns numeric
language sql
immutable
as $$
  select case
    when btrim(p) ~ '^-?\d+([.,]\d+)?$' then replace(btrim(p), ',', '.')::numeric
  end;
$$;

-- 'mm:ss' -> segundos (int). Ex.: '03:25' -> 205. Segundos precisam ter 2 dígitos.
create or replace function novo.mmss_para_segundos(p text)
returns int
language sql
immutable
as $$
  select case
    when btrim(p) ~ '^\d+:[0-5]\d$'
      then split_part(btrim(p), ':', 1)::int * 60 + split_part(btrim(p), ':', 2)::int
  end;
$$;

-- -----------------------------------------------------------------------------
-- Modo de carga.
-- Os scripts ligam o modo logo depois do `begin`:
--     select set_config('novo.modo_carga', 'on', true);  -- vale só nesta transação
-- Triggers de regra de negócio (ex.: avaliação consolidada não pode mudar)
-- consultam novo.em_modo_carga() e deixam a carga passar. Assim o
-- `on conflict do update` funciona na reexecução, sem desligar trigger nenhum
-- e sem afetar quem usa o banco ao mesmo tempo.
-- -----------------------------------------------------------------------------
create or replace function novo.em_modo_carga()
returns boolean
language sql
stable
as $$
  select coalesce(current_setting('novo.modo_carga', true), '') = 'on';
$$;

-- -----------------------------------------------------------------------------
-- Resumo: a última execução de cada script, na ordem da carga.
-- O script mestre (99) termina com: select * from novo.v_resumo_carga;
-- -----------------------------------------------------------------------------
create or replace view novo.v_resumo_carga
with (security_invoker = true)   -- a view respeita o RLS de quem consulta
as
select u.*
from (
  select distinct on (e.script)
         case e.script
           when 'referencia'  then 10 when 'cadastro'    then 20
           when 'comercial'   then 30 when 'agenda'      then 40
           when 'relatorio'   then 50 when 'avaliacao'   then 60
           when 'atendimento' then 70 when 'documentos'  then 80
           else 99
         end as ordem,
         e.script,
         e.linhas_carregadas,
         e.linhas_rejeitadas,
         e.observacao,
         e.executado_em
  from novo.carga_execucao e
  order by e.script, e.executado_em desc, e.id desc   -- id desempata execuções na mesma transação
) u
order by u.ordem;

-- -----------------------------------------------------------------------------
-- Segurança: nada nasce aberto. RLS ligado e nenhuma política = ninguém pela
-- API lê ou grava. Os scripts rodam como dono (postgres) e não são afetados.
-- -----------------------------------------------------------------------------
revoke all on schema novo from public;   -- anon/authenticated nem enxergam o schema
alter table novo.carga_execucao  enable row level security;
alter table novo.carga_rejeitado enable row level security;
alter table novo.carga_gabarito  enable row level security;
