-- Task 2.3 / Preflight do destino.
-- Somente leitura. Executar cada etapa manualmente e somente apos autorizacao.
-- Nao executar uma etapa se a pre-condicao anterior falhar.

-- 1) Identidade da sessao.
-- Esperado: banco, usuario e servidor correspondem ao ambiente aprovado.
-- Bloqueio: qualquer divergencia. current_database() nao identifica sozinho o projeto Supabase.
SELECT current_database() AS banco_atual,
       current_user AS usuario_efetivo,
       session_user AS usuario_da_sessao,
       current_schema() AS schema_atual,
       inet_server_addr() AS endereco_servidor,
       inet_server_port() AS porta_servidor,
       current_setting('server_version') AS versao_postgresql;
-- Confirmar o projeto por canal operacional independente, sem tokens, senhas ou strings de conexao.

-- 2) Schemas e privilegios basicos.
-- Pre-condicao: etapa 1 aprovada.
-- Esperado: novo/origem existem e USAGE esta disponivel.
-- Bloqueio: schema ausente ou USAGE indisponivel.
SELECT s.schema_name,
       n.oid IS NOT NULL AS existe,
       has_schema_privilege(current_user, s.schema_name, 'USAGE') AS possui_usage,
       has_schema_privilege(current_user, s.schema_name, 'CREATE') AS possui_create_informativo
FROM (VALUES ('novo'::name), ('origem'::name)) AS s(schema_name)
LEFT JOIN pg_namespace n ON n.nspname = s.schema_name
ORDER BY s.schema_name;

-- 3) Objetos essenciais de 06_destino_carga.sql.
-- Pre-condicao: etapa 2 aprovada.
-- Esperado: todos existem, tem o relkind esperado e permitem SELECT.
-- Bloqueio: AUSENTE, TIPO_INCOMPATIVEL ou SELECT_INDISPONIVEL.
WITH esperados(schema_name, object_name, expected_kind) AS (
  VALUES
    ('novo','agendamento','r'), ('novo','aluno','r'), ('novo','aluno_servico','r'),
    ('novo','anamnese','r'), ('novo','arquivo','r'), ('novo','atendimento','r'),
    ('novo','avaliacao','r'), ('novo','bloqueio_agenda','r'), ('novo','carga_execucao','r'),
    ('novo','carga_gabarito','r'), ('novo','carga_rejeitado','r'), ('novo','catalogo_item','r'),
    ('novo','credito_lancamento','r'), ('novo','evento_auditoria','r'), ('novo','feedback_treino','r'),
    ('novo','horario_grade','r'), ('novo','lista_espera','r'), ('novo','matricula','r'),
    ('novo','papel','r'), ('novo','papel_usuario','r'), ('novo','perfil_usuario','r'),
    ('novo','pessoa','r'), ('novo','plano','r'), ('novo','profissional','r'),
    ('novo','profissional_servico','r'), ('novo','relatorio_treino','r'), ('novo','renovacao','r'),
    ('novo','servico','r'), ('novo','sessao_treino','r'), ('novo','unidade','r'),
    ('novo','vw_saldo_credito','v'),
    ('origem','nutritionist_files','r'), ('origem','physical_test_comparisons','r'),
    ('origem','physio_assessments','r'), ('origem','physio_evolutions','r'),
    ('origem','specialist_evolutions','r'), ('origem','student_files','r'),
    ('origem','student_tests','r'), ('origem','training_reports','r')
), encontrados AS (
  SELECT e.*, c.oid, c.relkind
  FROM esperados e
  LEFT JOIN pg_namespace n ON n.nspname = e.schema_name
  LEFT JOIN pg_class c ON c.relnamespace = n.oid AND c.relname = e.object_name
)
SELECT schema_name, object_name, expected_kind, oid IS NOT NULL AS existe,
       relkind AS kind_encontrado,
       CASE
         WHEN oid IS NULL THEN 'AUSENTE'
         WHEN relkind <> expected_kind THEN 'TIPO_INCOMPATIVEL'
         WHEN has_table_privilege(current_user, format('%I.%I', schema_name, object_name), 'SELECT')
           THEN 'OK'
         ELSE 'SELECT_INDISPONIVEL'
       END AS preflight_status
