-- =============================================================================
-- 60_carga_avaliacao.sql
-- Domínio: avaliacao               Dono: Micael (Frente 1)
-- Origem:  origem.physical_test_sessions (teste físico: data jsonb, altura, peso),
--          origem.weekly_evaluations (avaliação semanal)
-- Destino: novo.metrica (catálogo das 109 métricas, inclusive as de fisioterapia
--          que o script 70 usa), novo.avaliacao, novo.avaliacao_medida
-- Depende de: migrations 001–011; scripts 10–50
-- Mapeamento: mapeamento/avaliacao.csv, mapeamento/avaliacao_metricas.csv
-- Não migram: physical_test_comparisons (só o PDF, script 80) e student_tests
-- (resultado nulo em todas as linhas).
-- =============================================================================
\set ON_ERROR_STOP on

begin;

select set_config('novo.modo_carga', 'on', true);

-- -----------------------------------------------------------------------------
-- c1) metrica: catálogo gerado de mapeamento/avaliacao_metricas.csv
--   valor_min/valor_max ficam nulos até a pendência 2 definir as faixas.
-- -----------------------------------------------------------------------------
insert into novo.metrica as m (codigo, nome, dominio, unidade_medida, tipo_dado, direcao_desejada,
                               usa_lado, ativo, ordem, pendencia)
select v.codigo, v.nome, v.dominio, v.unidade_medida, v.tipo_dado, v.direcao_desejada,
       v.usa_lado, true, v.ordem, v.pendencia
