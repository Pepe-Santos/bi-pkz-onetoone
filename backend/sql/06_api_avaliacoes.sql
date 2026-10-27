-- Views da API de avaliações (schema api). Contrato em backend/docs/api.md.
-- Depende do 04_trat_parametros_catalogo.sql, do 05_trat_medidas.sql e da novo.vw_aluno
-- (view de consumo do grupo de Dados). Pode rodar quantas vezes quiser (CREATE OR
-- REPLACE VIEW); rode sempre depois do 05, que apaga estas views ao recriar o trat.
--
-- As views são do postgres e rodam com as permissões dele: quem chama a API só precisa
-- de SELECT no schema api, sem acesso ao trat nem ao novo.
--
-- Separação por unidade: cada usuário tem app_metadata.unidade = PKZ, ONE_TO_ONE ou
-- TODAS (só um administrador muda, por SQL em auth.users). As views mostram só os atletas
-- dessa unidade. Usuário sem unidade não vê nada. A secret key (service_role) e o acesso
-- direto ao banco (SQL Editor, psql: sem token) veem tudo.

-- ---------------------------------------------------------------------------
-- Unidade de cada aluno, da novo.vw_aluno (view de consumo do grupo de Dados): a da
-- matrícula vigente. Aluno sem matrícula vigente fica sem unidade e só aparece para
-- quem vê TODAS.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW trat.aluno_unidade AS
SELECT aluno_id, upper(unidade) AS unidade
FROM novo.vw_aluno;

-- Quem fez a chamada pode ver atletas desta unidade?
CREATE OR REPLACE FUNCTION trat.unidade_permitida(unidade text)
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
  SELECT auth.jwt() IS NULL                                     -- fora da API
      OR auth.jwt() ->> 'role' = 'service_role'                 -- secret key
      OR auth.jwt() -> 'app_metadata' ->> 'unidade' IN ('TODAS', unidade);
$$;

-- ---------------------------------------------------------------------------
-- atleta: identificação e filtros. Única view com nome.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW api.atleta AS
WITH avaliacoes AS (
  SELECT aluno_id,
         count(DISTINCT avaliacao_id)::int AS total_avaliacoes,
         max(data_avaliacao)               AS ultima_avaliacao_em
  FROM trat.resultado_teste
  GROUP BY aluno_id
)
SELECT
  a.aluno_id                                             AS atleta_id,
  upper(a.unidade)                                       AS unidade,
  a.nome,
  extract(year FROM age(current_date, a.data_nascimento))::int AS idade,
  a.categoria,
  (a.status = 'ativo')                                   AS ativo,
  coalesce(av.total_avaliacoes, 0)                       AS total_avaliacoes,
  av.ultima_avaliacao_em
FROM novo.vw_aluno a
LEFT JOIN avaliacoes av ON av.aluno_id = a.aluno_id
WHERE trat.unidade_permitida(upper(a.unidade));

-- ---------------------------------------------------------------------------
-- evolucao: histórico de cada teste do atleta, uma linha por avaliação, teste e lado.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW api.evolucao AS
SELECT
  r.aluno_id           AS atleta_id,
  r.avaliacao_id,
  r.data_avaliacao,
  r.teste,
  c.nome               AS teste_nome,
  r.lado,
  c.unidade_padrao     AS unidade_medida,
  c.maior_melhor,
  c.confirmado,
  r.valor,
  r.tentativas_validas
FROM trat.resultado_teste r
JOIN trat.catalogo_teste c       ON c.codigo = r.teste
LEFT JOIN trat.aluno_unidade ua  ON ua.aluno_id = r.aluno_id
WHERE trat.unidade_permitida(ua.unidade);

-- comparacao e reavaliacao leem de api.evolucao e api.atleta, então já saem filtradas.

-- ---------------------------------------------------------------------------
-- comparacao: última avaliação contra a anterior, por atleta, teste e lado.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW api.comparacao AS
WITH ordenado AS (
  SELECT
    e.*,
    row_number() OVER (PARTITION BY e.atleta_id, e.teste, e.lado
                       ORDER BY e.data_avaliacao DESC, e.avaliacao_id DESC) AS ordem
  FROM api.evolucao e
),
par AS (
  SELECT
    atual.atleta_id,
    atual.teste,
    atual.teste_nome,
    atual.lado,
    atual.unidade_medida,
    atual.maior_melhor,
    atual.confirmado,
    ant.data_avaliacao   AS data_anterior,
    ant.valor            AS valor_anterior,
    atual.data_avaliacao AS data_atual,
    atual.valor          AS valor_atual,
    atual.valor - ant.valor AS variacao_abs,
    round((atual.valor - ant.valor) / nullif(ant.valor, 0) * 100, 1) AS variacao_pct
  FROM ordenado atual
  LEFT JOIN ordenado ant
    ON  ant.atleta_id = atual.atleta_id
    AND ant.teste = atual.teste
    AND ant.lado IS NOT DISTINCT FROM atual.lado
    AND ant.ordem = 2
  WHERE atual.ordem = 1
)
SELECT
  par.*,
  CASE
    WHEN valor_anterior IS NULL THEN 'sem_comparacao'
    WHEN variacao_abs = 0
      OR abs(variacao_pct) < (SELECT valor FROM trat.parametro WHERE chave = 'variacao_estavel_pct')
      THEN 'estavel'
    WHEN maior_melhor IS NULL THEN 'sem_classificacao'
    WHEN (variacao_abs > 0) = maior_melhor THEN 'melhorou'
    ELSE 'piorou'
  END AS situacao
FROM par;

-- ---------------------------------------------------------------------------
-- reavaliacao: reavaliações vencidas e a vencer, uma linha por atleta já avaliado.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW api.reavaliacao AS
WITH prazo AS (
  SELECT
    at.atleta_id,
    at.unidade,
    at.ultima_avaliacao_em,
    at.ultima_avaliacao_em
      + (SELECT valor FROM trat.parametro WHERE chave = 'reavaliacao_dias')::int AS vence_em
  FROM api.atleta at
  WHERE at.ultima_avaliacao_em IS NOT NULL
)
SELECT
  atleta_id,
  unidade,
  ultima_avaliacao_em,
  vence_em,
  (vence_em - current_date) AS dias_para_vencer,
  CASE
    WHEN vence_em < current_date THEN 'vencida'
    WHEN vence_em - current_date
         <= (SELECT valor FROM trat.parametro WHERE chave = 'reavaliacao_aviso_dias') THEN 'a_vencer'
    ELSE 'em_dia'
  END AS situacao
FROM prazo;

-- O 01_schemas.sql já dá SELECT nas views novas por ALTER DEFAULT PRIVILEGES; o GRANT
-- explícito cobre o caso de as views terem sido criadas antes dele.
GRANT SELECT ON ALL TABLES IN SCHEMA api TO authenticated, service_role;
