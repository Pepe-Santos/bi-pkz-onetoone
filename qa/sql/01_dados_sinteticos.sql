-- QA: massa de teste sintética (nomes e valores inventados). SÓ PARA O POSTGRES LOCAL.
-- Datas relativas a current_date, para os testes de reavaliação não envelhecerem.
-- Cada atleta cobre um grupo de casos; os resultados esperados ficam em 10_testes_tratamento.sql.

TRUNCATE novo.avaliacao_medida, novo.avaliacao, novo.matricula, novo.aluno, novo.pessoa,
         novo.metrica, novo.unidade, novo.servico, novo.agendamento, novo.relatorio_treino,
         novo.perfil_usuario RESTART IDENTITY CASCADE;

INSERT INTO novo.unidade VALUES (1, 'pkz'), (2, 'one_to_one');
INSERT INTO novo.servico VALUES (1, 'treino', 'Treino'), (2, 'avaliacao', 'Avaliação');
INSERT INTO novo.metrica (codigo, nome) SELECT codigo, nome FROM trat.catalogo_teste;

-- UUID curto: q('a01') = 00000000-0000-0000-0000-000000000a01
CREATE OR REPLACE FUNCTION pg_temp.q(t text) RETURNS uuid LANGUAGE sql AS
$$ SELECT ('00000000-0000-0000-0000-' || lpad(t, 12, '0'))::uuid $$;

-- Atleta com matrícula vigente na unidade (NULL = sem matrícula; 'vencida' = matrícula encerrada)
CREATE OR REPLACE FUNCTION pg_temp.atleta(cod text, nome text, unid int, situacao text DEFAULT 'vigente')
RETURNS void LANGUAGE sql AS $$
  INSERT INTO novo.pessoa VALUES (pg_temp.q(cod), nome, current_date - interval '12 years');
  INSERT INTO novo.aluno (id, pessoa_id, categoria) VALUES (pg_temp.q(cod), pg_temp.q(cod), 'Sub 12');
  INSERT INTO novo.matricula (aluno_id, unidade_id, vigencia_inicio, vigencia_fim)
  SELECT pg_temp.q(cod), unid, current_date - 400,
         CASE situacao WHEN 'vencida' THEN current_date - 10 END
  WHERE unid IS NOT NULL;
$$;

CREATE OR REPLACE FUNCTION pg_temp.av(cod text, aluno text, dias_atras int, unid int DEFAULT 1,
                                      status text DEFAULT 'consolidada', tipo text DEFAULT 'teste_fisico',
                                      corrige text DEFAULT NULL)
RETURNS void LANGUAGE sql AS $$
  INSERT INTO novo.avaliacao VALUES (pg_temp.q(cod), pg_temp.q(aluno), unid, current_date - dias_atras,
                                     tipo, status, pg_temp.q(corrige));
$$;

-- Uma linha por tentativa, na ordem do array
CREATE OR REPLACE FUNCTION pg_temp.med(av text, teste text, vals numeric[], lado text DEFAULT NULL)
RETURNS void LANGUAGE sql AS $$
  INSERT INTO novo.avaliacao_medida (avaliacao_id, metrica_id, lado, tentativa, valor_num)
  SELECT pg_temp.q(av), (SELECT id FROM novo.metrica WHERE codigo = teste), lado, n, v
  FROM unnest(vals) WITH ORDINALITY AS t(v, n);
$$;

-- ---------------------------------------------------------------------------
-- a01: conversão de unidade
-- ---------------------------------------------------------------------------
SELECT pg_temp.atleta('a01', 'Atleta Conversão', 1);
SELECT pg_temp.av('b011', 'a01', 20);
SELECT pg_temp.med('b011', 'single_hop', '{1.22, 141}', 'dir');     -- 1,22 m -> 122 cm; melhor 141
SELECT pg_temp.med('b011', 'single_hop', '{1.30}', 'esq');          -- 130
SELECT pg_temp.med('b011', 'cross_hop', '{4.01}', 'dir');           -- 401
SELECT pg_temp.med('b011', 'antropometria_altura', '{1.75}');       -- 175
SELECT pg_temp.med('b011', 'teste_vo2_distancia_total', '{1.02}');  -- 1,02 km -> 1020 m
SELECT pg_temp.av('b012', 'a01', 25);
SELECT pg_temp.med('b012', 'single_hop', '{10}', 'dir');            -- no corte: não converte, abaixo de 30 -> revisão
SELECT pg_temp.med('b012', 'single_hop', '{9.99}', 'esq');          -- converte para 999 -> acima de 350 -> revisão
SELECT pg_temp.med('b012', 'antropometria_altura', '{3}');          -- no corte: não converte, abaixo de 90 -> revisão
SELECT pg_temp.med('b012', 'teste_vo2_distancia_total', '{2880}');  -- já em metros