from (values
  (1, 'banco_wells', 'Banco de Wells', 'teste_fisico', 'cm', 'numero', 'maior', false, 'unidade e faixa a confirmar (pendência 2)'),
  (2, 'sprint_10', 'Sprint 10 m', 'teste_fisico', 's', 'numero', 'menor', false, 'unidade e faixa a confirmar (pendência 2)'),
  (3, 'sprint_20', 'Sprint 20 m', 'teste_fisico', 's', 'numero', 'menor', false, 'unidade e faixa a confirmar (pendência 2)'),
  (4, 'illinois', 'Teste de Illinois', 'teste_fisico', 's', 'numero', 'menor', false, 'unidade e faixa a confirmar (pendência 2)'),
  (5, 'slalom_wallball', 'Slalom com bola / Arremesso de Wall Ball', 'teste_fisico', null, 'numero', null, false, 'unidade e direção desejada a confirmar (pendência 3)'),
  (6, 'estabilidade_aquabag', 'Estabilidade Aquabag (nº de desequilíbrios)', 'teste_fisico', 'desequilibrios', 'numero', 'menor', false, 'unidade e faixa a confirmar (pendência 2)'),
  (7, 'blazepod_foco', 'Blazepod / Foco', 'teste_fisico', 'hits', 'numero', 'maior', false, 'unidade e faixa a confirmar (pendência 2)'),
  (8, 'single_hop', 'Single Hop Test', 'teste_fisico', 'cm', 'numero', 'maior', true, 'unidade e faixa a confirmar (pendência 2)'),
  (9, 'cross_hop', 'Cross Hop Test', 'teste_fisico', 'cm', 'numero', 'maior', true, 'unidade e faixa a confirmar (pendência 2)'),
  (10, 'saltos_vert_squat_jump', 'Saltos verticais: Squat Jump', 'teste_fisico', 'cm', 'numero', 'maior', false, 'unidade e faixa a confirmar (pendência 2)'),
  (11, 'saltos_vert_countermovement', 'Saltos verticais: Countermovement Jump', 'teste_fisico', 'cm', 'numero', 'maior', false, 'unidade e faixa a confirmar (pendência 2)'),
  (12, 'saltos_vert_abalakov', 'Saltos verticais: Abalakov', 'teste_fisico', 'cm', 'numero', 'maior', false, 'unidade e faixa a confirmar (pendência 2)'),
  (13, 'blazepod_vel_reacao_hits', 'Blazepod / Velocidade de reação: hits', 'teste_fisico', 'hits', 'numero', 'maior', false, 'unidade e faixa a confirmar (pendência 2)'),
  (14, 'blazepod_vel_reacao_ms', 'Blazepod / Velocidade de reação: tempo', 'teste_fisico', 'ms', 'numero', 'menor', false, 'unidade e faixa a confirmar (pendência 2)'),
  (15, 'blazepod_vel_reacao_legado', 'Blazepod / Velocidade de reação (formato antigo)', 'teste_fisico', null, 'texto', null, false, 'formato antigo: não dá para saber se é hits ou ms'),
  (16, 'teste_vo2_vel_max', 'Teste VO2: velocidade máxima', 'teste_fisico', 'km/h', 'numero', 'maior', false, 'unidade e faixa a confirmar (pendência 2)'),
  (17, 'teste_vo2_tempo_total', 'Teste VO2: tempo total', 'teste_fisico', 's', 'numero', 'maior', false, 'unidade e faixa a confirmar (pendência 2)'),
  (18, 'teste_vo2_distancia_total', 'Teste VO2: distância total', 'teste_fisico', 'm', 'numero', 'maior', false, 'unidade e faixa a confirmar (pendência 2)'),
  (19, 'teste_vo2_tempo_vel_max', 'Teste VO2: tempo na velocidade máxima', 'teste_fisico', 's', 'numero', 'maior', false, 'unidade e faixa a confirmar (pendência 2)'),
  (20, 'antropometria_altura', 'Altura', 'antropometria', null, 'numero', 'nenhuma', false, 'unidade ambígua: metros e centímetros misturados (pendência 2)'),
  (21, 'antropometria_peso', 'Peso', 'antropometria', 'kg', 'numero', 'nenhuma', false, null),
  (22, 'semanal_ambiente', 'Avaliação semanal: Ambiente', 'semanal', 'escala_1_5', 'escala', 'maior', false, null),
  (23, 'semanal_evolucao', 'Avaliação semanal: Evolução', 'semanal', 'escala_1_5', 'escala', 'maior', false, null),
  (24, 'semanal_qualidade', 'Avaliação semanal: Qualidade', 'semanal', 'escala_1_5', 'escala', 'maior', false, null),
  (25, 'semanal_satisfacao', 'Avaliação semanal: Satisfação', 'semanal', 'escala_1_5', 'escala', 'maior', false, null),
  (26, 'semanal_atendimento', 'Avaliação semanal: Atendimento', 'semanal', 'escala_1_5', 'escala', 'maior', false, null),
  (27, 'fisio_cotovelo_ext', 'Goniometria: Extensão de cotovelo', 'fisioterapia', 'graus', 'numero', null, true, 'unidade a confirmar (graus)'),
  (28, 'fisio_cotovelo_flex', 'Goniometria: Flexão de cotovelo', 'fisioterapia', 'graus', 'numero', null, true, 'unidade a confirmar (graus)'),
  (29, 'fisio_joelho_ext', 'Goniometria: Extensão de joelho', 'fisioterapia', 'graus', 'numero', null, true, 'unidade a confirmar (graus)'),
  (30, 'fisio_joelho_flex', 'Goniometria: Flexão de joelho', 'fisioterapia', 'graus', 'numero', null, true, 'unidade a confirmar (graus)'),
  (31, 'fisio_ombro_abd', 'Goniometria: Abdução de ombro', 'fisioterapia', 'graus', 'numero', null, true, 'unidade a confirmar (graus)'),
  (32, 'fisio_ombro_rot_ext', 'Goniometria: Rotação externa de ombro', 'fisioterapia', 'graus', 'numero', null, true, 'unidade a confirmar (graus)'),
  (33, 'fisio_quadril', 'Goniometria: Quadril', 'fisioterapia', 'graus', 'numero', null, true, 'unidade a confirmar (graus)'),
  (34, 'fisio_appley_sup', 'Teste de Appley (superior)', 'fisioterapia', null, 'texto', null, true, null),
  (35, 'fisio_appley_inf', 'Teste de Appley (inferior)', 'fisioterapia', null, 'texto', null, true, null),
  (36, 'fisio_pkz_forca_ext_quadril', 'Força: Extensão de quadril', 'fisioterapia', 'kg', 'numero', 'maior', true, 'kg a confirmar'),
  (37, 'fisio_pkz_forca_flex_quadril', 'Força: Flexão de quadril', 'fisioterapia', 'kg', 'numero', 'maior', true, 'kg a confirmar'),
  (38, 'fisio_pkz_forca_ext_joelho', 'Força: Extensão de joelho', 'fisioterapia', 'kg', 'numero', 'maior', true, 'kg a confirmar'),
  (39, 'fisio_pkz_forca_flex_joelho', 'Força: Flexão de joelho', 'fisioterapia', 'kg', 'numero', 'maior', true, 'kg a confirmar'),
  (40, 'fisio_pkz_forca_aducao_quadril', 'Força: Adução de quadril', 'fisioterapia', 'kg', 'numero', 'maior', true, 'kg a confirmar'),
  (41, 'fisio_pkz_forca_abducao_quadril', 'Força: Abdução de quadril', 'fisioterapia', 'kg', 'numero', 'maior', true, 'kg a confirmar'),
  (42, 'fisio_pkz_forca_abdominal', 'Força abdominal', 'fisioterapia', null, 'numero', 'maior', false, 'unidade a confirmar'),
  (43, 'fisio_pkz_ratio_flexext_quadril', 'Relação de força: Flexores / extensores de quadril (ref. 60–80%)', 'fisioterapia', '%', 'numero', 'nenhuma', true, null),
  (44, 'fisio_pkz_ratio_flexext_joelho', 'Relação de força: Flexores / extensores de joelho (ref. 50–70%)', 'fisioterapia', '%', 'numero', 'nenhuma', true, null),
  (45, 'fisio_pkz_ratio_aduabd_quadril', 'Relação de força: Adução / abdução de quadril (ref. 100–120%)', 'fisioterapia', '%', 'numero', 'nenhuma', true, null),
  (46, 'fisio_pkz_mob_tornozelo', 'Mobilidade de tornozelo', 'fisioterapia', 'graus', 'numero', 'maior', true, null),
  (47, 'fisio_pkz_mob_flex_quadril_ca', 'Flexão de quadril (cadeia aberta)', 'fisioterapia', 'graus', 'numero', 'maior', true, null),
  (48, 'fisio_pkz_post_anterior_inclinacao_cabeca', 'Postura, vista anterior: Inclinação de cabeça (valor)', 'fisioterapia', null, 'numero', 'nenhuma', false, 'unidade a confirmar'),
  (49, 'fisio_pkz_post_anterior_inclinacao_cabeca_direcao', 'Postura, vista anterior: Inclinação de cabeça (direção)', 'fisioterapia', null, 'texto', null, false, null),
  (50, 'fisio_pkz_post_anterior_alinhamento_ombros', 'Postura, vista anterior: Alinhamento de ombros (valor)', 'fisioterapia', null, 'numero', 'nenhuma', false, 'unidade a confirmar'),
  (51, 'fisio_pkz_post_anterior_alinhamento_ombros_direcao', 'Postura, vista anterior: Alinhamento de ombros (direção)', 'fisioterapia', null, 'texto', null, false, null),
  (52, 'fisio_pkz_post_anterior_inclinacao_pelvica', 'Postura, vista anterior: Inclinação pélvica (valor)', 'fisioterapia', null, 'numero', 'nenhuma', false, 'unidade a confirmar'),
  (53, 'fisio_pkz_post_anterior_inclinacao_pelvica_direcao', 'Postura, vista anterior: Inclinação pélvica (direção)', 'fisioterapia', null, 'texto', null, false, null),
  (54, 'fisio_pkz_post_anterior_eias_patela', 'Postura, vista anterior: EIAS — patela (valor)', 'fisioterapia', null, 'numero', 'nenhuma', true, 'unidade a confirmar'),
  (55, 'fisio_pkz_post_anterior_eias_patela_direcao', 'Postura, vista anterior: EIAS — patela (direção)', 'fisioterapia', null, 'texto', null, true, null),
  (56, 'fisio_pkz_post_anterior_angulo_q', 'Postura, vista anterior: Ângulo Q (valor)', 'fisioterapia', null, 'numero', 'nenhuma', true, 'unidade a confirmar'),
  (57, 'fisio_pkz_post_anterior_angulo_q_direcao', 'Postura, vista anterior: Ângulo Q (direção)', 'fisioterapia', null, 'texto', null, true, null),
  (58, 'fisio_pkz_post_anterior_tibia', 'Postura, vista anterior: Tíbia (valor)', 'fisioterapia', null, 'numero', 'nenhuma', true, 'unidade a confirmar'),
  (59, 'fisio_pkz_post_anterior_tibia_direcao', 'Postura, vista anterior: Tíbia (direção)', 'fisioterapia', null, 'texto', null, true, null),
  (60, 'fisio_pkz_post_anterior_rotacao_pe', 'Postura, vista anterior: Rotação do pé (valor)', 'fisioterapia', null, 'numero', 'nenhuma', true, 'unidade a confirmar'),
  (61, 'fisio_pkz_post_anterior_rotacao_pe_direcao', 'Postura, vista anterior: Rotação do pé (direção)', 'fisioterapia', null, 'texto', null, true, null),
  (62, 'fisio_pkz_post_anterior_alinhamento_vertical', 'Postura, vista anterior: Alinhamento vertical (valor)', 'fisioterapia', null, 'numero', 'nenhuma', false, 'unidade a confirmar'),
  (63, 'fisio_pkz_post_anterior_alinhamento_vertical_direcao', 'Postura, vista anterior: Alinhamento vertical (direção)', 'fisioterapia', null, 'texto', null, false, null),
  (64, 'fisio_pkz_post_lateral_dir_inclinacao_cabeca_sagital', 'Postura, vista lateral direita: Inclinação de cabeça (sagital) (valor)', 'fisioterapia', null, 'numero', 'nenhuma', false, 'unidade a confirmar'),
  (65, 'fisio_pkz_post_lateral_dir_inclinacao_cabeca_sagital_direcao', 'Postura, vista lateral direita: Inclinação de cabeça (sagital) (direção)', 'fisioterapia', null, 'texto', null, false, null),
  (66, 'fisio_pkz_post_lateral_dir_craniovertebral', 'Postura, vista lateral direita: Craniovertebral (valor)', 'fisioterapia', null, 'numero', 'nenhuma', false, 'unidade a confirmar'),
  (67, 'fisio_pkz_post_lateral_dir_craniovertebral_direcao', 'Postura, vista lateral direita: Craniovertebral (direção)', 'fisioterapia', null, 'texto', null, false, null),
  (68, 'fisio_pkz_post_lateral_dir_cabeca_ombro', 'Postura, vista lateral direita: Cabeça — ombro (valor)', 'fisioterapia', null, 'numero', 'nenhuma', false, 'unidade a confirmar'),
  (69, 'fisio_pkz_post_lateral_dir_cabeca_ombro_direcao', 'Postura, vista lateral direita: Cabeça — ombro (direção)', 'fisioterapia', null, 'texto', null, false, null),
  (70, 'fisio_pkz_post_lateral_dir_inclinacao_pelvica', 'Postura, vista lateral direita: Inclinação pélvica (valor)', 'fisioterapia', null, 'numero', 'nenhuma', false, 'unidade a confirmar'),
  (71, 'fisio_pkz_post_lateral_dir_inclinacao_pelvica_direcao', 'Postura, vista lateral direita: Inclinação pélvica (direção)', 'fisioterapia', null, 'texto', null, false, null),
  (72, 'fisio_pkz_post_lateral_dir_alinhamento_quadril', 'Postura, vista lateral direita: Alinhamento de quadril (valor)', 'fisioterapia', null, 'numero', 'nenhuma', false, 'unidade a confirmar'),
  (73, 'fisio_pkz_post_lateral_dir_alinhamento_quadril_direcao', 'Postura, vista lateral direita: Alinhamento de quadril (direção)', 'fisioterapia', null, 'texto', null, false, null),
  (74, 'fisio_pkz_post_lateral_dir_alinhamento_joelho', 'Postura, vista lateral direita: Alinhamento de joelho (valor)', 'fisioterapia', null, 'numero', 'nenhuma', false, 'unidade a confirmar'),
  (75, 'fisio_pkz_post_lateral_dir_alinhamento_joelho_direcao', 'Postura, vista lateral direita: Alinhamento de joelho (direção)', 'fisioterapia', null, 'texto', null, false, null),
  (76, 'fisio_pkz_post_lateral_dir_flexao_joelho', 'Postura, vista lateral direita: Flexão de joelho (valor)', 'fisioterapia', null, 'numero', 'nenhuma', false, 'unidade a confirmar'),
  (77, 'fisio_pkz_post_lateral_dir_flexao_joelho_direcao', 'Postura, vista lateral direita: Flexão de joelho (direção)', 'fisioterapia', null, 'texto', null, false, null),
  (78, 'fisio_pkz_post_lateral_dir_alinhamento_vertical', 'Postura, vista lateral direita: Alinhamento vertical (valor)', 'fisioterapia', null, 'numero', 'nenhuma', false, 'unidade a confirmar'),
  (79, 'fisio_pkz_post_lateral_dir_alinhamento_vertical_direcao', 'Postura, vista lateral direita: Alinhamento vertical (direção)', 'fisioterapia', null, 'texto', null, false, null),
  (80, 'fisio_pkz_post_posterior_inclinacao_cabeca', 'Postura, vista posterior: Inclinação de cabeça (valor)', 'fisioterapia', null, 'numero', 'nenhuma', false, 'unidade a confirmar'),
  (81, 'fisio_pkz_post_posterior_inclinacao_cabeca_direcao', 'Postura, vista posterior: Inclinação de cabeça (direção)', 'fisioterapia', null, 'texto', null, false, null),
  (82, 'fisio_pkz_post_posterior_alinhamento_ombros', 'Postura, vista posterior: Alinhamento de ombros (valor)', 'fisioterapia', null, 'numero', 'nenhuma', false, 'unidade a confirmar'),
  (83, 'fisio_pkz_post_posterior_alinhamento_ombros_direcao', 'Postura, vista posterior: Alinhamento de ombros (direção)', 'fisioterapia', null, 'texto', null, false, null),
  (84, 'fisio_pkz_post_posterior_alinhamento_escapular', 'Postura, vista posterior: Alinhamento escapular (valor)', 'fisioterapia', null, 'numero', 'nenhuma', false, 'unidade a confirmar'),
  (85, 'fisio_pkz_post_posterior_alinhamento_escapular_direcao', 'Postura, vista posterior: Alinhamento escapular (direção)', 'fisioterapia', null, 'texto', null, false, null),
  (86, 'fisio_pkz_post_posterior_inclinacao_pelvica', 'Postura, vista posterior: Inclinação pélvica (valor)', 'fisioterapia', null, 'numero', 'nenhuma', false, 'unidade a confirmar'),
  (87, 'fisio_pkz_post_posterior_inclinacao_pelvica_direcao', 'Postura, vista posterior: Inclinação pélvica (direção)', 'fisioterapia', null, 'texto', null, false, null),
  (88, 'fisio_pkz_post_posterior_alinhamento_joelho', 'Postura, vista posterior: Alinhamento de joelho (valor)', 'fisioterapia', null, 'numero', 'nenhuma', false, 'unidade a confirmar'),
  (89, 'fisio_pkz_post_posterior_alinhamento_joelho_direcao', 'Postura, vista posterior: Alinhamento de joelho (direção)', 'fisioterapia', null, 'texto', null, false, null),
  (90, 'fisio_pkz_post_posterior_pronacao_pe', 'Postura, vista posterior: Pronação do pé (valor)', 'fisioterapia', null, 'numero', 'nenhuma', true, 'unidade a confirmar'),
  (91, 'fisio_pkz_post_posterior_pronacao_pe_direcao', 'Postura, vista posterior: Pronação do pé (direção)', 'fisioterapia', null, 'texto', null, true, null),
  (92, 'fisio_pkz_post_posterior_alinhamento_vertical', 'Postura, vista posterior: Alinhamento vertical (valor)', 'fisioterapia', null, 'numero', 'nenhuma', false, 'unidade a confirmar'),
  (93, 'fisio_pkz_post_posterior_alinhamento_vertical_direcao', 'Postura, vista posterior: Alinhamento vertical (direção)', 'fisioterapia', null, 'texto', null, false, null),
  (94, 'fisio_pkz_post_lateral_esq_inclinacao_cabeca_sagital', 'Postura, vista lateral esquerda: Inclinação de cabeça (sagital) (valor)', 'fisioterapia', null, 'numero', 'nenhuma', false, 'unidade a confirmar'),
  (95, 'fisio_pkz_post_lateral_esq_inclinacao_cabeca_sagital_direcao', 'Postura, vista lateral esquerda: Inclinação de cabeça (sagital) (direção)', 'fisioterapia', null, 'texto', null, false, null),
  (96, 'fisio_pkz_post_lateral_esq_craniovertebral', 'Postura, vista lateral esquerda: Craniovertebral (valor)', 'fisioterapia', null, 'numero', 'nenhuma', false, 'unidade a confirmar'),
  (97, 'fisio_pkz_post_lateral_esq_craniovertebral_direcao', 'Postura, vista lateral esquerda: Craniovertebral (direção)', 'fisioterapia', null, 'texto', null, false, null),
  (98, 'fisio_pkz_post_lateral_esq_cabeca_ombro', 'Postura, vista lateral esquerda: Cabeça — ombro (valor)', 'fisioterapia', null, 'numero', 'nenhuma', false, 'unidade a confirmar'),
  (99, 'fisio_pkz_post_lateral_esq_cabeca_ombro_direcao', 'Postura, vista lateral esquerda: Cabeça — ombro (direção)', 'fisioterapia', null, 'texto', null, false, null),
  (100, 'fisio_pkz_post_lateral_esq_inclinacao_pelvica', 'Postura, vista lateral esquerda: Inclinação pélvica (valor)', 'fisioterapia', null, 'numero', 'nenhuma', false, 'unidade a confirmar'),
  (101, 'fisio_pkz_post_lateral_esq_inclinacao_pelvica_direcao', 'Postura, vista lateral esquerda: Inclinação pélvica (direção)', 'fisioterapia', null, 'texto', null, false, null),
  (102, 'fisio_pkz_post_lateral_esq_alinhamento_quadril', 'Postura, vista lateral esquerda: Alinhamento de quadril (valor)', 'fisioterapia', null, 'numero', 'nenhuma', false, 'unidade a confirmar'),
  (103, 'fisio_pkz_post_lateral_esq_alinhamento_quadril_direcao', 'Postura, vista lateral esquerda: Alinhamento de quadril (direção)', 'fisioterapia', null, 'texto', null, false, null),
  (104, 'fisio_pkz_post_lateral_esq_alinhamento_joelho', 'Postura, vista lateral esquerda: Alinhamento de joelho (valor)', 'fisioterapia', null, 'numero', 'nenhuma', false, 'unidade a confirmar'),
  (105, 'fisio_pkz_post_lateral_esq_alinhamento_joelho_direcao', 'Postura, vista lateral esquerda: Alinhamento de joelho (direção)', 'fisioterapia', null, 'texto', null, false, null),
  (106, 'fisio_pkz_post_lateral_esq_flexao_joelho', 'Postura, vista lateral esquerda: Flexão de joelho (valor)', 'fisioterapia', null, 'numero', 'nenhuma', false, 'unidade a confirmar'),
  (107, 'fisio_pkz_post_lateral_esq_flexao_joelho_direcao', 'Postura, vista lateral esquerda: Flexão de joelho (direção)', 'fisioterapia', null, 'texto', null, false, null),
  (108, 'fisio_pkz_post_lateral_esq_alinhamento_vertical', 'Postura, vista lateral esquerda: Alinhamento vertical (valor)', 'fisioterapia', null, 'numero', 'nenhuma', false, 'unidade a confirmar'),
  (109, 'fisio_pkz_post_lateral_esq_alinhamento_vertical_direcao', 'Postura, vista lateral esquerda: Alinhamento vertical (direção)', 'fisioterapia', null, 'texto', null, false, null)
) v(ordem, codigo, nome, dominio, unidade_medida, tipo_dado, direcao_desejada, usa_lado, pendencia)
on conflict (codigo) do update
  set nome = excluded.nome, dominio = excluded.dominio, unidade_medida = excluded.unidade_medida,
      tipo_dado = excluded.tipo_dado, direcao_desejada = excluded.direcao_desejada,
      usa_lado = excluded.usa_lado, ativo = excluded.ativo, ordem = excluded.ordem,
      pendencia = novo.juntar_pendencia(m.pendencia, excluded.pendencia), atualizado_em = now();

