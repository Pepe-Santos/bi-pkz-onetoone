-- =============================================================================
-- 011_saldo_nao_cumulativo.sql
-- Dono: Micael (Frente 1). Pré-requisito: 010. 15/10/2026.
--
-- Por quê: no app, a RENOVAÇÃO NÃO SOMA créditos, ela REDEFINE o saldo
-- (public.run_daily_renewal faz "credits = cota do plano" e grava no extrato um
-- lançamento com delta = cota, não com a diferença). Créditos não são cumulativos.
-- A view do 003 somava o extrato inteiro e dava saldos inflados (no ensaio, o
-- treino ficava em média 37 créditos acima do saldo real).
--
-- Regra nova: saldo = soma dos lançamentos a partir da ÚLTIMA renovação daquele
-- serviço (inclusive). Sem renovação, soma tudo. Conferido na foto de 12/10:
-- treino 106/106, fisio 104/106 e nutri 105/106 alunos batem com o saldo guardado.
-- =============================================================================

create or replace view novo.vw_saldo_credito
with (security_invoker = true)
as
with ultima as (
  select l.aluno_id, l.servico_id,
         max(l.criado_em) filter (where l.origem_tipo = 'renovacao') as ultima_renovacao_em
  from novo.credito_lancamento l
  group by l.aluno_id, l.servico_id
)
select l.aluno_id, l.servico_id,
       (sum(l.delta) filter (where u.ultima_renovacao_em is null or l.criado_em >= u.ultima_renovacao_em))::int as saldo,
       max(l.criado_em) as ultimo_lancamento_em
from novo.credito_lancamento l
join ultima u on u.aluno_id = l.aluno_id and u.servico_id = l.servico_id
group by l.aluno_id, l.servico_id;

comment on view novo.vw_saldo_credito is
  'Saldo por aluno e serviço. Créditos NÃO são cumulativos: a renovação redefine o saldo (delta da renovação = cota). Saldo = lançamentos desde a última renovação (inclusive).';

comment on column novo.credito_lancamento.delta is
  'Movimento do crédito. Em origem_tipo = renovacao, é a COTA que passa a valer (a renovação redefine o saldo, não soma).';
