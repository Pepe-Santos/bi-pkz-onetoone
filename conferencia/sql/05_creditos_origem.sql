-- Tarefa 2.1 / Confer?ncia 5: cr?ditos na origem.
-- Fonte exclusiva: origem.athletes e origem.credit_transactions.
--
-- A consulta separa quatro conceitos:
-- 1) saldos materializados na origem;
-- 2) soma hist?rica de todos os lan?amentos;
-- 3) saldo reconstruido com reinicio em 10 na ultima renovacao;
-- 4) diferencas entre o saldo reconstruido e o materializado.
--
-- O servico so e inferido quando o motivo o identifica: [fisio], [nutri],
-- "mensal fisio", "mensal nutri", "mensal PKZ" ou "semanal treino".
-- Renovacoes mensais genericas ficam sem servico, pois nao ha evidencia
-- suficiente para atribui-las a um servico.
-- A renova??o n?o ? somada como delta: ela apenas define o marco e reinicia
-- o saldo em 10. Somente lancamentos posteriores entram no saldo reconstruido.

WITH lancamentos AS (
    SELECT
        ct.*,
        CASE
            WHEN ct.reason ILIKE '%fisio%' THEN 'fisioterapia'
            WHEN ct.reason ILIKE '%nutri%' THEN 'nutricao'
            WHEN ct.reason ILIKE '%treino%' OR ct.reason ILIKE '%PKZ%' THEN 'treino'
            ELSE NULL
        END AS servico_inferido,
        ct.reason ILIKE 'Renovação%'
            AND (
                ct.reason ILIKE '%fisio%'
                OR ct.reason ILIKE '%nutri%'
                OR ct.reason ILIKE '%PKZ%'
                OR ct.reason ILIKE '%treino%'
            ) AS renovacao_com_servico
    FROM origem.credit_transactions AS ct
),
ultima_renovacao AS (
    SELECT
        athlete_id,
        servico_inferido,
        MAX(created_at) AS ultima_renovacao_em
    FROM lancamentos
    WHERE renovacao_com_servico
    GROUP BY athlete_id, servico_inferido
),
saldo_reconstruido AS (
    SELECT
        u.athlete_id,
        u.servico_inferido,
        10 + COALESCE(SUM(l.delta) FILTER (WHERE l.created_at > u.ultima_renovacao_em), 0)::integer AS saldo_reconstruido,
        COUNT(l.id) FILTER (WHERE l.created_at > u.ultima_renovacao_em) AS lancamentos_posteriores,
        MAX(l.created_at) FILTER (WHERE l.created_at > u.ultima_renovacao_em) AS ultimo_lancamento_em,
        u.ultima_renovacao_em
    FROM ultima_renovacao AS u
    LEFT JOIN lancamentos AS l
      ON l.athlete_id = u.athlete_id
     AND l.servico_inferido = u.servico_inferido
    GROUP BY u.athlete_id, u.servico_inferido, u.ultima_renovacao_em
)
SELECT
    a.id AS athlete_id,
    a.name,
    sr.servico_inferido,
    sr.ultima_renovacao_em,
    sr.lancamentos_posteriores,
    sr.saldo_reconstruido,
    CASE sr.servico_inferido
        WHEN 'treino' THEN a.credits
        WHEN 'fisioterapia' THEN a.credits_fisio
        WHEN 'nutricao' THEN a.credits_nutri
    END AS saldo_materializado,
    sr.saldo_reconstruido - CASE sr.servico_inferido
        WHEN 'treino' THEN a.credits
        WHEN 'fisioterapia' THEN a.credits_fisio
        WHEN 'nutricao' THEN a.credits_nutri
    END AS diferenca_reconstruido_materializado,
    sr.ultimo_lancamento_em
FROM saldo_reconstruido AS sr
JOIN origem.athletes AS a ON a.id = sr.athlete_id
ORDER BY a.name, sr.servico_inferido;

SELECT
    COUNT(*) AS comparacoes,
    COUNT(*) FILTER (WHERE diferenca_reconstruido_materializado = 0) AS sem_divergencia,
    COUNT(*) FILTER (WHERE diferenca_reconstruido_materializado <> 0) AS com_divergencia,
    SUM(ABS(diferenca_reconstruido_materializado)) AS diferenca_absoluta_total
FROM (
    WITH lancamentos AS (
        SELECT
            ct.*,
            CASE
                WHEN ct.reason ILIKE '%fisio%' THEN 'fisioterapia'
                WHEN ct.reason ILIKE '%nutri%' THEN 'nutricao'
                WHEN ct.reason ILIKE '%treino%' OR ct.reason ILIKE '%PKZ%' THEN 'treino'
            END AS servico_inferido,
            ct.reason ILIKE 'Renovação%'
                AND (ct.reason ILIKE '%fisio%' OR ct.reason ILIKE '%nutri%' OR ct.reason ILIKE '%PKZ%' OR ct.reason ILIKE '%treino%') AS renovacao_com_servico
        FROM origem.credit_transactions AS ct
    ),
    renovacoes AS (
        SELECT athlete_id, servico_inferido, MAX(created_at) AS ultima_renovacao_em
        FROM lancamentos
        WHERE renovacao_com_servico
        GROUP BY athlete_id, servico_inferido
    ),
    comparacao AS (
        SELECT
            r.servico_inferido,
            10 + COALESCE(SUM(l.delta) FILTER (WHERE l.created_at > r.ultima_renovacao_em), 0)::integer
                - CASE r.servico_inferido
                    WHEN 'treino' THEN a.credits
                    WHEN 'fisioterapia' THEN a.credits_fisio
                    WHEN 'nutricao' THEN a.credits_nutri
                  END AS diferenca_reconstruido_materializado
        FROM renovacoes AS r
        JOIN origem.athletes AS a ON a.id = r.athlete_id
        LEFT JOIN lancamentos AS l
          ON l.athlete_id = r.athlete_id
         AND l.servico_inferido = r.servico_inferido
        GROUP BY r.athlete_id, r.servico_inferido, r.ultima_renovacao_em, a.credits, a.credits_fisio, a.credits_nutri
    )
    SELECT diferenca_reconstruido_materializado FROM comparacao
) AS resultado;

SELECT
    reason,
    COUNT(*) AS quantidade_renovacoes_sem_servico,
    SUM(delta) AS soma_delta
FROM origem.credit_transactions
WHERE reason ILIKE 'Renovação%'
  AND reason NOT ILIKE '%fisio%'
  AND reason NOT ILIKE '%nutri%'
  AND reason NOT ILIKE '%PKZ%'
  AND reason NOT ILIKE '%treino%'
GROUP BY reason
ORDER BY reason;

SELECT
    COUNT(*) AS quantidade_lancamentos,
    COUNT(DISTINCT athlete_id) AS alunos_com_lancamentos,
    COALESCE(SUM(delta), 0) AS total_delta_extrato,
    MIN(created_at) AS primeiro_lancamento,
    MAX(created_at) AS ultimo_lancamento
FROM origem.credit_transactions;

SELECT
    reason,
    COUNT(*) AS quantidade_lancamentos,
    SUM(delta) AS soma_delta
FROM origem.credit_transactions
GROUP BY reason
ORDER BY reason;

SELECT
    COUNT(*) AS quantidade_alunos,
    COALESCE(SUM(credits), 0) AS total_saldo_treino_materializado,
    COALESCE(SUM(credits_fisio), 0) AS total_saldo_fisio_materializado,
    COALESCE(SUM(credits_nutri), 0) AS total_saldo_nutri_materializado
FROM origem.athletes;