FROM encontrados ORDER BY schema_name, object_name;

-- 4) Colunas criticas e tipos PostgreSQL.
-- Pre-condicao: etapa 3 sem bloqueio nos objetos correspondentes.
-- Esperado: timestamp/timestamptz aceitos; pkz_data=jsonb.
-- Bloqueio: AUSENTE ou TIPO_INCOMPATIVEL. Tipos explicitamente nao cobertos ficam NAO_VALIDADO.
WITH esperadas(schema_name, table_name, column_name, regra_tipo) AS (
  VALUES
    ('novo','carga_gabarito','rotulo','texto'),
    ('novo','carga_gabarito','registrado_em','timestamp_ou_timestamptz'),
    ('novo','carga_gabarito','tabela','texto'), ('novo','carga_gabarito','linhas','numerico'),
    ('novo','carga_rejeitado','script','texto'), ('novo','carga_rejeitado','tabela_origem','texto'),
    ('novo','carga_rejeitado','motivo','texto'), ('novo','carga_rejeitado','id_origem','numerico_ou_nao_validado'),
    ('novo','carga_execucao','script','texto'), ('novo','carga_execucao','executado_em','timestamp_ou_timestamptz'),
    ('novo','carga_execucao','linhas_carregadas','numerico'), ('novo','carga_execucao','linhas_rejeitadas','numerico'),
    ('origem','physio_assessments','pkz_data','jsonb')
)
SELECT e.schema_name, e.table_name, e.column_name, e.regra_tipo,
       a.attname IS NOT NULL AS existe,
       CASE WHEN a.attname IS NOT NULL THEN format_type(a.atttypid, a.atttypmod) END AS tipo_encontrado,
       CASE
         WHEN a.attname IS NULL THEN 'AUSENTE'
         WHEN e.regra_tipo = 'jsonb' AND a.atttypid = 'jsonb'::regtype THEN 'OK'
         WHEN e.regra_tipo = 'jsonb' THEN 'TIPO_INCOMPATIVEL'
         WHEN e.regra_tipo = 'timestamp_ou_timestamptz'
           AND a.atttypid IN ('timestamp'::regtype, 'timestamptz'::regtype) THEN 'OK'
         WHEN e.regra_tipo = 'timestamp_ou_timestamptz' THEN 'TIPO_INCOMPATIVEL'
         WHEN e.regra_tipo = 'texto'
           AND a.atttypid IN ('text'::regtype, 'varchar'::regtype, 'bpchar'::regtype, 'name'::regtype) THEN 'OK'
         WHEN e.regra_tipo = 'numerico'
           AND a.atttypid IN ('smallint'::regtype, 'integer'::regtype, 'bigint'::regtype, 'numeric'::regtype, 'decimal'::regtype) THEN 'OK'
         WHEN e.regra_tipo = 'numerico_ou_nao_validado' THEN 'NAO_VALIDADO'
         ELSE 'TIPO_INCOMPATIVEL'
       END AS tipo_status
FROM esperadas e
LEFT JOIN pg_namespace n ON n.nspname = e.schema_name
LEFT JOIN pg_class c ON c.relnamespace = n.oid AND c.relname = e.table_name
LEFT JOIN pg_attribute a ON a.attrelid = c.oid AND a.attname = e.column_name
  AND a.attnum > 0 AND NOT a.attisdropped
ORDER BY e.schema_name, e.table_name, e.column_name;

