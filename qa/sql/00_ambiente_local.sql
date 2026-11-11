-- QA: ambiente local que imita o Supabase, para testar os scripts do back-end com dados
-- sintéticos. SÓ PARA O POSTGRES LOCAL. Nunca rodar no projeto Supabase.
--
-- Cria o mínimo para os scripts 01, 04, 05, 06 e 08 do backend/sql rodarem sem alteração:
--   * papéis anon, authenticated e service_role e as funções auth.jwt() e auth.uid();
--   * tabelas do novo só com as colunas que as views usam;
--   * as views de consumo como na 014 do grupo de Dados (security_invoker = true);
--   * RLS no novo no mesmo espírito da 012: quem não tem perfil no app não vê aluno.

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon')          THEN CREATE ROLE anon NOLOGIN; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN CREATE ROLE authenticated NOLOGIN; END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role')  THEN CREATE ROLE service_role NOLOGIN BYPASSRLS; END IF;
END $$;

CREATE SCHEMA IF NOT EXISTS auth;
-- Igual ao Supabase: o PostgREST põe o token em request.jwt.claims.
CREATE OR REPLACE FUNCTION auth.jwt() RETURNS jsonb LANGUAGE sql STABLE AS $$
  SELECT coalesce(nullif(current_setting('request.jwt.claim', true), ''),
                  nullif(current_setting('request.jwt.claims', true), ''))::jsonb
$$;
CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $$
  SELECT nullif(auth.jwt() ->> 'sub', '')::uuid
$$;
GRANT USAGE ON SCHEMA auth TO anon, authenticated, service_role;

CREATE SCHEMA IF NOT EXISTS novo;
GRANT USAGE ON SCHEMA novo TO authenticated, service_role;

CREATE TABLE IF NOT EXISTS novo.unidade (id int PRIMARY KEY, codigo text NOT NULL);
CREATE TABLE IF NOT EXISTS novo.servico (id int PRIMARY KEY, codigo text NOT NULL, nome text NOT NULL);
CREATE TABLE IF NOT EXISTS novo.pessoa  (id uuid PRIMARY KEY, nome text NOT NULL, data_nascimento date);
CREATE TABLE IF NOT EXISTS novo.perfil_usuario (usuario_id uuid PRIMARY KEY, pessoa_id uuid);
CREATE TABLE IF NOT EXISTS novo.aluno (
  id uuid PRIMARY KEY, pessoa_id uuid NOT NULL REFERENCES novo.pessoa,
  categoria text, status text NOT NULL DEFAULT 'ativo', data_entrada date);
CREATE TABLE IF NOT EXISTS novo.matricula (
  id serial PRIMARY KEY, aluno_id uuid NOT NULL, unidade_id int NOT NULL,
  vigencia_inicio date NOT NULL, vigencia_fim date);
CREATE OR REPLACE VIEW novo.vw_matricula_vigente WITH (security_invoker = true) AS
  SELECT * FROM novo.matricula
  WHERE vigencia_inicio <= current_date AND (vigencia_fim IS NULL OR vigencia_fim >= current_date);
CREATE TABLE IF NOT EXISTS novo.metrica (
  id serial PRIMARY KEY, codigo text UNIQUE NOT NULL, nome text, dominio text,
  unidade_medida text, direcao_desejada text, valor_min numeric, valor_max numeric);
CREATE TABLE IF NOT EXISTS novo.avaliacao (
  id uuid PRIMARY KEY, aluno_id uuid NOT NULL, unidade_id int, data date NOT NULL,
  tipo text NOT NULL DEFAULT 'teste_fisico', status text NOT NULL DEFAULT 'consolidada',
  corrige_avaliacao_id uuid);
CREATE TABLE IF NOT EXISTS novo.avaliacao_medida (
  id serial PRIMARY KEY, avaliacao_id uuid NOT NULL, metrica_id int NOT NULL,
  lado text, tentativa int, valor_num numeric, valor_texto text);
CREATE TABLE IF NOT EXISTS novo.agendamento (
  id uuid PRIMARY KEY, aluno_id uuid, unidade_id int, servico_id int, data date,
  hora_inicio time, status text);
