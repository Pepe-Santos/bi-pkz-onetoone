-- QA: testes do tratamento das medidas e da API, com a massa do 01_dados_sinteticos.sql.
-- SÓ PARA O POSTGRES LOCAL (o 99 roda tudo na ordem). Saída: uma linha por caso,
-- com OK ou FALHOU, e o total no fim.

CREATE OR REPLACE FUNCTION pg_temp.q(t text) RETURNS uuid LANGUAGE sql AS
$$ SELECT ('00000000-0000-0000-0000-' || lpad(t, 12, '0'))::uuid $$;

-- Resultado de um teste numa avaliação (trat.resultado_teste)
CREATE OR REPLACE FUNCTION pg_temp.res(av text, teste_ text, lado_ text DEFAULT NULL) RETURNS text
LANGUAGE sql AS $$
  SELECT coalesce((SELECT valor::text || ' (' || tentativas_validas || ' válida' ||
                          CASE WHEN tentativas_validas > 1 THEN 's' ELSE '' END || ')'
                   FROM trat.resultado_teste
                   WHERE avaliacao_id = pg_temp.q(av) AND teste = teste_
                     AND lado IS NOT DISTINCT FROM lado_), 'sem resultado')
$$;

-- Tentativa em trat.medida: valor tratado ou motivo de revisão
CREATE OR REPLACE FUNCTION pg_temp.tent(av text, teste_ text, n int, lado_ text DEFAULT NULL) RETURNS text
LANGUAGE sql AS $$
  SELECT CASE WHEN valido THEN valor::text ELSE 'revisão: ' || motivo_revisao END
  FROM trat.medida
  WHERE avaliacao_id = pg_temp.q(av) AND teste = teste_ AND tentativa = n
    AND lado IS NOT DISTINCT FROM lado_
$$;

CREATE OR REPLACE FUNCTION pg_temp.comp(aluno text, teste_ text, lado_ text DEFAULT NULL) RETURNS text
LANGUAGE sql AS $$
  SELECT situacao || coalesce(' (' || variacao_pct || '%)', '')
  FROM api.comparacao WHERE atleta_id = pg_temp.q(aluno) AND teste = teste_
    AND lado IS NOT DISTINCT FROM lado_
$$;

CREATE OR REPLACE FUNCTION pg_temp.reav(aluno text) RETURNS text LANGUAGE sql AS $$
  SELECT situacao || ' (' || dias_para_vencer || ' dias)' FROM api.reavaliacao
  WHERE atleta_id = pg_temp.q(aluno)
$$;

CREATE TEMP TABLE qa_caso (
  ordem serial, grupo text, caso text, esperado text, obtido text, obs text);
GRANT ALL ON qa_caso TO PUBLIC;
GRANT ALL ON SEQUENCE qa_caso_ordem_seq TO PUBLIC;

