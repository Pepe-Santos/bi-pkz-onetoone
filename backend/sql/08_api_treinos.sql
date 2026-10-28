-- Views da API de treinos (schema api), para os relatórios PKZ e One to One (semanal,
-- mensal e anual). Contrato em backend/docs/api.md. Uma linha por registro, sem agregação:
-- o gerador filtra o período por data.
-- Depende do 06_api_avaliacoes.sql (trat.unidade_permitida) e da novo.vw_agendamento e
-- novo.vw_relatorio_treino (views de consumo do grupo de Dados, migration 013). Pode rodar
-- quantas vezes quiser (CREATE OR REPLACE VIEW). O 05 não apaga estas views: elas não leem
-- o trat.medida.
--
-- Como no 06, as views são do postgres e rodam com as permissões dele, e cada usuário só vê
-- as linhas da unidade em app_metadata.unidade (aqui, a unidade do próprio agendamento ou
-- relatório). Sem nome nem outro dado pessoal: o nome fica só em api.atleta.
--
-- A data de hoje é a de São Paulo: o current_date do Supabase é UTC, e há relatórios com
-- data no futuro, que ficam de fora até o dia chegar.

-- ---------------------------------------------------------------------------
-- presenca: uma linha por agendamento de treino.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW api.presenca AS
SELECT
  a.agendamento_id,
  a.aluno_id           AS atleta_id,
  upper(a.unidade)     AS unidade,
  a.data,
  a.hora_inicio,
  -- aguardando_confirmacao é um agendado que o aluno ainda não confirmou
  CASE WHEN a.status = 'aguardando_confirmacao' THEN 'agendado' ELSE a.status::text END AS status
FROM novo.vw_agendamento a
WHERE a.servico_codigo = 'treino'
  AND a.data <= (now() AT TIME ZONE 'America/Sao_Paulo')::date
  AND trat.unidade_permitida(upper(a.unidade));

-- ---------------------------------------------------------------------------
-- treino: uma linha por relatório de treino final. A novo.vw_relatorio_treino já traz
-- só os relatórios com status 'final' e não tem os campos de dor (dado de saúde).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW api.treino AS
SELECT
  r.relatorio_id,
  r.aluno_id           AS atleta_id,
  upper(r.unidade)     AS unidade,
  r.data,
  r.tipo_treino,
  r.intensidade,
  r.objetivos,
  r.desempenho,
  r.observacoes
FROM novo.vw_relatorio_treino r
WHERE r.data <= (now() AT TIME ZONE 'America/Sao_Paulo')::date
  AND trat.unidade_permitida(upper(r.unidade));

-- O SELECT para authenticated e service_role vem do ALTER DEFAULT PRIVILEGES do 01_schemas.sql.
