-- Parâmetros de negócio e catálogo de regras por teste (schema trat).
-- Não depende do banco do grupo de Banco de Dados: pode rodar logo depois do 01_schemas.sql.
-- Pode rodar quantas vezes quiser: CREATE IF NOT EXISTS e ON CONFLICT DO NOTHING,
-- então um valor ajustado à mão no banco não é sobrescrito.

-- ---------------------------------------------------------------------------
-- Parâmetros: os números das regras ficam aqui, não no código das views.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS trat.parametro (
  chave         text PRIMARY KEY,
  valor         numeric NOT NULL,
  descricao     text NOT NULL,
  atualizado_em timestamptz NOT NULL DEFAULT now()
);

INSERT INTO trat.parametro (chave, valor, descricao) VALUES
  ('variacao_estavel_pct',   2,  'Variação (em %, valor absoluto) abaixo da qual a comparação é "estável". Provisório.'),
  ('reavaliacao_dias',       90, 'Dias após a última avaliação para a reavaliação vencer. Provisório.'),
  ('reavaliacao_aviso_dias', 30, 'Dias de antecedência em que a reavaliação aparece como "a vencer". Provisório.')
ON CONFLICT (chave) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Catálogo de regras por teste.
-- O banco do app não grava unidade nem direção do teste, então estas regras
-- são HIPÓTESES, marcadas como não confirmadas até a PKZ validar.
-- O código de cada teste é o de novo.metrica.codigo, a tabela de métricas do grupo de
-- Dados (decidido em 20/10). Recodificado em 24/10, conferindo os valores reais de
-- novo.avaliacao_medida. O lado (dir/esq) vem de novo.metrica.usa_lado, não daqui.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS trat.catalogo_teste (
  codigo          text PRIMARY KEY,              -- = novo.metrica.codigo (ex.: sprint_20)
  nome            text NOT NULL,                 -- nome exibido no relatório
  unidade_padrao  text NOT NULL,                 -- s, ms, cm, m, km/h, kg, hits ou desequilibrios
  maior_melhor    boolean,                       -- true: maior é melhor; false: menor é melhor; NULL: não se classifica (medida antropométrica)
  faixa_min       numeric,                       -- faixa plausível, na unidade padrão; fora dela vai para revisão
  faixa_max       numeric,
  regra_conversao text,                          -- a conversão abaixo, por extenso
  conversao_abaixo_de numeric,                   -- valor menor que este está na unidade errada...
  conversao_fator     numeric,                   -- ...e é multiplicado por este (aplicado em trat.medida)
  usa_media       boolean NOT NULL DEFAULT false,-- false: melhor tentativa válida; true: média das tentativas
  confirmado      boolean NOT NULL DEFAULT false,-- true só depois da PKZ validar unidade, direção e faixa
  observacao      text,
  atualizado_em   timestamptz NOT NULL DEFAULT now()
);

-- RLS ligado e sem policy: ninguém lê estas tabelas direto pela API (anon nem
-- authenticated). As views do trat e da api são do postgres, dono das tabelas, e por
-- isso continuam lendo normalmente.
ALTER TABLE trat.parametro      ENABLE ROW LEVEL SECURITY;
ALTER TABLE trat.catalogo_teste ENABLE ROW LEVEL SECURITY;

-- Colunas criadas em 24/10, para o banco onde a tabela já existia.
ALTER TABLE trat.catalogo_teste ADD COLUMN IF NOT EXISTS conversao_abaixo_de numeric;
ALTER TABLE trat.catalogo_teste ADD COLUMN IF NOT EXISTS conversao_fator     numeric;

-- Códigos antigos (antes de 24/10), que não existem em novo.metrica.
DELETE FROM trat.catalogo_teste
WHERE codigo IN ('sprint_10m', 'sprint_20m', 'agilidade', 'slalom', 'salto_horizontal',
                 'salto_vertical', 'vo2_distancia', 'aquabag_estabilidade', 'altura');