INSERT INTO qa_caso (grupo, caso, esperado, obtido, obs) VALUES
-- Conversão de unidade
('1 conversão', 'Single hop 1,22 (m) vira 122 cm',              '122.00',  pg_temp.tent('b011', 'single_hop', 1, 'dir'), NULL),
('1 conversão', 'Single hop dir 1,22 m e 141 cm: melhor = 141',  '141 (2 válidas)', pg_temp.res('b011', 'single_hop', 'dir'), NULL),
('1 conversão', 'Single hop esq 1,30 m -> 130 cm',               '130.00 (1 válida)', pg_temp.res('b011', 'single_hop', 'esq'), NULL),
('1 conversão', 'Cross hop 4,01 m -> 401 cm',                    '401.00 (1 válida)', pg_temp.res('b011', 'cross_hop', 'dir'), NULL),
('1 conversão', 'Altura 1,75 m -> 175 cm',                       '175.00 (1 válida)', pg_temp.res('b011', 'antropometria_altura'), NULL),
('1 conversão', 'Distância VO2 1,02 km -> 1020 m',               '1020.00 (1 válida)', pg_temp.res('b011', 'teste_vo2_distancia_total'), NULL),
('1 conversão', 'Distância VO2 2880 m continua 2880',            '2880 (1 válida)', pg_temp.res('b012', 'teste_vo2_distancia_total'), NULL),
('1 conversão', 'Single hop 10 (no corte) não converte e vai para revisão', 'revisão: abaixo da faixa plausível', pg_temp.tent('b012', 'single_hop', 1, 'dir'), NULL),
('1 conversão', 'Single hop 9,99 vira 999 e vai para revisão',   'revisão: acima da faixa plausível', pg_temp.tent('b012', 'single_hop', 1, 'esq'), NULL),
('1 conversão', 'Altura 3 (no corte) não converte e vai para revisão', 'revisão: abaixo da faixa plausível', pg_temp.tent('b012', 'antropometria_altura', 1), NULL),
-- Valores impossíveis
('2 faixa', 'Sprint 10 m em 17 s vai para revisão',              'revisão: acima da faixa plausível', pg_temp.tent('b021', 'sprint_10', 1), NULL),
('2 faixa', 'Sprint 10 m: 17 descartado, melhor 1,9',            '1.9 (2 válidas)', pg_temp.res('b021', 'sprint_10'), NULL),
('2 faixa', 'Illinois 5,0 e 25,0 (limites) valem',               '5.0 (2 válidas)', pg_temp.res('b021', 'illinois'), NULL),
('2 faixa', 'Tempo total VO2 6 s vai para revisão',              'revisão: abaixo da faixa plausível', pg_temp.tent('b021', 'teste_vo2_tempo_total', 1), NULL),
('2 faixa', 'Tempo total VO2 6 s não gera resultado',            'sem resultado', pg_temp.res('b021', 'teste_vo2_tempo_total'), NULL),
('2 faixa', 'Slalom 300 vai para revisão',                       'revisão: acima da faixa plausível', pg_temp.tent('b021', 'slalom_wallball', 1), NULL),
('2 faixa', 'Banco de Wells só com texto vai para revisão',      'revisão: valor não numérico', pg_temp.tent('b021', 'banco_wells', 1), NULL),
('2 faixa', 'Tempo na vel. máx. (600 s) maior que o tempo total (300 s) vai para revisão',
  'revisão', coalesce(pg_temp.tent('b022', 'teste_vo2_tempo_vel_max', 1), '?'),
  'O catálogo diz "não pode passar do tempo total do teste", mas trat.medida só confere a faixa 1–900.'),
('2 faixa', 'Revisões listadas em trat.revisao_dados',           '8', (SELECT count(*)::text FROM trat.revisao_dados), '3 da a01, 4 da a02 e 1 da a03 (sprint 20 m em 30 s)'),
-- Melhor tentativa e média
('3 tentativas', 'Banco de Wells 20 e 25 (maior é melhor)',      '25 (2 válidas)',    pg_temp.res('b031', 'banco_wells'), NULL),
('3 tentativas', 'Aquabag 2 e 1 (menor é melhor)',               '1 (2 válidas)',     pg_temp.res('b031', 'estabilidade_aquabag'), NULL),
('3 tentativas', 'Peso 40 e 42 (sem direção: média)',            '41.00 (2 válidas)', pg_temp.res('b031', 'antropometria_peso'), NULL),
('3 tentativas', 'Slalom 10 e 12 (sem direção: média)',          '11.00 (2 válidas)', pg_temp.res('b031', 'slalom_wallball'), NULL),
('3 tentativas', 'Sprint 20 m 3,5 · 3,4 · 30: descarta 30, melhor 3,4', '3.4 (2 válidas)', pg_temp.res('b031', 'sprint_20'), NULL),
-- Comparação
('4 estável', 'Sprint 20 m 5,000 -> 4,900 (-2,0%)',              'melhorou (-2.0%)',       pg_temp.comp('a11', 'sprint_20'), NULL),
('4 estável', 'Sprint 20 m 5,000 -> 4,905 (-1,9%)',              'estavel (-1.9%)',        pg_temp.comp('a12', 'sprint_20'), NULL),
('4 estável', 'Sprint 20 m 5,000 -> 4,902 (-1,96%, abaixo de 2%)', 'estavel',              split_part(pg_temp.comp('a13', 'sprint_20'), ' ', 1),
  'A view arredonda a variação para 1 casa (-2,0%) antes de comparar com 2%. Variações de 1,95% a 1,99% saem como melhorou/piorou.'),
