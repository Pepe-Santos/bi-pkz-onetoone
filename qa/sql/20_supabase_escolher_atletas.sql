-- QA: escolha dos atletas de referência. RODAR NO SQL EDITOR DO SUPABASE (só leitura).
-- Sugere um atleta por situação que vale conferir com o app. O SQL Editor roda como
-- postgres, então vê todas as unidades.
--
-- O nome aparece só para achar o atleta no app. Na planilha de conferência e em qualquer
-- coisa que vá para o GitHub, use só o atleta_id (UUID).

WITH resumo AS (
  SELECT
    a.atleta_id,
    a.nome,
    coalesce(a.unidade, 'sem unidade')                               AS unidade,
    a.total_avaliacoes,
    a.ultima_avaliacao_em,
    (SELECT count(*) FROM trat.medida m WHERE m.aluno_id = a.atleta_id AND m.convertido)   AS convertidas,
    (SELECT count(*) FROM trat.revisao_dados r WHERE r.aluno_id = a.atleta_id)              AS em_revisao,
    (SELECT count(DISTINCT teste) FROM trat.resultado_teste t WHERE t.aluno_id = a.atleta_id) AS testes
  FROM api.atleta a
),
criterio AS (
  SELECT 'PKZ com histórico mais longo' AS criterio, 1 AS ordem, atleta_id,
         row_number() OVER (ORDER BY total_avaliacoes DESC, testes DESC) AS pos
  FROM resumo WHERE unidade = 'PKZ'
  UNION ALL
  SELECT 'PKZ com uma avaliação só', 2, atleta_id,
         row_number() OVER (ORDER BY testes DESC)
  FROM resumo WHERE unidade = 'PKZ' AND total_avaliacoes = 1
  UNION ALL
  SELECT 'One to One com avaliação', 3, atleta_id,
         row_number() OVER (ORDER BY total_avaliacoes DESC)
  FROM resumo WHERE unidade = 'ONE_TO_ONE' AND total_avaliacoes > 0
  UNION ALL
  SELECT 'Valor convertido (m -> cm ou km -> m)', 4, atleta_id,
         row_number() OVER (ORDER BY convertidas DESC)
  FROM resumo WHERE convertidas > 0
  UNION ALL
  SELECT 'Tentativa em revisão (valor impossível)', 5, atleta_id,
         row_number() OVER (ORDER BY em_revisao DESC)
  FROM resumo WHERE em_revisao > 0
  UNION ALL
  SELECT 'Sem matrícula vigente (sem unidade)', 6, atleta_id,
         row_number() OVER (ORDER BY total_avaliacoes DESC)
  FROM resumo WHERE unidade = 'sem unidade'
  UNION ALL
  SELECT 'Reavaliação vencida', 7, r.atleta_id,
         row_number() OVER (ORDER BY r.dias_para_vencer)
  FROM api.reavaliacao r WHERE r.situacao = 'vencida'
  UNION ALL
  SELECT 'Nunca avaliado', 8, atleta_id,
         row_number() OVER (ORDER BY atleta_id)
  FROM resumo WHERE total_avaliacoes = 0
)
SELECT c.criterio, r.atleta_id, r.nome, r.unidade, r.total_avaliacoes, r.testes,
       r.convertidas, r.em_revisao, r.ultima_avaliacao_em
FROM criterio c
JOIN resumo r USING (atleta_id)
WHERE c.pos = 1
ORDER BY c.ordem;
