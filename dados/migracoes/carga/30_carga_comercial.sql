-- =============================================================================
-- 30_carga_comercial.sql
-- Domínio: comercial               Dono: Micael (Frente 1)
-- Origem:  origem.athletes (matrícula vigente e saldos, só para conferir: créditos
--          não são cumulativos, ver migration 011),
--          origem.credit_transactions (extrato)
-- Destino: novo.matricula, novo.renovacao, novo.credito_lancamento
-- Depende de: migrations 001–011; scripts 10 e 20
-- Mapeamento: mapeamento/comercial.csv
-- =============================================================================
\set ON_ERROR_STOP on

begin;

select set_config('novo.modo_carga', 'on', true);

-- Saldo ("bucket") de onde o crédito sai, lido do texto de reason.
-- O colchete no fim manda; sem colchete, a palavra fisio/nutri; o resto é treino.
create or replace function pg_temp.bucket(r text) returns text language sql immutable as $$
  select case
    when r ~ '\[treino\]\s*$' then 'treino'
    when r ~ '\[fisio\]\s*$'  then 'fisioterapia'
    when r ~ '\[nutri\]\s*$'  then 'nutricao'
    when r ~* 'fisio'         then 'fisioterapia'
    when r ~* 'nutri'         then 'nutricao'
    else 'treino'
  end;
$$;

-- Lançamentos da origem já com serviço, tipo e pendências calculados.
create temporary table tmp_lanc on commit drop as
select t.id, t.athlete_id, t.delta, t.reason, t.actor_id, t.created_at,
       pg_temp.bucket(t.reason) as servico,
       case
         when t.reason ~ '^Renovação'                       then 'renovacao'
         when t.reason ~ '^(Agendamento|Solicitação)'       then 'agendamento'
         when t.reason ~ '^Cancelamento'                    then 'estorno'
         when t.reason ~ '^(Adição|Remoção|Ajuste) manual'  then 'ajuste_manual'
         else 'outro'
       end as origem_tipo,
       case when t.reason ~* 'semanal' then 'semana' when t.reason ~* 'mensal' then 'mes' end as periodicidade,
       (t.reason ~ '\[(treino|fisio|nutri)\]\s*$') as tem_colchete,
       case when t.reason ~* 'fisioterapeuta' then 'fisioterapia'
            when t.reason ~* 'nutricionista'  then 'nutricao'
            when t.reason ~* 'psicolog'       then 'psicologia' end as servico_citado
from origem.credit_transactions t;

-- -----------------------------------------------------------------------------
-- b) Rejeitados
-- -----------------------------------------------------------------------------
insert into novo.carga_rejeitado (script, tabela_origem, id_origem, motivo)
select 'comercial', 'credit_transactions', l.id, 'aluno inexistente no destino'
from tmp_lanc l
where not exists (select 1 from novo.aluno a where a.id = l.athlete_id)
on conflict (script, tabela_origem, id_origem, motivo) do nothing;

insert into novo.carga_rejeitado (script, tabela_origem, id_origem, motivo)
select 'comercial', 'athletes', a.id, 'aluno inexistente no destino: matrícula não criada'
from origem.athletes a
where not exists (select 1 from novo.aluno al where al.id = a.id)
on conflict (script, tabela_origem, id_origem, motivo) do nothing;

-- -----------------------------------------------------------------------------
-- c1) matricula: só a vigente (a origem não guarda histórico)
-- -----------------------------------------------------------------------------
insert into novo.matricula as m (
  aluno_id, plano_id, unidade_id, vigencia_inicio, duracao_treino_min, experimental,
  renovacao_ativa, renovacao_dia, renovacao_quantidade, ultima_renovacao_em,
  proxima_renovacao, proxima_renovacao_semanal, plano_mensal_origem, pendencia, criado_em)
