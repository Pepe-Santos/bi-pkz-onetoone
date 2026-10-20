-- Tarefa 2.1 / Conferencia 5: creditos na origem.
-- Fonte exclusiva: origem.athletes e origem.credit_transactions.
-- A reconstrucao usa evidencias textuais inequivocas; renovacoes genericas ficam inconclusivas.
-- O saldo reinicia no delta da renovacao mais recente e soma cada evento posterior uma vez,
-- usando created_at e id como ordenacao deterministica.

WITH lancamentos AS (
    SELECT ct.*,
        CASE
            WHEN reason ILIKE '%fisioterapia%' OR reason ILIKE '%fisioterapeuta%' OR reason ILIKE '%[fisio]%' OR reason ILIKE '%mensal fisio%' THEN 'fisioterapia'
            WHEN reason ILIKE '%nutricionista%' OR reason ILIKE '%[nutri]%' OR reason ILIKE '%mensal nutri%' THEN 'nutricao'
            WHEN reason ILIKE U&'Renova\00E7\00E3o semanal treino%' OR reason ILIKE U&'Renova\00E7\00E3o mensal PKZ%' OR (reason ILIKE '%[treino]%' AND reason NOT ILIKE '%fisioterapeuta%' AND reason NOT ILIKE '%nutricionista%' AND reason NOT ILIKE '%psicologo%') THEN 'treino'
            ELSE NULL
        END AS servico_inferido,
        reason ILIKE U&'Renova\00E7\00E3o%' AS eh_renovacao
    FROM origem.credit_transactions AS ct
), ultima_renovacao AS (
    SELECT DISTINCT ON (athlete_id, servico_inferido) athlete_id, servico_inferido, id AS renovacao_id, created_at AS renovacao_em, delta AS delta_renovacao
    FROM lancamentos WHERE servico_inferido IS NOT NULL AND eh_renovacao
    ORDER BY athlete_id, servico_inferido, created_at DESC, id DESC
), saldo_reconstruido AS (
    SELECT r.athlete_id, r.servico_inferido, r.renovacao_id, r.renovacao_em, r.delta_renovacao,
        r.delta_renovacao + COALESCE(SUM(l.delta), 0)::integer AS saldo_reconstruido,
        COUNT(l.id) AS lancamentos_posteriores, MAX(l.created_at) AS ultimo_lancamento_em
    FROM ultima_renovacao r
    LEFT JOIN lancamentos l ON l.athlete_id = r.athlete_id AND l.servico_inferido = r.servico_inferido AND (l.created_at, l.id) > (r.renovacao_em, r.renovacao_id)
    GROUP BY r.athlete_id, r.servico_inferido, r.renovacao_id, r.renovacao_em, r.delta_renovacao
)
SELECT a.id AS athlete_id, a.name, sr.servico_inferido, sr.renovacao_id, sr.renovacao_em, sr.delta_renovacao,
    sr.lancamentos_posteriores, sr.saldo_reconstruido,
    CASE sr.servico_inferido WHEN 'treino' THEN a.credits WHEN 'fisioterapia' THEN a.credits_fisio WHEN 'nutricao' THEN a.credits_nutri END AS saldo_materializado,
    sr.saldo_reconstruido - CASE sr.servico_inferido WHEN 'treino' THEN a.credits WHEN 'fisioterapia' THEN a.credits_fisio WHEN 'nutricao' THEN a.credits_nutri END AS diferenca_reconstruido_materializado,
    sr.ultimo_lancamento_em
FROM saldo_reconstruido sr JOIN origem.athletes a ON a.id = sr.athlete_id
ORDER BY a.name, sr.servico_inferido;

