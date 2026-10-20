-- Tarefa 2.1 / Conferência 2: valores preenchidos no JSON de testes físicos.
-- Fonte exclusiva: origem.physical_test_sessions.data (jsonb).
-- Regra: NULL e strings vazias/brancas não são preenchidos. Zero numérico,
-- booleanos, objetos e arrays não nulos são preenchidos. A consulta também
-- expõe chaves presentes com valor NULL ou string vazia para auditoria.

SELECT
    k.key AS chave_json,
    COUNT(*) AS ocorrencias_da_chave,
    COUNT(*) FILTER (
        WHERE jsonb_typeof(s.data -> k.key) <> 'null'
          AND (
              jsonb_typeof(s.data -> k.key) <> 'string'
              OR NULLIF(BTRIM(s.data ->> k.key), '') IS NOT NULL
          )
    ) AS valores_preenchidos,
    COUNT(*) FILTER (
        WHERE jsonb_typeof(s.data -> k.key) = 'null'
           OR (
               jsonb_typeof(s.data -> k.key) = 'string'
               AND NULLIF(BTRIM(s.data ->> k.key), '') IS NULL
           )
    ) AS valores_vazios
FROM origem.physical_test_sessions AS s
CROSS JOIN LATERAL jsonb_object_keys(s.data) AS k(key)
GROUP BY k.key
ORDER BY k.key;

SELECT
    COUNT(*) AS sessoes,
    COUNT(*) FILTER (WHERE data IS NULL) AS data_nula,
    COUNT(*) FILTER (WHERE data = '{}'::jsonb) AS objeto_vazio,
    COUNT(*) FILTER (WHERE data = '[]'::jsonb) AS array_vazio,
    COUNT(*) FILTER (WHERE data IS NOT NULL AND data <> '{}'::jsonb AND data <> '[]'::jsonb) AS json_com_conteudo
FROM origem.physical_test_sessions;