('4 estável', 'Sprint 20 m 5,000 -> 5,100 (+2,0%)',              'piorou (2.0%)',          pg_temp.comp('a14', 'sprint_20'), NULL),
('4 estável', 'Só uma avaliação',                                'sem_comparacao',         pg_temp.comp('a15', 'sprint_20'), NULL),
('4 estável', 'Altura 150 -> 160 (sem direção)',                 'sem_classificacao (6.7%)', pg_temp.comp('a16', 'antropometria_altura'), NULL),
('4 estável', 'Single hop dir 120 -> 130',                       'melhorou (8.3%)',        pg_temp.comp('a17', 'single_hop', 'dir'), NULL),
('4 estável', 'Single hop esq 1,20 m -> 1,10 m (convertidos)',   'piorou (-8.3%)',         pg_temp.comp('a17', 'single_hop', 'esq'), NULL),
('4 estável', 'Aquabag 0 -> 2 (anterior zero, sem %)',           'piorou',                 pg_temp.comp('a18', 'estabilidade_aquabag'), NULL),
-- Reavaliação
('5 reavaliação', 'Última avaliação há 59 dias',                 'em_dia (31 dias)',   pg_temp.reav('a21'), NULL),
('5 reavaliação', 'Última avaliação há 60 dias',                 'a_vencer (30 dias)', pg_temp.reav('a22'), NULL),
('5 reavaliação', 'Última avaliação há 90 dias (vence hoje)',    'a_vencer (0 dias)',  pg_temp.reav('a23'), NULL),
('5 reavaliação', 'Última avaliação há 91 dias',                 'vencida (-1 dias)',  pg_temp.reav('a24'), NULL),
-- Correção, rascunho, fisioterapia e unidade
('6 carga', 'Avaliação corrigida (consolidada) sai; fica só a correção', '2.5 (1 válida)',
  (SELECT string_agg(valor || ' (' || tentativas_validas || ' válida)', ', ') FROM trat.resultado_teste
   WHERE aluno_id = pg_temp.q('a33') AND teste = 'sprint_10'), NULL),
('6 carga', 'Correção em rascunho não esconde a original',       '4.0 (1 válida)', pg_temp.res('b333', 'sprint_20'), NULL),
('6 carga', 'Avaliação em rascunho e de fisioterapia não entram', '0',
  (SELECT count(*)::text FROM trat.resultado_teste WHERE aluno_id = pg_temp.q('a34')), NULL),
('6 carga', 'Aluno sem matrícula fica sem unidade',              'sem unidade',
  (SELECT coalesce(unidade, 'sem unidade') FROM api.atleta WHERE atleta_id = pg_temp.q('a32')), NULL),
('6 carga', 'Matrícula vencida: aluno fica sem unidade',         'sem unidade',
  (SELECT coalesce(unidade, 'sem unidade') FROM api.atleta WHERE atleta_id = pg_temp.q('a35')), NULL),
('6 carga', 'total_avaliacoes da a33 (a corrigida e o rascunho não contam)', '2',
  (SELECT total_avaliacoes::text FROM api.atleta WHERE atleta_id = pg_temp.q('a33')), NULL),
-- Treinos
('7 treinos', 'Presença: só treino, até hoje (2 da a31)',        '2',
  (SELECT count(*)::text FROM api.presenca WHERE atleta_id = pg_temp.q('a31')), NULL),
('7 treinos', 'Presença: aguardando_confirmacao vira agendado',  'agendado',
  (SELECT status FROM api.presenca WHERE agendamento_id = pg_temp.q('c02')), NULL),
('7 treinos', 'Treino: só relatório final e até hoje',           '1',
  (SELECT count(*)::text FROM api.treino WHERE atleta_id = pg_temp.q('a31')), NULL),
('7 treinos', 'Treino: nenhum campo de dor na API',              '0',
  (SELECT count(*)::text FROM information_schema.columns
   WHERE table_schema = 'api' AND column_name LIKE '%dor%'), NULL);