WITH lancamentos AS (
    SELECT ct.*,
        CASE
            WHEN reason ILIKE '%fisioterapia%' OR reason ILIKE '%fisioterapeuta%' OR reason ILIKE '%[fisio]%' OR reason ILIKE '%mensal fisio%' THEN 'fisioterapia'
            WHEN reason ILIKE '%nutricionista%' OR reason ILIKE '%[nutri]%' OR reason ILIKE '%mensal nutri%' THEN 'nutricao'
            WHEN reason ILIKE U&'Renova\00E7\00E3o semanal treino%' OR reason ILIKE U&'Renova\00E7\00E3o mensal PKZ%' OR (reason ILIKE '%[treino]%' AND reason NOT ILIKE '%fisioterapeuta%' AND reason NOT ILIKE '%nutricionista%' AND reason NOT ILIKE '%psicologo%') THEN 'treino'
        END AS servico_inferido, reason ILIKE U&'Renova\00E7\00E3o%' AS eh_renovacao
    FROM origem.credit_transactions ct
), ultima_renovacao AS (
    SELECT DISTINCT ON (athlete_id, servico_inferido) athlete_id, servico_inferido, id AS renovacao_id, created_at AS renovacao_em, delta AS delta_renovacao
    FROM lancamentos WHERE servico_inferido IS NOT NULL AND eh_renovacao
    ORDER BY athlete_id, servico_inferido, created_at DESC, id DESC
), comparacoes AS (
    SELECT r.athlete_id, r.servico_inferido, r.delta_renovacao + COALESCE(SUM(l.delta), 0)::integer AS saldo_reconstruido,
        CASE r.servico_inferido WHEN 'treino' THEN a.credits WHEN 'fisioterapia' THEN a.credits_fisio WHEN 'nutricao' THEN a.credits_nutri END AS saldo_materializado
    FROM ultima_renovacao r JOIN origem.athletes a ON a.id = r.athlete_id
    LEFT JOIN lancamentos l ON l.athlete_id = r.athlete_id AND l.servico_inferido = r.servico_inferido AND (l.created_at, l.id) > (r.renovacao_em, r.renovacao_id)
    GROUP BY r.athlete_id, r.servico_inferido, r.delta_renovacao, a.credits, a.credits_fisio, a.credits_nutri
)
SELECT servico_inferido AS servico, COUNT(*) AS comparacoes, COUNT(*) FILTER (WHERE saldo_reconstruido = saldo_materializado) AS correspondencias, COUNT(*) FILTER (WHERE saldo_reconstruido <> saldo_materializado) AS divergencias, COUNT(*) FILTER (WHERE saldo_reconstruido IS NULL OR saldo_materializado IS NULL) AS inconclusivos, COALESCE(SUM(ABS(saldo_reconstruido - saldo_materializado)), 0) AS diferenca_absoluta_total
FROM comparacoes GROUP BY servico_inferido ORDER BY servico_inferido;

WITH lancamentos AS (
    SELECT ct.*,
        CASE
            WHEN reason ILIKE '%fisioterapia%' OR reason ILIKE '%fisioterapeuta%' OR reason ILIKE '%[fisio]%' OR reason ILIKE '%mensal fisio%' THEN 'fisioterapia'
            WHEN reason ILIKE '%nutricionista%' OR reason ILIKE '%[nutri]%' OR reason ILIKE '%mensal nutri%' THEN 'nutricao'
            WHEN reason ILIKE U&'Renova\00E7\00E3o semanal treino%' OR reason ILIKE U&'Renova\00E7\00E3o mensal PKZ%' OR (reason ILIKE '%[treino]%' AND reason NOT ILIKE '%fisioterapeuta%' AND reason NOT ILIKE '%nutricionista%' AND reason NOT ILIKE '%psicologo%') THEN 'treino'
        END AS servico_inferido,
        reason ILIKE U&'Renova\00E7\00E3o%' AS eh_renovacao
    FROM origem.credit_transactions AS ct
), servicos_observados AS (
    SELECT DISTINCT athlete_id, servico_inferido
    FROM lancamentos
    WHERE servico_inferido IS NOT NULL
), renovacoes AS (
    SELECT DISTINCT ON (athlete_id, servico_inferido) athlete_id, servico_inferido, id
    FROM lancamentos
    WHERE servico_inferido IS NOT NULL AND eh_renovacao
    ORDER BY athlete_id, servico_inferido, created_at DESC, id DESC
)
SELECT s.servico_inferido AS servico, COUNT(*) AS servicos_observados, COUNT(r.id) AS com_renovacao_identificavel, COUNT(*) FILTER (WHERE r.id IS NULL) AS inconclusivos_sem_renovacao
FROM servicos_observados s
LEFT JOIN renovacoes r USING (athlete_id, servico_inferido)
GROUP BY s.servico_inferido
ORDER BY s.servico_inferido;

SELECT COUNT(*) AS quantidade_lancamentos, COUNT(DISTINCT athlete_id) AS alunos_com_lancamentos, COALESCE(SUM(delta), 0) AS total_delta_extrato, MIN(created_at) AS primeiro_lancamento, MAX(created_at) AS ultimo_lancamento FROM origem.credit_transactions;
SELECT reason, COUNT(*) AS quantidade_lancamentos, SUM(delta) AS soma_delta FROM origem.credit_transactions GROUP BY reason ORDER BY reason;
SELECT reason, COUNT(*) AS quantidade_renovacoes_sem_servico, SUM(delta) AS soma_delta FROM origem.credit_transactions WHERE reason ILIKE U&'Renova\00E7\00E3o%' AND reason NOT ILIKE '%fisioterapia%' AND reason NOT ILIKE '%fisioterapeuta%' AND reason NOT ILIKE '%fisio%' AND reason NOT ILIKE '%nutricionista%' AND reason NOT ILIKE '%nutri%' AND reason NOT ILIKE '%PKZ%' AND reason NOT ILIKE '%treino%' GROUP BY reason ORDER BY reason;
SELECT COUNT(*) AS quantidade_alunos, COALESCE(SUM(credits), 0) AS total_saldo_treino_materializado, COALESCE(SUM(credits_fisio), 0) AS total_saldo_fisio_materializado, COALESCE(SUM(credits_nutri), 0) AS total_saldo_nutri_materializado FROM origem.athletes;