-- Faixas e conversões vêm dos valores de novo.avaliacao_medida (24/10): saltos em m e cm
-- no mesmo teste, VO2 em km e m, tempos impossíveis. Entram todos os testes físicos
-- numéricos da novo.metrica, mais altura e peso; blazepod_vel_reacao_legado fica de fora
-- (texto, não dá para saber se é hits ou ms).
INSERT INTO trat.catalogo_teste
  (codigo, nome, unidade_padrao, maior_melhor, faixa_min, faixa_max, regra_conversao, observacao) VALUES
  ('sprint_10',                   'Sprint 10 m',                     's',              false, 1.2,  4.0,  NULL,                                                     'Ex.: 10 m em 17 s é impossível e vai para revisão.'),
  ('sprint_20',                   'Sprint 20 m',                     's',              false, 2.3,  8.0,  NULL,                                                     'Tempos de 6 a 7,5 s são plausíveis para crianças; 10 s vai para revisão.'),
  ('illinois',                    'Agilidade (Illinois)',            's',              false, 5.0,  25.0, NULL,                                                     NULL),
  ('slalom_wallball',             'Slalom com bola / Wall Ball',     's',              NULL,  3.0,  60.0, NULL,                                                     'Unidade e direção em aberto (pendência 3 do grupo de Dados). Valores de 227 a 400 vão para revisão. Sem direção, aparece sem classificação.'),
  ('estabilidade_aquabag',        'Estabilidade Aquabag',            'desequilibrios', false, 0,    6,    NULL,                                                     'Nº de desequilíbrios (inteiros de 0 a 6, mediana 1): menor é melhor.'),
  ('banco_wells',                 'Banco de Wells (flexibilidade)',  'cm',             true,  0,    60,   NULL,                                                     NULL),
  ('single_hop',                  'Single hop (salto horizontal)',   'cm',             true,  30,   350,  'valor abaixo de 10 está em metros: multiplicar por 100', 'Por lado. Origem mistura 1,22 (m) e 141 (cm); valores de 450 a 495 parecem cross hop e vão para revisão.'),
  ('cross_hop',                   'Cross hop',                       'cm',             true,  100,  600,  'valor abaixo de 10 está em metros: multiplicar por 100', 'Por lado. Origem mistura 4,01 (m) e 543 (cm); sem conversão daria melhora de 13.000%.'),
  ('saltos_vert_squat_jump',      'Salto vertical (squat jump)',     'cm',             true,  5,    80,   NULL,                                                     NULL),
  ('saltos_vert_countermovement', 'Salto vertical (contramovimento)','cm',             true,  5,    80,   NULL,                                                     NULL),
  ('saltos_vert_abalakov',        'Salto vertical (Abalakov)',       'cm',             true,  5,    80,   NULL,                                                     NULL),
  ('blazepod_foco',               'Blazepod (foco)',                 'hits',           true,  1,    150,  NULL,                                                     NULL),
  ('blazepod_vel_reacao_hits',    'Blazepod (reação, acertos)',      'hits',           true,  1,    150,  NULL,                                                     NULL),
  ('blazepod_vel_reacao_ms',      'Blazepod (reação, tempo)',        'ms',             false, 150,  2000, NULL,                                                     NULL),
  ('teste_vo2_vel_max',           'VO2 (velocidade máxima)',         'km/h',           true,  5,    25,   NULL,                                                     NULL),
  ('teste_vo2_tempo_total',       'VO2 (tempo total)',               's',              true,  60,   1800, NULL,                                                     'Ex.: 6 s é impossível e vai para revisão.'),
  ('teste_vo2_distancia_total',   'VO2 (distância)',                 'm',              true,  400,  4000, 'valor abaixo de 10 está em km: multiplicar por 1000',    'Origem mistura 1,02 (km) e 2.880 (m).'),
  ('teste_vo2_tempo_vel_max',     'VO2 (tempo na velocidade máxima)','s',              true,  1,    900,  NULL,                                                     'Não pode passar do tempo total do teste.'),
  ('antropometria_altura',        'Altura',                          'cm',             NULL,  90,   220,  'valor abaixo de 3 está em metros: multiplicar por 100',  'Medida antropométrica: aparece no relatório, mas não é classificada.'),
  ('antropometria_peso',          'Peso',                            'kg',             NULL,  15,   150,  NULL,                                                     'Medida antropométrica: aparece no relatório, mas não é classificada.')
ON CONFLICT (codigo) DO NOTHING;

-- Conversões em números, para a view de medidas aplicar (as mesmas de regra_conversao).
UPDATE trat.catalogo_teste c
SET conversao_abaixo_de = v.abaixo_de, conversao_fator = v.fator
FROM (VALUES
  ('single_hop',                10, 100),
  ('cross_hop',                 10, 100),
  ('teste_vo2_distancia_total', 10, 1000),
  ('antropometria_altura',      3,  100)
) AS v (codigo, abaixo_de, fator)
WHERE c.codigo = v.codigo
  AND c.conversao_abaixo_de IS NULL;
