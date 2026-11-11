-- =============================================================================
-- 013_views_consumo.sql
-- Views que o Grupo de Desenvolvimento lê (tarefa 3.4)
-- Dono: Iago (Frente 3). Pré-requisito: 012_politicas_rls.sql.
--
-- Cria: vw_aluno, vw_avaliacao_medida, vw_relatorio_treino, vw_agendamento.
--
-- O conteúdo segue o card "[Dados] Criar as views que o Grupo de Desenvolvimento
-- vai ler" (Ewerton, 24/10), coluna por coluna. Ficam no schema `novo` com o
-- prefixo vw_, como as 5 views da Frente 1.
--
-- Escolhas:
--   * `security_invoker = true` em todas, como nas views da Frente 1: a view
--     aplica a política de quem consulta, e não a do dono. Sem isso qualquer
--     política da 012 seria contornável pela view.
--   * Sem cálculo: nada de conversão de unidade, melhor tentativa ou comparação.
--     Isso é do Grupo de Desenvolvimento, como diz o card.
--   * A unidade sai como código ('pkz' ou 'one_to_one'); em vw_aluno ela vem da
--     matrícula vigente, porque o aluno não tem unidade própria no modelo.
--   * Dado sensível de fora: vw_aluno não traz cpf, telefone nem foto;
--     vw_relatorio_treino não traz os campos de dor.
--   * Sem begin/commit e sem comando do psql, como as migrations 001–012
--     (o apply_migration já roda tudo numa transação).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- vw_aluno — uma linha por aluno (106)
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
left join novo.vw_matricula_vigente m on m.aluno_id = a.id
left join novo.unidade u on u.id = m.unidade_id;

comment on view novo.vw_aluno is
  'Consumo (3.4): um aluno por linha, com a unidade da matrícula vigente. Sem cpf, telefone e foto.';

-- -----------------------------------------------------------------------------
-- vw_avaliacao_medida — uma linha por medida (2.908)
-- Só avaliação consolidada e que não foi substituída por uma correção.
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
  and not exists (select 1 from novo.avaliacao c where c.corrige_avaliacao_id = v.id);

comment on view novo.vw_avaliacao_medida is
  'Consumo (3.4): uma medida por linha, com a métrica. Só avaliação consolidada e não corrigida. Sem conversão de unidade: o valor sai como foi registrado.';

-- -----------------------------------------------------------------------------
-- vw_relatorio_treino — uma linha por relatório final (224)
-- Os campos de dor ficam de fora: dado de saúde e os relatórios não usam.
-- -----------------------------------------------------------------------------
create or replace view novo.vw_relatorio_treino with (security_invoker = true) as
select
  r.id                                                             as relatorio_id,
  r.aluno_id,
  u.codigo                                                         as unidade,
  r.data,
  r.tipo,
  r.tipo_treino,
  r.numero_sessao,
  r.intensidade,
  r.objetivos,
  r.desempenho,
  r.evolucao,
  r.observacoes
from novo.relatorio_treino r
left join novo.unidade u on u.id = r.unidade_id
where r.status = 'final';

comment on view novo.vw_relatorio_treino is
  'Consumo (3.4): um relatório final por linha. Sem os campos de dor (dado de saúde).';

-- -----------------------------------------------------------------------------
-- vw_agendamento — uma linha por agendamento (536)
-- Serve para contar presença, falta e cancelamento.
-- -----------------------------------------------------------------------------
create or replace view novo.vw_agendamento with (security_invoker = true) as
select
  ag.id                                                            as agendamento_id,
  ag.aluno_id,
  u.codigo                                                         as unidade,
  ag.data,
  ag.hora_inicio,
  ag.status,
  s.nome                                                           as servico,
  s.codigo                                                         as servico_codigo
from novo.agendamento ag
join novo.servico s on s.id = ag.servico_id
left join novo.unidade u on u.id = ag.unidade_id;

comment on view novo.vw_agendamento is
  'Consumo (3.4): um agendamento por linha, para contar presença, falta e cancelamento. servico é o nome; servico_codigo serve para filtrar.';

-- -----------------------------------------------------------------------------
-- Acesso
-- A 012 deu select em todas as tabelas que existiam naquele momento; view nova
-- precisa do grant próprio.
-- -----------------------------------------------------------------------------
grant select on novo.vw_aluno, novo.vw_avaliacao_medida,
                novo.vw_relatorio_treino, novo.vw_agendamento
  to authenticated, service_role;
