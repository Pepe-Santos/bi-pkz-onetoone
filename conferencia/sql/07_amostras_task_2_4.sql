-- Task 2.4: candidatos de amostragem, somente leitura.
-- Este arquivo não compara origem e destino e não declara resultados.
-- Saídas destinadas ao registro: IDs técnicos, contagens, nulidade e status de candidato.

-- 0) Pré-condições operacionais
-- Executar somente depois de revisar conferencia/sql/00_preflight_destino.sql.
-- As consultas abaixo não substituem a confirmação independente do projeto, das permissões,
-- do snapshot de gabarito e do estado não homologado da Task 2.3.

-- 1) Cadastro: candidatos no destino por cardinalidade de vínculos técnicos.
WITH candidatos AS (
  SELECT
    a.id AS destino_id,
    COUNT(DISTINCT asv.servico_id) + COUNT(DISTINCT m.id) AS vinculos_tecnicos,
    COUNT(DISTINCT asv.servico_id) AS servicos_relacionados,
    COUNT(DISTINCT m.id) AS matriculas_relacionadas,
    CASE WHEN COUNT(DISTINCT p.id) > 0 THEN 1 ELSE 0 END AS pessoa_vinculada
  FROM novo.aluno a
  LEFT JOIN novo.aluno_servico asv ON asv.aluno_id = a.id
  LEFT JOIN novo.matricula m ON m.aluno_id = a.id
  LEFT JOIN novo.pessoa p ON p.id = a.pessoa_id
  GROUP BY a.id
)
SELECT 'CADASTRO' AS dominio, 'MUITOS' AS categoria, c.*
FROM candidatos c
ORDER BY vinculos_tecnicos DESC, servicos_relacionados DESC, matriculas_relacionadas DESC, destino_id
LIMIT 10;

WITH candidatos AS (
  SELECT
    a.id AS destino_id,
    COUNT(DISTINCT asv.servico_id) + COUNT(DISTINCT m.id) AS vinculos_tecnicos,
    COUNT(DISTINCT asv.servico_id) AS servicos_relacionados,
    COUNT(DISTINCT m.id) AS matriculas_relacionadas,
    CASE WHEN COUNT(DISTINCT p.id) > 0 THEN 1 ELSE 0 END AS pessoa_vinculada
  FROM novo.aluno a
  LEFT JOIN novo.aluno_servico asv ON asv.aluno_id = a.id
  LEFT JOIN novo.matricula m ON m.aluno_id = a.id
  LEFT JOIN novo.pessoa p ON p.id = a.pessoa_id
  GROUP BY a.id
)
SELECT 'CADASTRO' AS dominio, 'POUCOS' AS categoria, c.*
FROM candidatos c
WHERE vinculos_tecnicos > 0
ORDER BY vinculos_tecnicos, servicos_relacionados, matriculas_relacionadas, destino_id
LIMIT 10;

SELECT 'CADASTRO' AS dominio, 'ESTRANHO' AS categoria, 'PESSOA_ORIGEM_DUPLICADA' AS anomalia,
       origem_tabela, origem_id, quantidade
FROM (
  SELECT origem_tabela, origem_id, COUNT(*) AS quantidade
  FROM novo.pessoa
  WHERE origem_tabela IS NOT NULL AND origem_id IS NOT NULL
  GROUP BY origem_tabela, origem_id
  HAVING COUNT(*) > 1
) d
ORDER BY quantidade DESC, origem_tabela, origem_id
LIMIT 10;

-- 2) Comercial e créditos: candidatos por extrato e saldo reconstruível.
WITH candidatos AS (
  SELECT aluno_id, servico_id, COUNT(*) AS lancamentos,
         COUNT(*) FILTER (WHERE origem_tipo = 'renovacao') AS renovacoes,
         SUM(delta)::integer AS delta_total
  FROM novo.credito_lancamento
  GROUP BY aluno_id, servico_id
)
SELECT 'COMERCIAL_E_CREDITOS' AS dominio, 'MUITOS' AS categoria, c.*
FROM candidatos c
ORDER BY lancamentos DESC, renovacoes DESC, aluno_id, servico_id
LIMIT 10;

WITH candidatos AS (
  SELECT aluno_id, servico_id, COUNT(*) AS lancamentos,
         COUNT(*) FILTER (WHERE origem_tipo = 'renovacao') AS renovacoes,
         SUM(delta)::integer AS delta_total
  FROM novo.credito_lancamento
  GROUP BY aluno_id, servico_id
)
SELECT 'COMERCIAL_E_CREDITOS' AS dominio, 'POUCOS' AS categoria, c.*
FROM candidatos c
WHERE lancamentos > 0
ORDER BY lancamentos, renovacoes, aluno_id, servico_id
LIMIT 10;