-- 5) View de saldo.
-- Pre-condicao: etapa 3 confirma a existencia da view.
-- Esperado: relkind=v, SELECT disponivel e aluno_id/servico_id/saldo presentes.
-- Bloqueio: VIEW_AUSENTE, TIPO_INCOMPATIVEL, SELECT_INDISPONIVEL ou COLUNA_CRITICA_AUSENTE.
WITH estado AS (SELECT EXISTS (SELECT 1 FROM pg_namespace n JOIN pg_class c ON c.relnamespace = n.oid AND c.relname = 'vw_saldo_credito' WHERE n.nspname = 'novo') AS existe_view),
esperado(coluna, tipo) AS (
  VALUES ('aluno_id'::name, 'nao_validado'), ('servico_id'::name, 'nao_validado'),
         ('saldo'::name, 'numerico')
), view_info AS (
  SELECT c.oid, c.relkind FROM pg_namespace n
  LEFT JOIN pg_class c ON c.relnamespace = n.oid AND c.relname = 'vw_saldo_credito'
  WHERE n.nspname = 'novo'
), colunas AS (
  SELECT e.coluna, e.tipo, a.attname, a.atttypid, a.atttypmod
  FROM esperado e CROSS JOIN view_info v
  LEFT JOIN pg_attribute a ON a.attrelid = v.oid AND a.attname = e.coluna
    AND a.attnum > 0 AND NOT a.attisdropped
)
SELECT CASE
         WHEN v.oid IS NULL THEN 'VIEW_AUSENTE'
         WHEN v.relkind <> 'v' THEN 'TIPO_INCOMPATIVEL'
         WHEN NOT has_table_privilege(current_user, 'novo.vw_saldo_credito', 'SELECT') THEN 'SELECT_INDISPONIVEL'
         WHEN EXISTS (SELECT 1 FROM colunas WHERE attname IS NULL) THEN 'COLUNA_CRITICA_AUSENTE'
         WHEN EXISTS (SELECT 1 FROM colunas WHERE tipo = 'numerico'
           AND atttypid NOT IN ('smallint'::regtype, 'integer'::regtype, 'bigint'::regtype,
                                'numeric'::regtype, 'decimal'::regtype)) THEN 'TIPO_INCOMPATIVEL'
         ELSE 'OK'
       END AS preflight_status,
       v.oid IS NOT NULL AS existe, v.relkind,
       has_table_privilege(current_user, 'novo.vw_saldo_credito', 'SELECT') AS possui_select,
       (SELECT COUNT(*) FROM colunas WHERE attname IS NULL) AS colunas_criticas_ausentes,
       (SELECT COUNT(*) FROM colunas WHERE tipo = 'numerico'
          AND atttypid NOT IN ('smallint'::regtype, 'integer'::regtype, 'bigint'::regtype,
                               'numeric'::regtype, 'decimal'::regtype)) AS colunas_com_tipo_incompativel
FROM estado e LEFT JOIN view_info v ON true;

SELECT e.coluna AS coluna_critica, a.attname IS NOT NULL AS existe,
       CASE WHEN a.attname IS NOT NULL THEN format_type(a.atttypid, a.atttypmod) END AS tipo_encontrado
FROM (VALUES ('aluno_id'::name), ('servico_id'::name), ('saldo'::name)) AS e(coluna)
LEFT JOIN pg_namespace n ON n.nspname = 'novo'
LEFT JOIN pg_class c ON c.relnamespace = n.oid AND c.relname = 'vw_saldo_credito'
LEFT JOIN pg_attribute a ON a.attrelid = c.oid AND a.attname = e.coluna
  AND a.attnum > 0 AND NOT a.attisdropped
ORDER BY e.coluna;