select a.id, p.id, u.id,
       (a.created_at at time zone 'America/Sao_Paulo')::date,
       a.training_duration_min, a.is_trial,
       a.auto_renew_enabled, a.auto_renew_day, a.auto_renew_amount, a.last_renewed_at,
       a.next_renewal_date, a.next_weekly_renewal, a.monthly_plan,
       novo.juntar_pendencia(
         novo.juntar_pendencia('início aproximado (= criação do cadastro)',
           case when a.program = 'one_to_one' and a.plan is null then 'aluno One to One sem plano na origem' end),
         case when a.monthly_plan <> 0 then 'significado de monthly_plan a confirmar' end),
       a.created_at
from origem.athletes a
join novo.aluno al on al.id = a.id
join novo.unidade u on u.codigo = a.program::text
join novo.plano p on p.codigo = case
       when a.program = 'pkz' then 'pkz_padrao'
       when a.plan is null    then 'one_to_one_sem_plano'
       else a.plan::text end
on conflict (aluno_id, plano_id, vigencia_inicio) do update
  set unidade_id = excluded.unidade_id, duracao_treino_min = excluded.duracao_treino_min,
      experimental = excluded.experimental, renovacao_ativa = excluded.renovacao_ativa,
      renovacao_dia = excluded.renovacao_dia, renovacao_quantidade = excluded.renovacao_quantidade,
      ultima_renovacao_em = excluded.ultima_renovacao_em, proxima_renovacao = excluded.proxima_renovacao,
      proxima_renovacao_semanal = excluded.proxima_renovacao_semanal,
      plano_mensal_origem = excluded.plano_mensal_origem,
      pendencia = novo.juntar_pendencia(m.pendencia, excluded.pendencia),
      criado_em = excluded.criado_em, atualizado_em = now();

-- -----------------------------------------------------------------------------
-- c2) renovacao: um registro por (aluno, serviço, periodicidade, competência)
-- -----------------------------------------------------------------------------
insert into novo.renovacao as r (aluno_id, servico_id, matricula_id, competencia, periodicidade,
                                 executada_em, pendencia, criado_em)
select g.athlete_id, s.id,
       (select m.id from novo.matricula m where m.aluno_id = g.athlete_id and m.vigencia_fim is null),
       g.competencia, g.periodicidade, g.primeiro,
       case when g.n > 1 then 'mais de um lançamento de renovação na mesma competência' end,
       g.primeiro
from (
  select l.athlete_id, l.servico, l.periodicidade,
         case l.periodicidade
           when 'semana' then date_trunc('week',  l.created_at at time zone 'America/Sao_Paulo')::date
           else               date_trunc('month', l.created_at at time zone 'America/Sao_Paulo')::date
         end as competencia,
         min(l.created_at) as primeiro, count(*) as n
  from tmp_lanc l
  where l.origem_tipo = 'renovacao' and l.periodicidade is not null
    and exists (select 1 from novo.aluno a where a.id = l.athlete_id)
  group by 1, 2, 3, 4
) g
join novo.servico s on s.codigo = g.servico
on conflict (aluno_id, servico_id, periodicidade, competencia) do update
  set matricula_id = excluded.matricula_id, executada_em = excluded.executada_em,
      pendencia = novo.juntar_pendencia(r.pendencia, excluded.pendencia),
      criado_em = excluded.criado_em, atualizado_em = now();

-- -----------------------------------------------------------------------------
-- c3) credito_lancamento (extrato; id = credit_transactions.id)
-- -----------------------------------------------------------------------------
insert into novo.credito_lancamento as c (id, aluno_id, servico_id, delta, motivo, origem_tipo,
                                          renovacao_id, ator_id, pendencia, criado_em)
