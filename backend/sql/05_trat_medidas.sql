-- Medidas padronizadas dos testes físicos (schema trat).
-- Depende do 04_trat_parametros_catalogo.sql e das tabelas novo.avaliacao,
-- novo.avaliacao_medida e novo.metrica (grupo de Dados).
--
-- Lê as tabelas, e não a novo.vw_avaliacao_medida: essa view é security_invoker, então
-- aplica o RLS da 012 a quem chama a API, e o usuário da API não tem papel no app
-- (novo.perfil_usuario). Por ela, quem entra com login recebe 0 atletas. Veja o 08.
-- Entram só as avaliações de teste físico consolidadas e não substituídas por uma correção.
--
-- Pode rodar quantas vezes quiser (CREATE OR REPLACE VIEW); as views da api continuam de pé.

-- ---------------------------------------------------------------------------
-- Uma linha por tentativa, já na unidade padrão do catálogo, com o motivo de revisão
-- quando o valor não serve. No VO2, o tempo na velocidade máxima não pode passar do
-- tempo total válido da mesma avaliação; sem tempo total válido, essa regra não se aplica.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW trat.medida AS
WITH base AS (
  SELECT
    am.id                AS medida_id,
    a.id                 AS avaliacao_id,
    a.aluno_id,
    a.data               AS data_avaliacao,
    c.codigo             AS teste,
    am.lado,
    am.tentativa,
    am.valor_num         AS valor_origem,
    am.valor_texto       AS valor_texto_origem,
    am.pendencia         AS pendencia_origem,
    CASE
      WHEN am.valor_num < c.conversao_abaixo_de THEN am.valor_num * c.conversao_fator
      ELSE am.valor_num
    END                  AS valor,
    (am.valor_num < c.conversao_abaixo_de) AS convertido,
    c.faixa_min,
    c.faixa_max
  FROM novo.avaliacao_medida am
  JOIN novo.avaliacao a ON a.id = am.avaliacao_id
  JOIN novo.metrica m   ON m.id = am.metrica_id
  JOIN trat.catalogo_teste c ON c.codigo = m.codigo
  WHERE a.tipo = 'teste_fisico'
    AND a.status = 'consolidada'
    AND NOT EXISTS (SELECT 1 FROM novo.avaliacao corr WHERE corr.corrige_avaliacao_id = a.id)
),
tempo_total AS (
  SELECT avaliacao_id, max(valor) AS valor
  FROM base
  WHERE teste = 'teste_vo2_tempo_total'
    AND valor IS NOT NULL
    AND (faixa_min IS NULL OR valor >= faixa_min)
    AND (faixa_max IS NULL OR valor <= faixa_max)
  GROUP BY avaliacao_id
),
conferido AS (
  SELECT
    b.*,
    coalesce(b.teste = 'teste_vo2_tempo_vel_max' AND b.valor > t.valor, false) AS passa_tempo_total
  FROM base b
  LEFT JOIN tempo_total t ON t.avaliacao_id = b.avaliacao_id
)
SELECT
  medida_id,
  avaliacao_id,
  aluno_id,
  data_avaliacao,
  teste,
  lado,
  tentativa,
  valor_origem,
  valor_texto_origem,
  pendencia_origem,
  valor,
  coalesce(convertido, false) AS convertido,
  CASE
    WHEN valor IS NULL     THEN 'valor não numérico'
    WHEN valor < faixa_min THEN 'abaixo da faixa plausível'
    WHEN valor > faixa_max THEN 'acima da faixa plausível'
    WHEN passa_tempo_total THEN 'tempo na velocidade máxima maior que o tempo total'
  END AS motivo_revisao,
  (valor IS NOT NULL
   AND (faixa_min IS NULL OR valor >= faixa_min)
   AND (faixa_max IS NULL OR valor <= faixa_max)
   AND NOT passa_tempo_total) AS valido
FROM conferido;

COMMENT ON VIEW trat.medida IS
  'Uma linha por tentativa de teste físico, na unidade padrão de trat.catalogo_teste. valido = false quando o valor não é numérico, fica fora da faixa plausível ou, no VO2, o tempo na velocidade máxima passa do tempo total.';

-- ---------------------------------------------------------------------------
-- Tentativas que não servem, para alguém da PKZ conferir.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW trat.revisao_dados AS
SELECT
  medida_id,
  avaliacao_id,
  aluno_id,
  data_avaliacao,
  teste,
  lado,
  tentativa,
  valor_origem,
  valor_texto_origem,
  valor,
  motivo_revisao,
  pendencia_origem
FROM trat.medida
WHERE NOT valido;

COMMENT ON VIEW trat.revisao_dados IS
  'Tentativas fora da faixa plausível, sem valor numérico ou com tempo na velocidade máxima maior que o tempo total do VO2. Não entram nos resultados.';

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