-- -----------------------------------------------------------------------------
-- b) Rejeitados
-- -----------------------------------------------------------------------------
insert into novo.carga_rejeitado (script, tabela_origem, id_origem, motivo)
select 'avaliacao', 'physical_test_sessions', s.id,
       case when not exists (select 1 from novo.aluno a where a.id = s.athlete_id) then 'aluno inexistente no destino'
            else 'aluno sem matrícula no destino (sem unidade)' end
from origem.physical_test_sessions s
where not exists (select 1 from novo.aluno a where a.id = s.athlete_id)
   or novo.unidade_atual_do_aluno(s.athlete_id) is null
on conflict (script, tabela_origem, id_origem, motivo) do nothing;

insert into novo.carga_rejeitado (script, tabela_origem, id_origem, motivo)
select 'avaliacao', 'weekly_evaluations', w.id, 'aluno inexistente no destino'
from origem.weekly_evaluations w
where not exists (select 1 from novo.aluno a where a.id = w.athlete_id)
on conflict (script, tabela_origem, id_origem, motivo) do nothing;

-- -----------------------------------------------------------------------------
-- c2) avaliacao: teste físico
-- -----------------------------------------------------------------------------
insert into novo.avaliacao as av (id, aluno_id, unidade_id, tipo, data, avaliador_id, avaliador_nome, status,
                                  consolidada_em, observacoes, criado_por, pendencia, criado_em)