-- ---------------------------------------------------------------------------
-- a02: valores impossíveis e faixa plausível
-- ---------------------------------------------------------------------------
SELECT pg_temp.atleta('a02', 'Atleta Faixa', 1);
SELECT pg_temp.av('b021', 'a02', 20);
SELECT pg_temp.med('b021', 'sprint_10', '{17, 1.9, 2.1}');          -- 17 s -> revisão; melhor 1,9
SELECT pg_temp.med('b021', 'illinois', '{5.0, 25.0}');              -- limites da faixa: os dois valem
SELECT pg_temp.med('b021', 'teste_vo2_tempo_total', '{6}');         -- 6 s -> revisão
SELECT pg_temp.med('b021', 'slalom_wallball', '{300}');             -- acima de 60 -> revisão
INSERT INTO novo.avaliacao_medida (avaliacao_id, metrica_id, tentativa, valor_num, valor_texto)
SELECT pg_temp.q('b021'), id, 1, NULL, 'não realizou' FROM novo.metrica WHERE codigo = 'banco_wells';
SELECT pg_temp.av('b022', 'a02', 15);
SELECT pg_temp.med('b022', 'teste_vo2_tempo_total', '{300}');
SELECT pg_temp.med('b022', 'teste_vo2_tempo_vel_max', '{600}');     -- maior que o tempo total do teste

-- ---------------------------------------------------------------------------
-- a03: melhor tentativa e média
-- ---------------------------------------------------------------------------
SELECT pg_temp.atleta('a03', 'Atleta Tentativas', 1);
SELECT pg_temp.av('b031', 'a03', 20);
SELECT pg_temp.med('b031', 'banco_wells', '{20, 25}');              -- maior é melhor: 25
SELECT pg_temp.med('b031', 'estabilidade_aquabag', '{2, 1}');       -- menor é melhor: 1
SELECT pg_temp.med('b031', 'antropometria_peso', '{40, 42}');       -- sem direção: média 41
SELECT pg_temp.med('b031', 'slalom_wallball', '{10, 12}');          -- sem direção: média 11
SELECT pg_temp.med('b031', 'sprint_20', '{3.5, 3.4, 30}');          -- 30 descartado; melhor 3,4 com 2 válidas

-- ---------------------------------------------------------------------------
-- a11-a18: comparação (estável abaixo de 2%)
-- Sprint 20 m: anterior 5,000 s (40 dias atrás), atual (10 dias atrás) varia
-- ---------------------------------------------------------------------------
SELECT pg_temp.atleta(c, 'Atleta Comparação ' || c, 1) FROM unnest('{a11,a12,a13,a14,a15,a16,a17,a18}'::text[]) c;
SELECT pg_temp.av('b' || c || '1', c, 40), pg_temp.av('b' || c || '2', c, 10)
FROM unnest('{a11,a12,a13,a14,a16,a17,a18}'::text[]) c;
SELECT pg_temp.med('ba111', 'sprint_20', '{5.000}'); SELECT pg_temp.med('ba112', 'sprint_20', '{4.900}'); -- -2,0%
SELECT pg_temp.med('ba121', 'sprint_20', '{5.000}'); SELECT pg_temp.med('ba122', 'sprint_20', '{4.905}'); -- -1,9%
SELECT pg_temp.med('ba131', 'sprint_20', '{5.000}'); SELECT pg_temp.med('ba132', 'sprint_20', '{4.902}'); -- -1,96%
SELECT pg_temp.med('ba141', 'sprint_20', '{5.000}'); SELECT pg_temp.med('ba142', 'sprint_20', '{5.100}'); -- +2,0%
SELECT pg_temp.av('ba151', 'a15', 10);
SELECT pg_temp.med('ba151', 'sprint_20', '{5.000}');                                                    -- só uma avaliação
SELECT pg_temp.med('ba161', 'antropometria_altura', '{150}'); SELECT pg_temp.med('ba162', 'antropometria_altura', '{160}');
SELECT pg_temp.med('ba171', 'single_hop', '{120}', 'dir');    SELECT pg_temp.med('ba172', 'single_hop', '{130}', 'dir');
SELECT pg_temp.med('ba171', 'single_hop', '{1.20}', 'esq');   SELECT pg_temp.med('ba172', 'single_hop', '{1.10}', 'esq');
SELECT pg_temp.med('ba181', 'estabilidade_aquabag', '{0}');   SELECT pg_temp.med('ba182', 'estabilidade_aquabag', '{2}');

