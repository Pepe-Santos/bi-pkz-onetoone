-- Views da API de treinos (schema api), para os relatórios PKZ e One to One (semanal,
-- mensal e anual). Contrato em backend/docs/api.md. Uma linha por registro, sem agregação:
-- o gerador filtra o período por data.
-- Depende do 06_api_avaliacoes.sql (trat.unidade_permitida) e das tabelas novo.agendamento,
-- novo.relatorio_treino, novo.unidade e novo.servico (grupo de Dados). Pode rodar quantas
-- vezes quiser (CREATE OR REPLACE VIEW). O 05 não apaga estas views: elas não leem o trat.medida.
--
-- Como no 06, as views são do postgres e rodam com as permissões dele, e cada usuário só vê
-- as linhas da unidade em app_metadata.unidade (aqui, a unidade do próprio agendamento ou
-- relatório). Sem nome nem outro dado pessoal: o nome fica só em api.atleta.
--
-- Lê as tabelas, e não a novo.vw_agendamento / novo.vw_relatorio_treino: essas views são
-- security_invoker, então aplicam o RLS da 012 a quem chama a API, e o usuário da API não
-- tem papel no app (novo.perfil_usuario). Por elas, quem entra com login recebe 0 linhas.
--
-- A data de hoje é a de São Paulo: o current_date do Supabase é UTC, e há relatórios com
-- data no futuro, que ficam de fora até o dia chegar.

-- ---------------------------------------------------------------------------
-- presenca: uma linha por agendamento de treino.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW api.presenca AS
SELECT
  a.id                 AS agendamento_id,
  a.aluno_id           AS atleta_id,
  upper(u.codigo)      AS unidade,
  a.data,
  a.hora_inicio,
  -- aguardando_confirmacao é um agendado que o aluno ainda não confirmou
  CASE WHEN a.status = 'aguardando_confirmacao' THEN 'agendado' ELSE a.status::text END AS status
FROM novo.agendamento a
JOIN novo.servico s     ON s.id = a.servico_id
LEFT JOIN novo.unidade u ON u.id = a.unidade_id
WHERE s.codigo = 'treino'
  AND a.data <= (now() AT TIME ZONE 'America/Sao_Paulo')::date
  AND trat.unidade_permitida(upper(u.codigo));

-- ---------------------------------------------------------------------------
-- treino: uma linha por relatório de treino final. Os campos de dor (dor, dor_local,
-- dor_intensidade, dor_movimento) são dado de saúde e não entram.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW api.treino AS
SELECT
  r.id                 AS relatorio_id,
  r.aluno_id           AS atleta_id,
  upper(u.codigo)      AS unidade,
  r.data,
  r.tipo_treino,
  r.intensidade,
  r.objetivos,
  r.desempenho,
  r.observacoes
FROM novo.relatorio_treino r
LEFT JOIN novo.unidade u ON u.id = r.unidade_id
WHERE r.status = 'final'
  AND r.data <= (now() AT TIME ZONE 'America/Sao_Paulo')::date
  AND trat.unidade_permitida(upper(u.codigo));

-- O SELECT para authenticated e service_role vem do ALTER DEFAULT PRIVILEGES do 01_schemas.sql.