-- 6) Snapshot do gabarito.
-- Pre-condicao: carga_gabarito existe e permite SELECT.
-- Esperado: uma linha mesmo sem snapshot; rotulo e pertinencia exigem confirmacao operacional.
-- Bloqueio: GABARITO_INEXISTENTE, empate de rotulos, SEM_TABELA_NO_GABARITO ou duplicidade nao explicada.
WITH estado AS (SELECT EXISTS (SELECT 1 FROM novo.carga_gabarito) AS existe_snapshot),
rotulos AS (
  SELECT rotulo, MAX(registrado_em) AS registrado_em_mais_recente FROM novo.carga_gabarito GROUP BY rotulo
), maximo AS (SELECT MAX(registrado_em_mais_recente) AS timestamp_maximo FROM rotulos),
empate AS (
  SELECT COUNT(*) AS rotulos_no_timestamp_maximo FROM rotulos r CROSS JOIN maximo m
  WHERE r.registrado_em_mais_recente IS NOT DISTINCT FROM m.timestamp_maximo
), escolhido AS (
  SELECT r.rotulo, r.registrado_em_mais_recente FROM rotulos r CROSS JOIN maximo m
  WHERE r.registrado_em_mais_recente IS NOT DISTINCT FROM m.timestamp_maximo
    AND (SELECT rotulos_no_timestamp_maximo FROM empate) = 1
)
SELECT CASE
         WHEN NOT e.existe_snapshot THEN 'GABARITO_INEXISTENTE'
         WHEN (SELECT rotulos_no_timestamp_maximo FROM empate) > 1 THEN 'INCONCLUSIVO_ROTULO_EMPATE'
         WHEN c.rotulo IS NULL OR COUNT(g.tabela) = 0 THEN 'SEM_TABELA_NO_GABARITO'
         ELSE 'ROTULO_IDENTIFICADO_CONFIRMACAO_OPERACIONAL_PENDENTE'
       END AS preflight_status,
       e.existe_snapshot, c.rotulo AS rotulo_mais_recente, c.registrado_em_mais_recente,
       (SELECT rotulos_no_timestamp_maximo FROM empate) AS rotulos_no_timestamp_maximo,
       COUNT(g.tabela) AS quantidade_tabelas,
       COUNT(*) FILTER (WHERE g.linhas IS NULL) AS contagens_nulas,
       COUNT(*) FILTER (WHERE g.tabela IS NULL) AS tabelas_nulas
FROM estado e LEFT JOIN escolhido c ON true
LEFT JOIN novo.carga_gabarito g ON g.rotulo = c.rotulo
GROUP BY e.existe_snapshot, c.rotulo, c.registrado_em_mais_recente;
WITH rotulos AS (
  SELECT rotulo, MAX(registrado_em) AS registrado_em_mais_recente
  FROM novo.carga_gabarito GROUP BY rotulo
), maximo AS (
  SELECT MAX(registrado_em_mais_recente) AS timestamp_maximo FROM rotulos
), escolhido AS (
  SELECT r.rotulo FROM rotulos r CROSS JOIN maximo m
  WHERE r.registrado_em_mais_recente IS NOT DISTINCT FROM m.timestamp_maximo
    AND (SELECT COUNT(*) FROM rotulos r2 CROSS JOIN maximo m2
         WHERE r2.registrado_em_mais_recente IS NOT DISTINCT FROM m2.timestamp_maximo) = 1
)
SELECT g.tabela, COUNT(*) AS ocorrencias_no_rotulo,
       COUNT(*) FILTER (WHERE g.linhas IS NULL) AS ocorrencias_com_linhas_nulas
FROM novo.carga_gabarito g JOIN escolhido e ON e.rotulo = g.rotulo
GROUP BY g.tabela HAVING COUNT(*) > 1 ORDER BY g.tabela;
-- O rotulo mais recente nao e automaticamente o rotulo correto do ensaio.

-- 7) Esquema real de carga_execucao e desempate.
-- Pre-condicao: carga_execucao existe e permite SELECT.
-- Esperado: esquema real documentado antes de consultar historico.
-- Bloqueio: executado_em ausente/incompativel ou ausencia de PK/identificador confiavel.
SELECT ordinal_position, column_name, data_type, udt_schema, udt_name, is_nullable
FROM information_schema.columns
WHERE table_schema = 'novo' AND table_name = 'carga_execucao'
ORDER BY ordinal_position;
SELECT con.conname AS constraint_name, con.contype AS constraint_type,
       ARRAY_AGG(att.attname ORDER BY key.ord) AS colunas