select s.id, s.athlete_id, novo.unidade_atual_do_aluno(s.athlete_id), 'teste_fisico', s.test_date,
       p.id,
       case when p.id is null then nullif(btrim(s.evaluator_name), '') end,
       'consolidada', s.created_at, s.observacoes,
       case when exists (select 1 from novo.perfil_usuario u where u.usuario_id = s.created_by) then s.created_by end,
       case when s.evaluator_id is not null and p.id is null then 'avaliador não encontrado no destino' end,
       s.created_at
from origem.physical_test_sessions s
join novo.aluno a on a.id = s.athlete_id
left join novo.profissional p on p.id = s.evaluator_id
where novo.unidade_atual_do_aluno(s.athlete_id) is not null
on conflict (id) do update
  set aluno_id = excluded.aluno_id, unidade_id = excluded.unidade_id, tipo = excluded.tipo, data = excluded.data,
      avaliador_id = excluded.avaliador_id, avaliador_nome = excluded.avaliador_nome, status = excluded.status,
      consolidada_em = excluded.consolidada_em, observacoes = excluded.observacoes, criado_por = excluded.criado_por,
      pendencia = novo.juntar_pendencia(av.pendencia, excluded.pendencia),
      criado_em = excluded.criado_em, atualizado_em = now();

-- -----------------------------------------------------------------------------
-- c3) avaliacao: semanal (unidade vem da própria avaliação; sem avaliador)
-- -----------------------------------------------------------------------------
insert into novo.avaliacao as av (id, aluno_id, unidade_id, tipo, data, avaliador_id, status,
                                  consolidada_em, observacoes, criado_por, pendencia, criado_em)
