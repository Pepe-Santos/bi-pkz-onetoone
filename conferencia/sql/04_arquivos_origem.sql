-- Tarefa 2.1 / Conferência 4: exatamente as nove colunas de caminho usadas
-- pelo modelo novo.arquivo, identificadas no comentário do banco e confirmadas
-- contra o catálogo de colunas do schema origem.
-- Fonte exclusiva: schema origem.
-- Regra: NULL ou texto vazio/branco = não preenchido.

WITH candidatas AS (
    SELECT 'origem.student_files.storage_path' AS coluna, storage_path AS referencia FROM origem.student_files
    UNION ALL SELECT 'origem.nutritionist_files.storage_path', storage_path FROM origem.nutritionist_files
    UNION ALL SELECT 'origem.physio_evolutions.storage_path', storage_path FROM origem.physio_evolutions
    UNION ALL SELECT 'origem.specialist_evolutions.file_path', file_path FROM origem.specialist_evolutions
    UNION ALL SELECT 'origem.training_reports.file_path', file_path FROM origem.training_reports
    UNION ALL SELECT 'origem.training_reports.pdf_storage_path', pdf_storage_path FROM origem.training_reports
    UNION ALL SELECT 'origem.physical_test_comparisons.file_path', file_path FROM origem.physical_test_comparisons
    UNION ALL SELECT 'origem.physio_assessments.file_path', file_path FROM origem.physio_assessments
    UNION ALL SELECT 'origem.student_tests.file_path', file_path FROM origem.student_tests
)
SELECT
    coluna,
    COUNT(*) FILTER (WHERE NULLIF(BTRIM(referencia), '') IS NOT NULL) AS referencias_preenchidas,
    COUNT(DISTINCT NULLIF(BTRIM(referencia), '')) AS caminhos_distintos
FROM candidatas
GROUP BY coluna
ORDER BY coluna;

WITH candidatas AS (
    SELECT 'origem.student_files.storage_path' AS coluna, storage_path AS referencia FROM origem.student_files
    UNION ALL SELECT 'origem.nutritionist_files.storage_path', storage_path FROM origem.nutritionist_files
    UNION ALL SELECT 'origem.physio_evolutions.storage_path', storage_path FROM origem.physio_evolutions
    UNION ALL SELECT 'origem.specialist_evolutions.file_path', file_path FROM origem.specialist_evolutions
    UNION ALL SELECT 'origem.training_reports.file_path', file_path FROM origem.training_reports
    UNION ALL SELECT 'origem.training_reports.pdf_storage_path', pdf_storage_path FROM origem.training_reports
    UNION ALL SELECT 'origem.physical_test_comparisons.file_path', file_path FROM origem.physical_test_comparisons
    UNION ALL SELECT 'origem.physio_assessments.file_path', file_path FROM origem.physio_assessments
    UNION ALL SELECT 'origem.student_tests.file_path', file_path FROM origem.student_tests
)
SELECT DISTINCT
    coluna,
    NULLIF(BTRIM(referencia), '') AS caminho
FROM candidatas
WHERE NULLIF(BTRIM(referencia), '') IS NOT NULL
ORDER BY coluna, caminho;