CREATE TABLE IF NOT EXISTS novo.relatorio_treino (
  id uuid PRIMARY KEY, aluno_id uuid, unidade_id int, data date, status text, tipo text,
  tipo_treino text, numero_sessao int, intensidade int, objetivos text, desempenho text,
  evolucao text, observacoes text, dor boolean, dor_local text);

-- Mesmo espírito da 012: todo usuário logado tem SELECT, e o RLS decide as linhas.
-- Quem não tem perfil no app (caso do usuário da API) não enxerga aluno nenhum.
GRANT SELECT ON ALL TABLES IN SCHEMA novo TO authenticated, service_role;
CREATE OR REPLACE FUNCTION novo.enxerga_aluno(p_aluno uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT EXISTS (SELECT 1 FROM novo.perfil_usuario WHERE usuario_id = auth.uid())
$$;
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['pessoa','aluno','matricula','avaliacao','avaliacao_medida',
                           'agendamento','relatorio_treino','perfil_usuario'] LOOP
    EXECUTE format('ALTER TABLE novo.%I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('DROP POLICY IF EXISTS qa_leitura ON novo.%I', t);
  END LOOP;
END $$;
CREATE POLICY qa_leitura ON novo.pessoa           FOR SELECT TO authenticated USING (novo.enxerga_aluno(NULL));
CREATE POLICY qa_leitura ON novo.aluno            FOR SELECT TO authenticated USING (novo.enxerga_aluno(id));
CREATE POLICY qa_leitura ON novo.matricula        FOR SELECT TO authenticated USING (novo.enxerga_aluno(aluno_id));
CREATE POLICY qa_leitura ON novo.avaliacao        FOR SELECT TO authenticated USING (novo.enxerga_aluno(aluno_id));
CREATE POLICY qa_leitura ON novo.avaliacao_medida FOR SELECT TO authenticated USING (novo.enxerga_aluno(NULL));
CREATE POLICY qa_leitura ON novo.agendamento      FOR SELECT TO authenticated USING (novo.enxerga_aluno(aluno_id));
CREATE POLICY qa_leitura ON novo.relatorio_treino FOR SELECT TO authenticated USING (novo.enxerga_aluno(aluno_id));
CREATE POLICY qa_leitura ON novo.perfil_usuario   FOR SELECT TO authenticated USING (usuario_id = auth.uid());

-- Views de consumo, copiadas da 014 do grupo de Dados (colunas e filtros iguais).
CREATE OR REPLACE VIEW novo.vw_aluno WITH (security_invoker = true) AS
SELECT a.id AS aluno_id, p.nome, p.data_nascimento, a.categoria, a.status, a.data_entrada,
       u.codigo AS unidade
FROM novo.aluno a
JOIN novo.pessoa p ON p.id = a.pessoa_id
LEFT JOIN LATERAL (
  SELECT m.unidade_id FROM novo.vw_matricula_vigente m
  WHERE m.aluno_id = a.id
  ORDER BY (m.vigencia_fim IS NULL) DESC, m.vigencia_inicio DESC, m.id
  LIMIT 1
) mv ON true
LEFT JOIN novo.unidade u ON u.id = mv.unidade_id;

CREATE OR REPLACE VIEW novo.vw_avaliacao_medida WITH (security_invoker = true) AS
SELECT v.id AS avaliacao_id, v.aluno_id, u.codigo AS unidade, v.data, v.tipo,
       me.codigo AS metrica_codigo, me.nome AS metrica_nome, me.dominio, me.unidade_medida,
       me.direcao_desejada, me.valor_min, me.valor_max,
       m.lado, m.tentativa, m.valor_num, m.valor_texto
FROM novo.avaliacao_medida m
JOIN novo.avaliacao v ON v.id = m.avaliacao_id
JOIN novo.metrica me  ON me.id = m.metrica_id
LEFT JOIN novo.unidade u ON u.id = v.unidade_id
WHERE v.status = 'consolidada'
  AND v.tipo <> 'fisioterapia'
  AND NOT EXISTS (SELECT 1 FROM novo.avaliacao c
                  WHERE c.corrige_avaliacao_id = v.id AND c.status = 'consolidada');

GRANT SELECT ON novo.vw_aluno, novo.vw_avaliacao_medida TO authenticated, service_role;
