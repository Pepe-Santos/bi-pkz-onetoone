-- =============================================================================
-- conferencia/03_saldo_credito.sql
-- Saldo de créditos: as duas conferências lado a lado. SÓ LEITURA.
--
-- Existem duas conferências de saldo, com universos e critérios diferentes:
--   A) Carga 30 + migration 011 (Frente 1): todo par (aluno, serviço) da origem,
--      106 alunos × 3 saldos (treino, fisio, nutri). Serviço de cada lançamento
--      pela regra da carga (o colchete [treino]/[fisio]/[nutri] diz de qual saldo
--      saiu; sem colchete, pelo texto; renovação genérica = treino). Saldo =
--      lançamentos desde a última renovação do serviço, INCLUSIVE a renovação,
--      cujo delta é a cota do plano. Sem renovação: soma de tudo.
--   B) Conferência 5 da tarefa 2.1 (Frente 2): só os pares (atleta, serviço) que
--      têm uma renovação cujo texto identifica o serviço. Serviço pelo texto
--      (fisio > nutri > treino/PKZ), sem olhar o colchete; renovações genéricas
--      ficam de fora. Saldo = 10 + lançamentos DEPOIS da última renovação.
-- Como ler as duas juntas: explicação em mapeamento/README.md, seção
-- "Saldo de créditos: as duas conferências".
-- Nenhuma consulta mostra dado pessoal: só contagens.
-- =============================================================================

with
-- saldo guardado na origem, por aluno e serviço
guardado as (
  select a.id as aluno_id, v.servico, v.saldo
  from origem.athletes a
  cross join lateral (values ('treino', a.credits), ('fisioterapia', a.credits_fisio),
                             ('nutricao', a.credits_nutri)) v(servico, saldo)
),
-- A) critério da carga: novo.vw_saldo_credito (migration 011)
criterio_a as (
  select g.aluno_id, g.servico, g.saldo as guardado, coalesce(vs.saldo, 0) as calculado
  from guardado g
  join novo.servico s on s.codigo = g.servico
  left join novo.vw_saldo_credito vs on vs.aluno_id = g.aluno_id and vs.servico_id = s.id
),
-- B) critério da 2.1, reproduzido sobre a origem
lanc_b as (
  select t.athlete_id, t.delta, t.created_at,
         case when t.reason ilike '%fisio%' then 'fisioterapia'
              when t.reason ilike '%nutri%' then 'nutricao'
              when t.reason ilike '%treino%' or t.reason ilike '%PKZ%' then 'treino' end as servico,
         t.reason ilike 'Renovação%'
           and (t.reason ilike '%fisio%' or t.reason ilike '%nutri%'
                or t.reason ilike '%PKZ%' or t.reason ilike '%treino%') as renovacao_com_servico
  from origem.credit_transactions t
),
ultima_b as (
  select distinct on (athlete_id, servico)
         athlete_id as aluno_id, servico, created_at as ultima_renovacao_em, delta as cota
  from lanc_b
  where renovacao_com_servico
  order by athlete_id, servico, created_at desc
),
criterio_b as (
  select u.aluno_id, u.servico, u.cota,
         coalesce(sum(l.delta) filter (where l.created_at > u.ultima_renovacao_em), 0)::int as depois
  from ultima_b u
  left join lanc_b l on l.athlete_id = u.aluno_id and l.servico = u.servico
  group by u.aluno_id, u.servico, u.cota
),
juntos as (
  select a.*, b.aluno_id is not null as no_universo_b, b.cota, b.depois
  from criterio_a a
  left join criterio_b b on b.aluno_id = a.aluno_id and b.servico = a.servico
)
select 'A: todos os pares (aluno, serviço)'                         as recorte,
       count(*)                                                     as pares,
       count(*) filter (where guardado <> calculado)                as divergentes_criterio_a,
       null::bigint                                                 as divergentes_base_10,
       null::bigint                                                 as divergentes_base_cota
from juntos
union all
select 'B: só pares com renovação que identifica o serviço',
       count(*),
       count(*) filter (where guardado <> calculado),
       count(*) filter (where guardado <> 10 + depois),
       count(*) filter (where guardado <> cota + depois)
from juntos where no_universo_b
union all
select 'A fora de B (sem renovação identificável pelo texto)',
       count(*),
       count(*) filter (where guardado <> calculado),
       null, null
from juntos where not no_universo_b;

-- Cotas de renovação encontradas na origem (por que "reiniciar em 10" não serve)
select delta as cota, count(*) as renovacoes
from origem.credit_transactions
where reason ilike 'Renovação%'
group by delta
order by delta;