-- ---------------------------------------------------------------------------
-- a21-a24: reavaliação (vence 90 dias depois; "a vencer" nos 30 dias antes)
-- ---------------------------------------------------------------------------
SELECT pg_temp.atleta(c, 'Atleta Reavaliação ' || c, 1) FROM unnest('{a21,a22,a23,a24}'::text[]) c;
SELECT pg_temp.av('b' || c, c, d), pg_temp.med('b' || c, 'sprint_10', '{2.0}')
FROM (VALUES ('a21', 59), ('a22', 60), ('a23', 90), ('a24', 91)) v(c, d);

-- ---------------------------------------------------------------------------
-- a31-a36: unidade, correção e o que não deve entrar
-- ---------------------------------------------------------------------------
SELECT pg_temp.atleta('a31', 'Aluno One to One', 2);
SELECT pg_temp.av('b311', 'a31', 20, 2); SELECT pg_temp.med('b311', 'sprint_10', '{2.5}');
SELECT pg_temp.atleta('a32', 'Atleta Sem Matrícula', NULL);
SELECT pg_temp.av('b321', 'a32', 20, 1); SELECT pg_temp.med('b321', 'sprint_10', '{2.5}');
SELECT pg_temp.atleta('a33', 'Atleta Correção', 1);
SELECT pg_temp.av('b331', 'a33', 30);                                SELECT pg_temp.med('b331', 'sprint_10', '{3.0}');
SELECT pg_temp.av('b332', 'a33', 29, 1, 'consolidada', 'teste_fisico', 'b331'); SELECT pg_temp.med('b332', 'sprint_10', '{2.5}');
SELECT pg_temp.av('b333', 'a33', 20);                                SELECT pg_temp.med('b333', 'sprint_20', '{4.0}');
SELECT pg_temp.av('b334', 'a33', 19, 1, 'rascunho', 'teste_fisico', 'b333');    SELECT pg_temp.med('b334', 'sprint_20', '{3.0}');
SELECT pg_temp.atleta('a34', 'Atleta Fora da Carga', 1);
SELECT pg_temp.av('b341', 'a34', 20, 1, 'rascunho');                 SELECT pg_temp.med('b341', 'sprint_10', '{2.0}');
SELECT pg_temp.av('b342', 'a34', 20, 1, 'consolidada', 'fisioterapia');         SELECT pg_temp.med('b342', 'sprint_10', '{2.0}');
SELECT pg_temp.atleta('a35', 'Atleta Matrícula Vencida', 1, 'vencida');
SELECT pg_temp.av('b351', 'a35', 20, 1); SELECT pg_temp.med('b351', 'sprint_10', '{2.5}');

-- ---------------------------------------------------------------------------
-- Treinos (api.presenca e api.treino)
-- ---------------------------------------------------------------------------
INSERT INTO novo.agendamento VALUES
  (pg_temp.q('c01'), pg_temp.q('a31'), 2, 1, current_date - 3, '08:00', 'presente'),
  (pg_temp.q('c02'), pg_temp.q('a31'), 2, 1, current_date - 2, '08:00', 'aguardando_confirmacao'),
  (pg_temp.q('c03'), pg_temp.q('a31'), 2, 1, current_date + 5, '08:00', 'agendado'),   -- futuro: fora
  (pg_temp.q('c04'), pg_temp.q('a31'), 2, 2, current_date - 1, '08:00', 'presente'),   -- avaliação: fora
  (pg_temp.q('c05'), pg_temp.q('a01'), 1, 1, current_date - 1, '09:00', 'falta');
INSERT INTO novo.relatorio_treino (id, aluno_id, unidade_id, data, status, tipo_treino, intensidade, dor, dor_local) VALUES
  (pg_temp.q('d01'), pg_temp.q('a31'), 2, current_date - 3, 'final',    'força', 7, true, 'joelho'),
  (pg_temp.q('d02'), pg_temp.q('a31'), 2, current_date - 2, 'rascunho', 'força', 6, false, NULL),   -- fora
  (pg_temp.q('d03'), pg_temp.q('a31'), 2, current_date + 2, 'final',    'força', 6, false, NULL);   -- futuro: fora