FROM pg_constraint con
JOIN pg_class c ON c.oid = con.conrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN LATERAL unnest(con.conkey) WITH ORDINALITY AS key(attnum, ord) ON true
JOIN pg_attribute att ON att.attrelid = c.oid AND att.attnum = key.attnum
WHERE n.nspname = 'novo' AND c.relname = 'carga_execucao' AND con.contype IN ('p','u')
GROUP BY con.conname, con.contype;

-- 8) Historico dos oito scripts.
-- Executar somente apos a etapa 7. Esta consulta nao presume coluna id.
-- Sem chave primaria ou chave composta cuja semantica seja validada como identificador de execucao,
-- a comparacao das duas ultimas execucoes permanece INCONCLUSIVA.
-- A etapa 7 apenas levanta o schema; nao autoriza escolher uma coluna UNIQUE isolada.
WITH esperados(script) AS (
  VALUES ('referencia'),('cadastro'),('comercial'),('agenda'),
         ('relatorio'),('avaliacao'),('atendimento'),('documentos')
), resumo AS (
  SELECT e.script, COUNT(c.script) AS quantidade_execucoes,
         COUNT(DISTINCT c.executado_em) AS horarios_distintos
  FROM esperados e LEFT JOIN novo.carga_execucao c ON c.script = e.script
  GROUP BY e.script
)
SELECT script, quantidade_execucoes, horarios_distintos,
       quantidade_execucoes >= 2 AS possui_duas_execucoes,
       CASE
         WHEN quantidade_execucoes < 2 THEN 'INCONCLUSIVO_HISTORICO_INSUFICIENTE'
         ELSE 'INCONCLUSIVO_DESEMPATE_E_SEMANTICA_NAO_CONFIRMADOS'
       END AS historico_status,
       'A comparacao valida exige chave de execucao confirmada na etapa 7 e revisao operacional da sua semantica.'
         AS condicao_para_comparacao_valida
FROM resumo ORDER BY script;

-- 9) Permissoes e RLS; nao contorna RLS nem eleva privilegios.
-- Esperado: SELECT e politicas documentados.
-- Bloqueio: SELECT ausente, politica desconhecida ou visibilidade nao explicada.
SELECT n.nspname AS schema_name, c.relname AS object_name, c.relkind,
       c.relrowsecurity AS rls_habilitado, c.relforcerowsecurity AS rls_forcado,
       has_table_privilege(current_user, format('%I.%I', n.nspname, c.relname), 'SELECT') AS possui_select
FROM pg_namespace n JOIN pg_class c ON c.relnamespace = n.oid
WHERE n.nspname IN ('novo','origem')
  AND c.relname IN ('carga_gabarito','carga_rejeitado','carga_execucao','vw_saldo_credito',
    'physio_assessments','student_files','nutritionist_files','physio_evolutions',
    'specialist_evolutions','training_reports','physical_test_comparisons','student_tests',
    'arquivo','credito_lancamento','renovacao')
ORDER BY n.nspname, c.relname;
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies WHERE schemaname IN ('novo','origem')
ORDER BY schemaname, tablename, policyname;

-- 10) JSONB condicional e separada.
-- Executar somente apos confirmar ambiente, tabela, SELECT e pkz_data=jsonb na etapa 4.
-- Bloqueio: qualquer valor nao-objeto impede a conferencia de arquivos derivada.
SELECT COUNT(*) AS total_registros,
       COUNT(*) FILTER (WHERE pkz_data IS NULL) AS pkz_data_nulo,
       COUNT(*) FILTER (WHERE jsonb_typeof(pkz_data) = 'object') AS objetos_json,
       COUNT(*) FILTER (WHERE pkz_data IS NOT NULL AND jsonb_typeof(pkz_data) <> 'object') AS valores_nao_objeto
FROM origem.physio_assessments;

-- Riscos remanescentes:
-- current_database() nao autentica o projeto Supabase; exige confirmacao externa.
-- SELECT e catalogos nao demonstram visibilidade integral sob RLS.
-- Sem identificador unico validado, empates em executado_em mantem o historico inconclusivo.
-- O snapshot mais recente pode nao ser o snapshot correto do ensaio.
-- Nenhuma consulta deste arquivo homologa a Task 2.3.