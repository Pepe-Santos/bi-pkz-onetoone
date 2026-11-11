-- =============================================================================
-- 014_ajuste_views_consumo.sql
-- Ajustes da revisão da Frente 1 nas views de consumo da 013 (tarefa 3.4)
-- Pré-requisito: 013_views_consumo.sql.
--
-- Muda: vw_aluno, vw_avaliacao_medida. As colunas continuam as mesmas, na mesma
-- ordem, então o `create or replace` mantém o grant da 013.
--
-- Ajustes:
--   * vw_avaliacao_medida: a correção só esconde a avaliação original depois de
--     consolidada. Antes, uma correção ainda em rascunho tirava as duas da view.
--   * vw_avaliacao_medida: sem avaliação de fisioterapia. É dado clínico e o
--     Grupo de Desenvolvimento só usa teste_fisico; quem precisar da fisio lê a
--     tabela, com a política da 012.
--   * vw_aluno: no máximo uma unidade por aluno. A vw_matricula_vigente também
--     traz matrícula com fim no futuro, e o índice único só cobre
--     vigencia_fim nula; um aluno com as duas sairia duplicado. A regra de
--     desempate é a da unidade_atual_do_aluno (que o authenticated não pode
--     executar), mas só entre matrículas vigentes: aluno sem matrícula vigente
--     continua sem unidade, como na 013.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- vw_aluno — uma linha por aluno
-- -----------------------------------------------------------------------------
create or replace view novo.vw_aluno with (security_invoker = true) as
select
  a.id                                                             as aluno_id,
  p.nome,
  p.data_nascimento,
  a.categoria,
  a.status,
  a.data_entrada,
  u.codigo                                                         as unidade
from novo.aluno a
join novo.pessoa p on p.id = a.pessoa_id
left join lateral (
  select m.unidade_id
  from novo.vw_matricula_vigente m
  where m.aluno_id = a.id
  order by (m.vigencia_fim is null) desc, m.vigencia_inicio desc, m.id
  limit 1
) mv on true
left join novo.unidade u on u.id = mv.unidade_id;

comment on view novo.vw_aluno is
  'Consumo (3.4): um aluno por linha, com a unidade da matrícula vigente (a sem fim, ou a mais recente). Sem cpf, telefone e foto.';

-- -----------------------------------------------------------------------------
-- vw_avaliacao_medida — uma linha por medida
-- Só avaliação consolidada, fora da fisioterapia, e que não foi substituída por
-- uma correção consolidada.
-- -----------------------------------------------------------------------------
create or replace view novo.vw_avaliacao_medida with (security_invoker = true) as
select
  v.id                                                             as avaliacao_id,
  v.aluno_id,
  u.codigo                                                         as unidade,
  v.data,
  v.tipo,
  me.codigo                                                        as metrica_codigo,
  me.nome                                                          as metrica_nome,
  me.dominio,
  me.unidade_medida,
  me.direcao_desejada,
  me.valor_min,
  me.valor_max,
  m.lado,
  m.tentativa,
  m.valor_num,
  m.valor_texto
from novo.avaliacao_medida m
join novo.avaliacao v on v.id = m.avaliacao_id
join novo.metrica me on me.id = m.metrica_id
left join novo.unidade u on u.id = v.unidade_id
where v.status = 'consolidada'
  and v.tipo <> 'fisioterapia'
  and not exists (
    select 1
    from novo.avaliacao c
    where c.corrige_avaliacao_id = v.id
      and c.status = 'consolidada'
  );

comment on view novo.vw_avaliacao_medida is
  'Consumo (3.4): uma medida por linha, com a métrica. Só avaliação consolidada, sem fisioterapia, e não substituída por correção consolidada. Sem conversão de unidade: o valor sai como foi registrado.';
