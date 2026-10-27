-- Medidas padronizadas dos testes físicos (schema trat).
-- Depende do 04_trat_parametros_catalogo.sql e da novo.vw_avaliacao_medida, view de
-- consumo do grupo de Dados (013_views_consumo.sql deles).
--
-- Lê a vw_avaliacao_medida, que já traz só avaliações consolidadas e não substituídas
-- por uma correção. Aqui entram só as do tipo teste_fisico.
--
-- Começa com DROP ... CASCADE, porque a troca para a view do grupo de Dados tirou
-- colunas (medida_id e pendencia_origem) e CREATE OR REPLACE não remove coluna.
-- O CASCADE apaga também as views da api: depois deste script, rode o 06.
DROP VIEW IF EXISTS trat.medida CASCADE;

-- ---------------------------------------------------------------------------
-- Uma linha por tentativa, já na unidade padrão do catálogo, com o motivo de revisão
-- quando o valor não serve.
-- ---------------------------------------------------------------------------
CREATE VIEW trat.medida AS
WITH base AS (
  SELECT
    am.avaliacao_id,
    am.aluno_id,
    am.data              AS data_avaliacao,
    c.codigo             AS teste,
    am.lado,
    am.tentativa,
    am.valor_num         AS valor_origem,
    am.valor_texto       AS valor_texto_origem,
    CASE
      WHEN am.valor_num < c.conversao_abaixo_de THEN am.valor_num * c.conversao_fator
      ELSE am.valor_num
    END                  AS valor,
    (am.valor_num < c.conversao_abaixo_de) AS convertido,
    c.faixa_min,
    c.faixa_max
  FROM novo.vw_avaliacao_medida am
  JOIN trat.catalogo_teste c ON c.codigo = am.metrica_codigo
  WHERE am.tipo = 'teste_fisico'
)
SELECT
  avaliacao_id,
  aluno_id,
  data_avaliacao,
  teste,
  lado,
  tentativa,
  valor_origem,
  valor_texto_origem,
  valor,
  coalesce(convertido, false) AS convertido,
  CASE
    WHEN valor IS NULL     THEN 'valor não numérico'
    WHEN valor < faixa_min THEN 'abaixo da faixa plausível'
    WHEN valor > faixa_max THEN 'acima da faixa plausível'
  END AS motivo_revisao,
  (valor IS NOT NULL
   AND (faixa_min IS NULL OR valor >= faixa_min)
   AND (faixa_max IS NULL OR valor <= faixa_max)) AS valido
FROM base;

COMMENT ON VIEW trat.medida IS
  'Uma linha por tentativa de teste físico, na unidade padrão de trat.catalogo_teste. valido = false quando o valor não é numérico ou fica fora da faixa plausível.';

-- ---------------------------------------------------------------------------
-- Tentativas que não servem, para alguém da PKZ conferir.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW trat.revisao_dados AS
SELECT
  avaliacao_id,
  aluno_id,
  data_avaliacao,
  teste,
  lado,
  tentativa,
  valor_origem,
  valor_texto_origem,
  valor,
  motivo_revisao
FROM trat.medida
WHERE NOT valido;

COMMENT ON VIEW trat.revisao_dados IS
  'Tentativas fora da faixa plausível ou sem valor numérico. Não entram nos resultados.';

-- ---------------------------------------------------------------------------
-- Uma linha por avaliação, teste e lado: o resultado que vai para a API.
-- Melhor tentativa válida pela direção do teste; média quando o catálogo pede
-- (usa_media) ou quando o teste não tem direção (altura, peso, slalom_wallball).
-- Avaliação sem tentativa válida para o teste não gera linha.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW trat.resultado_teste AS
SELECT
  m.avaliacao_id,
  m.aluno_id,
  m.data_avaliacao,
  m.teste,
  m.lado,
  CASE
    WHEN c.usa_media OR c.maior_melhor IS NULL THEN round(avg(m.valor), 2)
    WHEN c.maior_melhor                        THEN max(m.valor)
    ELSE                                            min(m.valor)
  END              AS valor,
  count(*)::int    AS tentativas_validas
FROM trat.medida m
JOIN trat.catalogo_teste c ON c.codigo = m.teste
WHERE m.valido
GROUP BY m.avaliacao_id, m.aluno_id, m.data_avaliacao, m.teste, m.lado,
         c.usa_media, c.maior_melhor;

COMMENT ON VIEW trat.resultado_teste IS
  'Resultado de cada teste por avaliação e lado, a partir das tentativas válidas de trat.medida.';