select w.id, w.athlete_id, u.id, 'semanal', w.week_start_date, null, 'consolidada', w.created_at,
       w.observations,
       case when exists (select 1 from novo.perfil_usuario pu where pu.usuario_id = w.created_by) then w.created_by end,
       case when u.id is distinct from novo.unidade_atual_do_aluno(w.athlete_id)
            then 'unidade da avaliação diferente da unidade do aluno' end,
       w.created_at
from origem.weekly_evaluations w
join novo.aluno a on a.id = w.athlete_id
join novo.unidade u on u.codigo = w.unit::text
on conflict (id) do update
  set aluno_id = excluded.aluno_id, unidade_id = excluded.unidade_id, tipo = excluded.tipo, data = excluded.data,
      status = excluded.status, consolidada_em = excluded.consolidada_em, observacoes = excluded.observacoes,
      criado_por = excluded.criado_por,
      pendencia = novo.juntar_pendencia(av.pendencia, excluded.pendencia),
      criado_em = excluded.criado_em, atualizado_em = now();

-- -----------------------------------------------------------------------------
-- Valores brutos do teste físico, um por (sessão, métrica, lado, tentativa)
--   listas simples:  "sprint_10": ["1,9", "2,0", ""]
--   lados:           "single_hop": {"direita": [...], "esquerda": [...]}
--   blocos:          "saltos_vert": {"squat_jump": [...]}, "blazepod_vel_reacao": {"hits": [...], "ms": [...]}
--   VO2:             "teste_vo2": {"vel_max": "12", "tempo_total": "08:30", ...}
--   legado:          "blazepod_vel_reacao": [...] (lista simples, formato antigo)
-- Vazio não gera linha.
-- -----------------------------------------------------------------------------
create temporary table tmp_bruto on commit drop as
select s.id as avaliacao_id, s.created_at, x.chave, x.codigo, x.lado, x.tentativa::smallint as tentativa, x.bruto
from origem.physical_test_sessions s
join novo.avaliacao av on av.id = s.id
cross join lateral (
  -- lista simples
  select e.k as chave,
         case when e.k = 'blazepod_vel_reacao' then 'blazepod_vel_reacao_legado' else e.k end as codigo,
         null::text as lado, l.ord as tentativa, l.val as bruto
  from jsonb_each(s.data) e(k, v)
  cross join lateral jsonb_array_elements_text(case when jsonb_typeof(e.v) = 'array' then e.v else '[]' end)
                     with ordinality l(val, ord)
  union all
  -- objeto com listas: lados (single_hop, cross_hop) ou blocos (saltos_vert, blazepod_vel_reacao)
  select e.k, case when e.k in ('single_hop', 'cross_hop') then e.k else e.k || '_' || o.k2 end,
         case when e.k in ('single_hop', 'cross_hop') then
              case o.k2 when 'direita' then 'dir' when 'esquerda' then 'esq' end end,
         l.ord, l.val
  from jsonb_each(s.data) e(k, v)
  cross join lateral jsonb_each(case when jsonb_typeof(e.v) = 'object' then e.v else '{}' end) o(k2, v2)
  cross join lateral jsonb_array_elements_text(case when jsonb_typeof(o.v2) = 'array' then o.v2 else '[]' end)
                     with ordinality l(val, ord)
  union all
  -- objeto com valores únicos (teste_vo2)
  select e.k, e.k || '_' || o.k2, null, 1, o.v2 #>> '{}'
  from jsonb_each(s.data) e(k, v)
  cross join lateral jsonb_each(case when jsonb_typeof(e.v) = 'object' then e.v else '{}' end) o(k2, v2)
  where jsonb_typeof(o.v2) in ('string', 'number')
  union all
  -- valor único no primeiro nível (não aparece na foto, mas não pode sumir calado)
  select e.k, e.k, null, 1, e.v #>> '{}'
  from jsonb_each(s.data) e(k, v)
  where jsonb_typeof(e.v) in ('string', 'number')
) x
where nullif(btrim(x.bruto), '') is not null;