-- ---------------------------------------------------------------------------
-- Quem vê o quê pela API: simula o token de cada usuário como o Supabase faz
-- (papel do banco + request.jwt.claims). O usuário da API não tem perfil no app.
-- Atletas na massa: 17 PKZ, 1 One to One, 2 sem unidade = 20.
-- ---------------------------------------------------------------------------
DO $$
DECLARE
  r record;
  n bigint;
  obtido text;
BEGIN
  FOR r IN SELECT * FROM (VALUES
    ('8 acesso', 'Sem login (anon) não lê api.atleta',              'anon',          NULL,                                   'api.atleta',   'acesso negado', NULL::text),
    ('8 acesso', 'Usuário PKZ vê os 17 atletas PKZ em api.atleta',  'authenticated', '{"app_metadata":{"unidade":"PKZ"}}',   'api.atleta',   '17',
       'Ver o achado sobre security_invoker: as views da api leem novo.vw_aluno e novo.vw_avaliacao_medida, que aplicam o RLS de quem chama.'),
    ('8 acesso', 'Usuário PKZ vê avaliações em api.evolucao',       'authenticated', '{"app_metadata":{"unidade":"PKZ"}}',   'api.evolucao', '38', NULL),
    ('8 acesso', 'Usuário One to One vê 1 atleta em api.atleta',    'authenticated', '{"app_metadata":{"unidade":"ONE_TO_ONE"}}', 'api.atleta', '1', NULL),
    ('8 acesso', 'Usuário TODAS vê os 20 atletas',                  'authenticated', '{"app_metadata":{"unidade":"TODAS"}}', 'api.atleta',   '20', NULL),
    ('8 acesso', 'Usuário sem unidade não vê ninguém',              'authenticated', '{"app_metadata":{}}',                  'api.atleta',   '0', NULL),
    ('8 acesso', 'Secret key (service_role) vê os 20',              'service_role',  '{"role":"service_role"}',              'api.atleta',   '20', NULL),
    ('8 acesso', 'Usuário One to One vê 2 presenças',               'authenticated', '{"app_metadata":{"unidade":"ONE_TO_ONE"}}', 'api.presenca', '2', NULL),
    ('8 acesso', 'Usuário PKZ vê 1 presença (não vê a do One to One)', 'authenticated', '{"app_metadata":{"unidade":"PKZ"}}', 'api.presenca', '1', NULL),
    ('8 acesso', 'Usuário logado não lê o trat direto',             'authenticated', '{"app_metadata":{"unidade":"TODAS"}}', 'trat.medida',  'acesso negado', NULL)
  ) v(grupo, caso, papel, claims, objeto, esperado, obs)
  LOOP
    BEGIN
      PERFORM set_config('request.jwt.claims', coalesce(r.claims, ''), true);
      EXECUTE format('SET LOCAL ROLE %I', r.papel);
      EXECUTE format('SELECT count(*) FROM %s', r.objeto) INTO n;
      obtido := n::text;
      RESET ROLE;
    EXCEPTION WHEN insufficient_privilege THEN
      obtido := 'acesso negado';
    END;
    RESET ROLE;
    PERFORM set_config('request.jwt.claims', '', true);
    INSERT INTO qa_caso (grupo, caso, esperado, obtido, obs)
    VALUES (r.grupo, r.caso, r.esperado, obtido, r.obs);
  END LOOP;
END $$;

\pset footer off
SELECT grupo, caso, esperado, coalesce(obtido, '(nada)') AS obtido,
       CASE WHEN obtido = esperado OR (esperado = 'revisão' AND obtido LIKE 'revisão%')
            THEN 'OK' ELSE 'FALHOU' END AS resultado,
       CASE WHEN obtido IS DISTINCT FROM esperado THEN obs ELSE NULL END AS observacao
FROM qa_caso ORDER BY ordem;

SELECT count(*) FILTER (WHERE obtido = esperado OR (esperado = 'revisão' AND obtido LIKE 'revisão%')) AS ok,
       count(*) FILTER (WHERE NOT (obtido = esperado OR (esperado = 'revisão' AND obtido LIKE 'revisão%')) OR obtido IS NULL) AS falhou,
       count(*) AS total
FROM qa_caso;
