-- QA: massa sintética para os PDFs (curto, longo e incompleto). SÓ PARA O POSTGRES LOCAL.
-- Roda depois do 01. Datas fixas em 2026, para gerar o relatório mensal de agosto/2026.

CREATE OR REPLACE FUNCTION pg_temp.q(t text) RETURNS uuid LANGUAGE sql AS
$$ SELECT ('00000000-0000-0000-0000-' || lpad(t, 12, '0'))::uuid $$;

CREATE OR REPLACE FUNCTION pg_temp.atleta(cod text, nome text, nasc date, categoria text)
RETURNS void LANGUAGE sql AS $$
  INSERT INTO novo.pessoa VALUES (pg_temp.q(cod), nome, nasc);
  INSERT INTO novo.aluno (id, pessoa_id, categoria) VALUES (pg_temp.q(cod), pg_temp.q(cod), categoria);
  INSERT INTO novo.matricula (aluno_id, unidade_id, vigencia_inicio) VALUES (pg_temp.q(cod), 1, '2025-01-01');
$$;

CREATE OR REPLACE FUNCTION pg_temp.av(cod text, aluno text, dia date) RETURNS void LANGUAGE sql AS $$
  INSERT INTO novo.avaliacao (id, aluno_id, unidade_id, data) VALUES (pg_temp.q(cod), pg_temp.q(aluno), 1, dia);
$$;

CREATE OR REPLACE FUNCTION pg_temp.med(av text, teste text, vals numeric[], lado text DEFAULT NULL)
RETURNS void LANGUAGE sql AS $$
  INSERT INTO novo.avaliacao_medida (avaliacao_id, metrica_id, lado, tentativa, valor_num)
  SELECT pg_temp.q(av), (SELECT id FROM novo.metrica WHERE codigo = teste), lado, n, v
  FROM unnest(vals) WITH ORDINALITY AS t(v, n);
$$;

-- a41: histórico longo, 5 avaliações (uma em agosto/2026 e duas DEPOIS de agosto)
SELECT pg_temp.atleta('a41', 'Atleta Histórico Longo da Silva Pereira Santos', '2014-03-10', 'Sub 12');
SELECT pg_temp.av('b41' || i, 'a41', d)
FROM (VALUES (1, '2025-11-10'::date), (2, '2026-02-12'), (3, '2026-05-14'), (4, '2026-08-13'), (5, '2026-10-20')) v(i, d);
SELECT pg_temp.med('b41' || i, 'sprint_10',  ARRAY[2.30 - i * 0.04, 2.35 - i * 0.04]),
       pg_temp.med('b41' || i, 'sprint_20',  ARRAY[4.10 - i * 0.05]),
       pg_temp.med('b41' || i, 'illinois',   ARRAY[19.5 - i * 0.3]),
       pg_temp.med('b41' || i, 'single_hop', ARRAY[1.30 + i * 0.04, 128 + i * 4], 'dir'),
       pg_temp.med('b41' || i, 'single_hop', ARRAY[118 + i * 2], 'esq'),
       pg_temp.med('b41' || i, 'cross_hop',  ARRAY[400 + i * 10], 'dir'),
       pg_temp.med('b41' || i, 'cross_hop',  ARRAY[380 + i * 12], 'esq'),
       pg_temp.med('b41' || i, 'banco_wells', ARRAY[22 + i]),
       pg_temp.med('b41' || i, 'saltos_vert_countermovement', ARRAY[24 + i, 25 + i]),
       pg_temp.med('b41' || i, 'blazepod_vel_reacao_ms', ARRAY[620 - i * 15]),
       pg_temp.med('b41' || i, 'estabilidade_aquabag', ARRAY[(4 - i % 3)::numeric]),
       pg_temp.med('b41' || i, 'teste_vo2_distancia_total', ARRAY[1.6 + i * 0.1]),
       pg_temp.med('b41' || i, 'antropometria_altura', ARRAY[1.45 + i * 0.01]),
       pg_temp.med('b41' || i, 'antropometria_peso', ARRAY[38 + i * 0.5])
FROM generate_series(1, 5) i;
INSERT INTO novo.agendamento (id, aluno_id, unidade_id, servico_id, data, hora_inicio, status)
SELECT gen_random_uuid(), pg_temp.q('a41'), 1, 1, d::date, '17:00',
       CASE WHEN extract(day FROM d) IN (6, 20) THEN 'falta'
            WHEN extract(day FROM d) = 27 THEN 'cancelado' ELSE 'presente' END
FROM generate_series('2026-08-04'::date, '2026-08-31', interval '1 day') d
WHERE extract(isodow FROM d) IN (2, 4);

-- a42: curto, uma avaliação em agosto/2026, sem presença
SELECT pg_temp.atleta('a42', 'Atleta Avaliação Única', '2012-07-01', 'Sub 14/15');
SELECT pg_temp.av('b421', 'a42', '2026-08-20');
SELECT pg_temp.med('b421', 'sprint_10', '{2.05}'), pg_temp.med('b421', 'banco_wells', '{28}'),
       pg_temp.med('b421', 'antropometria_altura', '{158}');

-- a43: incompleto, só presenças em agosto/2026, sem avaliação e sem categoria
SELECT pg_temp.atleta('a43', 'Atleta Só Frequência', NULL, NULL);
INSERT INTO novo.agendamento (id, aluno_id, unidade_id, servico_id, data, hora_inicio, status) VALUES
  (gen_random_uuid(), pg_temp.q('a43'), 1, 1, '2026-08-05', '17:00', 'presente'),
  (gen_random_uuid(), pg_temp.q('a43'), 1, 1, '2026-08-12', '17:00', 'falta'),
  (gen_random_uuid(), pg_temp.q('a43'), 1, 1, '2026-08-19', '17:00', 'aguardando_confirmacao');