SELECT 'COMERCIAL_E_CREDITOS' AS dominio, 'ESTRANHO' AS categoria,
       'RENOVACAO_SEM_LANCAMENTO' AS anomalia, r.id AS renovacao_id,
       r.aluno_id, r.servico_id
FROM novo.renovacao r
WHERE NOT EXISTS (
  SELECT 1 FROM novo.credito_lancamento l WHERE l.renovacao_id = r.id
)
UNION ALL
SELECT 'COMERCIAL_E_CREDITOS', 'ESTRANHO', 'LANCAMENTO_RENOVACAO_SEM_FK',
       l.id, l.aluno_id, l.servico_id
FROM novo.credito_lancamento l
WHERE l.origem_tipo = 'renovacao' AND l.renovacao_id IS NULL
ORDER BY anomalia, aluno_id, servico_id
LIMIT 20;

-- 3) Agenda: candidatos no destino. As tabelas de origem existem no inventário,
-- mas suas colunas de correspondência não estão documentadas nos arquivos locais.
WITH candidatos AS (
  SELECT aluno_id, servico_id, COUNT(*) AS agendamentos,
         COUNT(*) FILTER (WHERE status <> 'cancelado') AS agendamentos_ativos
  FROM novo.agendamento
  GROUP BY aluno_id, servico_id
)
SELECT 'AGENDA' AS dominio, 'MUITOS' AS categoria, c.*
FROM candidatos c
ORDER BY agendamentos DESC, agendamentos_ativos DESC, aluno_id, servico_id
LIMIT 10;

WITH candidatos AS (
  SELECT aluno_id, servico_id, COUNT(*) AS agendamentos,
         COUNT(*) FILTER (WHERE status <> 'cancelado') AS agendamentos_ativos
  FROM novo.agendamento
  GROUP BY aluno_id, servico_id
)
SELECT 'AGENDA' AS dominio, 'POUCOS' AS categoria, c.*
FROM candidatos c
WHERE agendamentos > 0
ORDER BY agendamentos, agendamentos_ativos, aluno_id, servico_id
LIMIT 10;

SELECT 'AGENDA' AS dominio, 'ESTRANHO' AS categoria,
       'DUPLICIDADE_AGENDAMENTO_ATIVO' AS anomalia,
       aluno_id, servico_id, data, hora_inicio, COUNT(*) AS quantidade
FROM novo.agendamento
WHERE status <> 'cancelado'
GROUP BY aluno_id, servico_id, data, hora_inicio
HAVING COUNT(*) > 1
ORDER BY quantidade DESC, aluno_id, servico_id, data, hora_inicio
LIMIT 10;

-- 4) Relatórios: bloqueado para seleção de registros.
-- O repositório comprova as tabelas e o filtro de domínio do catálogo, mas não
-- comprova a chave entre training_reports e relatorio_treino nem a relação dos
-- itens de catálogo com um relatório. Não selecionar amostras aqui por contagem
-- de catalogo_item: isso mediria itens, não relatórios.

-- 5) Avaliações: candidatos por tipo e aluno no destino.
WITH candidatos AS (
  SELECT tipo, aluno_id, COUNT(*) AS avaliacoes
  FROM novo.avaliacao
  WHERE tipo IN ('teste_fisico', 'semanal')
  GROUP BY tipo, aluno_id
)
SELECT 'AVALIACOES' AS dominio, 'MUITOS' AS categoria, c.*
FROM candidatos c
ORDER BY avaliacoes DESC, tipo, aluno_id
LIMIT 10;

WITH candidatos AS (
  SELECT tipo, aluno_id, COUNT(*) AS avaliacoes
  FROM novo.avaliacao
  WHERE tipo IN ('teste_fisico', 'semanal')
  GROUP BY tipo, aluno_id
)
SELECT 'AVALIACOES' AS dominio, 'POUCOS' AS categoria, c.*
FROM candidatos c
ORDER BY avaliacoes, tipo, aluno_id
LIMIT 10;

SELECT 'AVALIACOES' AS dominio, 'ESTRANHO' AS categoria,
       'TIPO_FORA_DO_MAPEAMENTO_CONFIRMADO' AS anomalia,
       id AS destino_id, tipo, aluno_id
FROM novo.avaliacao
WHERE tipo IS NULL OR tipo NOT IN ('teste_fisico', 'semanal', 'fisioterapia')
ORDER BY destino_id
LIMIT 10;

