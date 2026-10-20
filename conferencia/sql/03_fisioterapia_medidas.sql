-- Tarefa 2.1 / Conferência 3: medidas não nulas por avaliação de fisioterapia.
-- Fonte exclusiva: origem.physio_assessments.
-- As 14 colunas abaixo foram confirmadas no catálogo de colunas da origem.
-- Zero é valor preenchido; somente NULL é contado como ausente.

SELECT
    medida,
    COUNT(*) AS total_avaliacoes,
    COUNT(*) FILTER (WHERE valor IS NOT NULL) AS medidas_nao_nulas,
    COUNT(*) FILTER (WHERE valor IS NULL) AS medidas_nulas
FROM origem.physio_assessments AS p
CROSS JOIN LATERAL (
    VALUES
        ('cotovelo_ext_dir', p.cotovelo_ext_dir),
        ('cotovelo_ext_esq', p.cotovelo_ext_esq),
        ('cotovelo_flex_dir', p.cotovelo_flex_dir),
        ('cotovelo_flex_esq', p.cotovelo_flex_esq),
        ('joelho_ext_dir', p.joelho_ext_dir),
        ('joelho_ext_esq', p.joelho_ext_esq),
        ('joelho_flex_dir', p.joelho_flex_dir),
        ('joelho_flex_esq', p.joelho_flex_esq),
        ('ombro_abd_dir', p.ombro_abd_dir),
        ('ombro_abd_esq', p.ombro_abd_esq),
        ('ombro_rot_ext_dir', p.ombro_rot_ext_dir),
        ('ombro_rot_ext_esq', p.ombro_rot_ext_esq),
        ('quadril_dir', p.quadril_dir),
        ('quadril_esq', p.quadril_esq)
) AS medidas(medida, valor)
GROUP BY medida
ORDER BY medida;
