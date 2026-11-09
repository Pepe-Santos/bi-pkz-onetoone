-- QA: verificações do tratamento sobre a base inteira. RODAR NO SQL EDITOR DO SUPABASE
-- (só leitura). Só contagens e totais: o resultado pode ir para o relatório de QA.
-- Cada bloco diz o que é esperado.

-- 1. Cobertura: toda medida de teste físico do banco novo tem regra no catálogo?
--    Esperado: 0 linhas. Teste fora do catálogo some sem aviso (o JOIN do trat.medida descarta).
SELECT am.metrica_codigo, count(*) AS medidas_descartadas
FROM novo.vw_avaliacao_medida am
LEFT JOIN trat.catalogo_teste c ON c.codigo = am.metrica_codigo
WHERE am.tipo = 'teste_fisico' AND c.codigo IS NULL
GROUP BY am.metrica_codigo ORDER BY 2 DESC;

-- 2. Totais origem × tratamento. Esperado: medidas_teste_fisico = tentativas_no_trat.
SELECT
  (SELECT count(*) FROM novo.vw_avaliacao_medida WHERE tipo = 'teste_fisico') AS medidas_teste_fisico,
  (SELECT count(*) FROM trat.medida)                                         AS tentativas_no_trat,
  (SELECT count(*) FROM trat.medida WHERE valido)                            AS validas,
  (SELECT count(*) FROM trat.revisao_dados)                                  AS em_revisao,
  (SELECT count(*) FROM trat.medida WHERE convertido)                        AS convertidas;

-- 3. Revisões por teste e motivo: confere se as faixas fazem sentido com os dados reais.
--    Muita revisão num teste só costuma ser faixa ou unidade errada no catálogo.
SELECT teste, motivo_revisao, count(*) AS tentativas,
       min(valor_origem) AS menor_valor_no_app, max(valor_origem) AS maior_valor_no_app
FROM trat.revisao_dados
GROUP BY teste, motivo_revisao ORDER BY teste, motivo_revisao;

-- 4. Conversões por teste: valores antes e depois. Conferir se nenhum valor convertido
--    era, na verdade, um valor certo e pequeno.
SELECT teste, count(*) AS convertidas,
       min(valor_origem) AS menor_antes, max(valor_origem) AS maior_antes,
       min(valor) AS menor_depois, max(valor) AS maior_depois
FROM trat.medida WHERE convertido
GROUP BY teste ORDER BY teste;

-- 5. Tempo na velocidade máxima maior que o tempo total do VO2 (bug 2 do relatório de QA).
--    Esperado: 0. Hoje esses valores entram como válidos.
SELECT count(*) AS avaliacoes_com_tempo_vel_max_maior_que_total
FROM trat.resultado_teste vm
JOIN trat.resultado_teste tt
  ON tt.avaliacao_id = vm.avaliacao_id AND tt.teste = 'teste_vo2_tempo_total'
WHERE vm.teste = 'teste_vo2_tempo_vel_max' AND vm.valor > tt.valor;

-- 6. Comparações afetadas pelo arredondamento do "estável" (bug 3): variação real entre
--    1,95% e 2% que sai como melhorou/piorou.
SELECT count(*) AS comparacoes_afetadas
FROM api.comparacao
WHERE valor_anterior IS NOT NULL AND valor_anterior <> 0
  AND abs((valor_atual - valor_anterior) / valor_anterior * 100) >= 1.95
  AND abs((valor_atual - valor_anterior) / valor_anterior * 100) < 2
  AND situacao IN ('melhorou', 'piorou');

-- 7. Tentativa repetida (mesma avaliação, teste, lado e número). Esperado: 0.
SELECT count(*) AS tentativas_duplicadas FROM (
  SELECT avaliacao_id, teste, lado, tentativa
  FROM trat.medida GROUP BY 1, 2, 3, 4 HAVING count(*) > 1) d;

-- 8. Situação das reavaliações e das comparações, para o resumo.
SELECT 'reavaliacao' AS view, situacao, count(*) FROM api.reavaliacao GROUP BY situacao
UNION ALL
SELECT 'comparacao', situacao, count(*) FROM api.comparacao GROUP BY situacao
ORDER BY 1, 2;

-- 9. Data de "hoje" usada pelas views (bug 4): o Supabase roda em UTC.
--    Das 21h às 24h de Brasília, current_date já é o dia seguinte.
SELECT current_setting('TimeZone') AS fuso_do_banco, current_date AS hoje_nas_views_de_avaliacao,
       (now() AT TIME ZONE 'America/Sao_Paulo')::date AS hoje_em_sao_paulo;