-- 6) Atendimento: medidas da origem estão comprovadas; a correspondência
-- physio_assessments -> avaliacao/anamnese continua parcial.
WITH medidas AS (
  SELECT p.id AS origem_id,
         COUNT(*) FILTER (WHERE v.valor IS NOT NULL) AS medidas_preenchidas
  FROM origem.physio_assessments p
  CROSS JOIN LATERAL (VALUES
    (p.cotovelo_ext_dir), (p.cotovelo_ext_esq), (p.cotovelo_flex_dir),
    (p.cotovelo_flex_esq), (p.joelho_ext_dir), (p.joelho_ext_esq),
    (p.joelho_flex_dir), (p.joelho_flex_esq), (p.ombro_abd_dir),
    (p.ombro_abd_esq), (p.ombro_rot_ext_dir), (p.ombro_rot_ext_esq),
    (p.quadril_dir), (p.quadril_esq)
  ) v(valor)
  GROUP BY p.id
)
SELECT 'ATENDIMENTO' AS dominio, 'MUITOS' AS categoria, m.*
FROM medidas m
ORDER BY medidas_preenchidas DESC, origem_id
LIMIT 10;

WITH medidas AS (
  SELECT p.id AS origem_id,
         COUNT(*) FILTER (WHERE v.valor IS NOT NULL) AS medidas_preenchidas
  FROM origem.physio_assessments p
  CROSS JOIN LATERAL (VALUES
    (p.cotovelo_ext_dir), (p.cotovelo_ext_esq), (p.cotovelo_flex_dir),
    (p.cotovelo_flex_esq), (p.joelho_ext_dir), (p.joelho_ext_esq),
    (p.joelho_flex_dir), (p.joelho_flex_esq), (p.ombro_abd_dir),
    (p.ombro_abd_esq), (p.ombro_rot_ext_dir), (p.ombro_rot_ext_esq),
    (p.quadril_dir), (p.quadril_esq)
  ) v(valor)
  GROUP BY p.id
)
SELECT 'ATENDIMENTO' AS dominio, 'POUCOS' AS categoria, m.*
FROM medidas m
ORDER BY medidas_preenchidas, origem_id
LIMIT 10;

SELECT 'ATENDIMENTO' AS dominio, 'ESTRANHO' AS categoria,
       'PKZ_DATA_NAO_OBJETO_OU_NULO' AS anomalia,
       id AS origem_id
FROM origem.physio_assessments
WHERE pkz_data IS NULL OR jsonb_typeof(pkz_data) <> 'object'
ORDER BY origem_id
LIMIT 10;

-- 7) Documentos e auditoria: somente IDs do destino e cardinalidades.
WITH candidatos AS (
  SELECT aluno_id, COUNT(*) AS arquivos,
         COUNT(DISTINCT avaliacao_id) AS avaliacoes_relacionadas,
         COUNT(DISTINCT atendimento_id) AS atendimentos_relacionados
  FROM novo.arquivo
  GROUP BY aluno_id
)
SELECT 'DOCUMENTOS_E_AUDITORIA' AS dominio, 'MUITOS' AS categoria, c.*
FROM candidatos c
ORDER BY arquivos DESC, avaliacoes_relacionadas DESC, atendimentos_relacionados DESC, aluno_id
LIMIT 10;

WITH candidatos AS (
  SELECT aluno_id, COUNT(*) AS arquivos,
         COUNT(DISTINCT avaliacao_id) AS avaliacoes_relacionadas,
         COUNT(DISTINCT atendimento_id) AS atendimentos_relacionados
  FROM novo.arquivo
  GROUP BY aluno_id
)
SELECT 'DOCUMENTOS_E_AUDITORIA' AS dominio, 'POUCOS' AS categoria, c.*
FROM candidatos c
WHERE arquivos > 0
ORDER BY arquivos, avaliacoes_relacionadas, atendimentos_relacionados, aluno_id
LIMIT 10;

SELECT 'DOCUMENTOS_E_AUDITORIA' AS dominio, 'ESTRANHO' AS categoria,
       'ARQUIVO_SEM_RELACAO_DOCUMENTADA' AS anomalia,
       id AS destino_id
FROM novo.arquivo
WHERE relatorio_id IS NULL AND aluno_id IS NULL AND avaliacao_id IS NULL AND atendimento_id IS NULL
ORDER BY destino_id
LIMIT 10;

-- activity_logs e booking_audit_logs aparecem no mapa de carga, mas suas
-- colunas de origem não estão comprovadas nos arquivos locais; não há candidato
-- de auditoria por registro nesta etapa.