-- Chave de teste físico sem métrica no catálogo: rejeitada (com o nome da chave).
insert into novo.carga_rejeitado (script, tabela_origem, id_origem, motivo)
select distinct 'avaliacao', 'physical_test_sessions', b.avaliacao_id,
       'chave do teste físico sem métrica no catálogo: ' || b.codigo
from tmp_bruto b
where not exists (select 1 from novo.metrica m where m.codigo = b.codigo)
on conflict (script, tabela_origem, id_origem, motivo) do nothing;

-- -----------------------------------------------------------------------------
-- c4) avaliacao_medida: teste físico
-- -----------------------------------------------------------------------------
insert into novo.avaliacao_medida as am (avaliacao_id, metrica_id, lado, tentativa, valor_num, valor_texto,
                                         pendencia, criado_em)
select c.avaliacao_id, c.metrica_id, c.lado, c.tentativa, c.num,
       case when c.num is null then c.bruto end,
       novo.juntar_pendencia(
         case when c.codigo = 'blazepod_vel_reacao_legado' then 'formato antigo: não dá para saber se é hits ou ms'
              when c.num is null then 'formato antigo / não numérico' end,
         case when c.codigo in ('single_hop', 'cross_hop', 'teste_vo2_distancia_total') and c.num < 10
              then 'unidade não confirmada (abaixo de 10: limiar provisório)'
              when c.num < c.valor_min or c.num > c.valor_max then 'unidade não confirmada' end),
       c.created_at
