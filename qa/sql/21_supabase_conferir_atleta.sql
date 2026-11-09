-- QA: conferência de um atleta, tentativa por tentativa. RODAR NO SQL EDITOR DO SUPABASE
-- (só leitura). Troque o UUID na linha marcada e compare com a tela de avaliação do app.
--
-- Para cada tentativa: o valor como está no banco novo, o valor tratado, se valeu, o
-- resultado que vai para a API e a comparação com a avaliação anterior.
-- Na planilha, anote só o atleta_id, o teste, a data e os números. Nada de nome.

WITH alvo AS (
  SELECT '00000000-0000-0000-0000-000000000000'::uuid AS atleta_id   -- <<< troque aqui
)
SELECT
  m.data_avaliacao,
  m.teste,
  m.lado,
  m.tentativa,
  m.valor_origem                               AS valor_no_app,
  m.valor_texto_origem                         AS texto_no_app,
  m.valor                                      AS valor_tratado,
  CASE WHEN m.convertido THEN 'sim' END        AS convertido,
  CASE WHEN m.valido THEN 'vale' ELSE m.motivo_revisao END AS situacao,
  r.valor                                      AS resultado_na_api,
  r.tentativas_validas,
  CASE WHEN c.data_atual = m.data_avaliacao
       THEN c.situacao || coalesce(' (' || c.variacao_pct || '%)', '') END AS comparacao_com_anterior
FROM alvo
JOIN trat.medida m ON m.aluno_id = alvo.atleta_id
LEFT JOIN trat.resultado_teste r
       ON r.avaliacao_id = m.avaliacao_id AND r.teste = m.teste AND r.lado IS NOT DISTINCT FROM m.lado
LEFT JOIN api.comparacao c
       ON c.atleta_id = m.aluno_id AND c.teste = m.teste AND c.lado IS NOT DISTINCT FROM m.lado
ORDER BY m.data_avaliacao DESC, m.teste, m.lado, m.tentativa;

-- Medidas do atleta que NÃO chegam ao trat (teste fora do catálogo ou tipo diferente
-- de teste_fisico). Se aparecer algo aqui que existe no app, é dado perdido.
WITH alvo AS (
  SELECT '00000000-0000-0000-0000-000000000000'::uuid AS atleta_id   -- <<< troque aqui também
)
SELECT am.data, am.tipo, am.metrica_codigo, am.lado, am.tentativa, am.valor_num, am.valor_texto
FROM alvo
JOIN novo.vw_avaliacao_medida am ON am.aluno_id = alvo.atleta_id
WHERE am.tipo <> 'teste_fisico'
   OR am.metrica_codigo NOT IN (SELECT codigo FROM trat.catalogo_teste)
ORDER BY am.data DESC, am.metrica_codigo;