select l.id, l.athlete_id, s.id, l.delta, l.reason, l.origem_tipo,
       (select r.id from novo.renovacao r
         where l.origem_tipo = 'renovacao'
           and r.aluno_id = l.athlete_id and r.servico_id = s.id and r.periodicidade = l.periodicidade
           and r.competencia = case l.periodicidade
                 when 'semana' then date_trunc('week',  l.created_at at time zone 'America/Sao_Paulo')::date
                 else               date_trunc('month', l.created_at at time zone 'America/Sao_Paulo')::date end),
       case when exists (select 1 from novo.perfil_usuario u where u.usuario_id = l.actor_id) then l.actor_id end,
       novo.juntar_pendencia(novo.juntar_pendencia(novo.juntar_pendencia(
         case
           when l.tem_colchete then null
           when l.reason ~ '^Renovação semanal' and l.reason ~* 'treino' then null
           when l.reason ~ '^Renovação mensal' and l.reason ~* 'fisio|nutri' then null
           when l.reason !~* 'treino|fisio|nutri|pkz|renovação' then 'serviço não identificado (assumido treino)'
           else 'serviço deduzido do texto'
         end,
         case when l.tem_colchete and l.servico_citado is not null and l.servico_citado <> l.servico
              then 'crédito debitado de saldo diferente do serviço agendado' end),
         case when l.origem_tipo = 'outro' then 'origem do lançamento não identificada' end),
         case when l.actor_id is not null
               and not exists (select 1 from novo.perfil_usuario u where u.usuario_id = l.actor_id)
              then 'ator do lançamento não encontrado' end),
       l.created_at
from tmp_lanc l
join novo.aluno a on a.id = l.athlete_id
join novo.servico s on s.codigo = l.servico
on conflict (id) do update
  set aluno_id = excluded.aluno_id, servico_id = excluded.servico_id, delta = excluded.delta,
      motivo = excluded.motivo, origem_tipo = excluded.origem_tipo, renovacao_id = excluded.renovacao_id,
      ator_id = excluded.ator_id,
      pendencia = novo.juntar_pendencia(c.pendencia, excluded.pendencia),
      criado_em = excluded.criado_em, atualizado_em = now();

-- -----------------------------------------------------------------------------
-- c4) Conferência de saldo (não corrige nada)
--   Créditos não são cumulativos: a renovação redefine o saldo (migration 011).
--   Compara o saldo guardado no aluno com novo.vw_saldo_credito, por serviço.
--   Primeiro tira as marcas de saldo de execuções anteriores (a regra pode ter
--   mudado), depois marca de novo. É update, não delete.
-- -----------------------------------------------------------------------------
update novo.matricula m
set pendencia = nullif(array_to_string(array(
      select p from unnest(string_to_array(m.pendencia, '; ')) p
      where p not like 'ajuste de saldo pendente%'), '; '), '')
where m.pendencia like '%ajuste de saldo pendente%';

update novo.matricula m
set pendencia = novo.juntar_pendencia(m.pendencia,
      format('ajuste de saldo pendente: %s cadastro=%s calculado=%s', d.servico, d.cadastro, d.calculado))
from (
  select a.id as aluno_id, v.servico, v.cadastro, coalesce(vs.saldo, 0) as calculado
  from origem.athletes a
  cross join lateral (values ('treino', a.credits), ('fisioterapia', a.credits_fisio), ('nutricao', a.credits_nutri)) v(servico, cadastro)
  join novo.servico s on s.codigo = v.servico
  left join novo.vw_saldo_credito vs on vs.aluno_id = a.id and vs.servico_id = s.id
) d
where m.aluno_id = d.aluno_id
  and m.vigencia_fim is null
  and d.cadastro <> d.calculado;

-- -----------------------------------------------------------------------------
-- Registro da execução
-- -----------------------------------------------------------------------------
insert into novo.carga_execucao (script, linhas_carregadas, linhas_rejeitadas, observacao)
select 'comercial',
       (select count(*) from novo.matricula) + (select count(*) from novo.renovacao)
     + (select count(*) from novo.credito_lancamento),
       (select count(*) from novo.carga_rejeitado where script = 'comercial'),
       format('matricula %s (com ajuste de saldo pendente: %s), renovacao %s, credito_lancamento %s',
              (select count(*) from novo.matricula),
              (select count(*) from novo.matricula where pendencia like '%ajuste de saldo pendente%'),
              (select count(*) from novo.renovacao), (select count(*) from novo.credito_lancamento));

commit;