from (
  select b.*, m.id as metrica_id, m.valor_min, m.valor_max,
         case when b.codigo = 'blazepod_vel_reacao_legado' then null
              when b.codigo in ('teste_vo2_tempo_total', 'teste_vo2_tempo_vel_max') then novo.mmss_para_segundos(b.bruto)::numeric
              else novo.texto_para_numero(b.bruto) end as num
  from tmp_bruto b
  join novo.metrica m on m.codigo = b.codigo
) c
on conflict (avaliacao_id, metrica_id, lado, tentativa) do update
  set valor_num = excluded.valor_num, valor_texto = excluded.valor_texto,
      pendencia = novo.juntar_pendencia(am.pendencia, excluded.pendencia),
      criado_em = excluded.criado_em, atualizado_em = now();

-- altura e peso (colunas numéricas; nulo não gera linha)
insert into novo.avaliacao_medida as am (avaliacao_id, metrica_id, lado, tentativa, valor_num, pendencia, criado_em)
select s.id, m.id, null, 1, v.valor, v.pendencia, s.created_at
from origem.physical_test_sessions s
join novo.avaliacao av on av.id = s.id
cross join lateral (values
  ('antropometria_altura', s.altura, 'unidade ambígua (metros e centímetros misturados)'),
  ('antropometria_peso',   s.peso,   null)) v(codigo, valor, pendencia)
join novo.metrica m on m.codigo = v.codigo
where v.valor is not null
on conflict (avaliacao_id, metrica_id, lado, tentativa) do update
  set valor_num = excluded.valor_num, valor_texto = null,
      pendencia = novo.juntar_pendencia(am.pendencia, excluded.pendencia),
      criado_em = excluded.criado_em, atualizado_em = now();

-- -----------------------------------------------------------------------------
-- c5) avaliacao_medida: notas da avaliação semanal (1 a 5)
-- -----------------------------------------------------------------------------
insert into novo.avaliacao_medida as am (avaliacao_id, metrica_id, lado, tentativa, valor_num, criado_em)
select w.id, m.id, null, 1, v.nota, w.created_at
from origem.weekly_evaluations w
join novo.avaliacao av on av.id = w.id
cross join lateral (values
  ('semanal_ambiente',    w.rating_environment),
  ('semanal_evolucao',    w.rating_evolution),
  ('semanal_qualidade',   w.rating_quality),
  ('semanal_satisfacao',  w.rating_satisfaction),
  ('semanal_atendimento', w.rating_service)) v(codigo, nota)
join novo.metrica m on m.codigo = v.codigo
where v.nota is not null
on conflict (avaliacao_id, metrica_id, lado, tentativa) do update
  set valor_num = excluded.valor_num, valor_texto = null, criado_em = excluded.criado_em, atualizado_em = now();

-- -----------------------------------------------------------------------------
-- Registro da execução (contagens das partes deste script)
-- -----------------------------------------------------------------------------
insert into novo.carga_execucao (script, linhas_carregadas, linhas_rejeitadas, observacao)
select 'avaliacao',
       (select count(*) from novo.metrica)
     + (select count(*) from novo.avaliacao where tipo in ('teste_fisico', 'semanal'))
     + (select count(*) from novo.avaliacao_medida am join novo.avaliacao a on a.id = am.avaliacao_id
         where a.tipo in ('teste_fisico', 'semanal')),
       (select count(*) from novo.carga_rejeitado where script = 'avaliacao'),
       format('metrica %s, avaliacao teste_fisico %s / semanal %s, avaliacao_medida %s (com pendência %s: '
              || 'não numérico %s, limiar provisório %s, altura ambígua %s)',
              (select count(*) from novo.metrica),
              (select count(*) from novo.avaliacao where tipo = 'teste_fisico'),
              (select count(*) from novo.avaliacao where tipo = 'semanal'),
              (select count(*) from novo.avaliacao_medida am join novo.avaliacao a on a.id = am.avaliacao_id
                where a.tipo in ('teste_fisico', 'semanal')),
              (select count(*) from novo.avaliacao_medida am join novo.avaliacao a on a.id = am.avaliacao_id
                where a.tipo in ('teste_fisico', 'semanal') and am.pendencia is not null),
              (select count(*) from novo.avaliacao_medida am join novo.avaliacao a on a.id = am.avaliacao_id where a.tipo in ('teste_fisico', 'semanal') and (am.pendencia like '%não numérico%' or am.pendencia like '%hits ou ms%')),
              (select count(*) from novo.avaliacao_medida am join novo.avaliacao a on a.id = am.avaliacao_id where a.tipo in ('teste_fisico', 'semanal') and am.pendencia like '%limiar provisório%'),
              (select count(*) from novo.avaliacao_medida am join novo.avaliacao a on a.id = am.avaliacao_id where a.tipo in ('teste_fisico', 'semanal') and am.pendencia like '%ambígua%'));

commit;
