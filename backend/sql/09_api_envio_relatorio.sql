-- Funções da API para o envio automático (relatorios/enviar_lote.py) ler e gravar a
-- trat.envio_relatorio só com a secret key, pela REST do Supabase (POST /rest/v1/rpc/...),
-- sem a senha do banco. Depende do 07_trat_envio_relatorio.sql. Pode rodar quantas vezes
-- quiser (CREATE OR REPLACE).
--
-- Só a secret key (service_role) executa: o EXECUTE é tirado de PUBLIC, anon e
-- authenticated, então o usuário logado na API não lê nem grava envios. As funções são do
-- postgres (SECURITY DEFINER) porque o service_role não tem acesso ao schema trat.

-- Alunos que já receberam o relatório deste período, neste modo (teste ou real).
CREATE OR REPLACE FUNCTION api.relatorios_enviados(periodo text, inicio_periodo date, teste boolean)
RETURNS TABLE (aluno_id uuid)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT e.aluno_id
  FROM trat.envio_relatorio e
  WHERE e.periodo = relatorios_enviados.periodo
    AND e.inicio_periodo = relatorios_enviados.inicio_periodo
    AND e.teste = relatorios_enviados.teste;
$$;

-- Registra um envio. Se já existir (mesmo aluno, período e modo), não faz nada.
CREATE OR REPLACE FUNCTION api.registrar_envio_relatorio(
  aluno_id uuid, unidade text, periodo text, inicio_periodo date, fim_periodo date,
  teste boolean, arquivo text
)
RETURNS void
LANGUAGE sql
VOLATILE
SECURITY DEFINER
SET search_path = ''
AS $$
  INSERT INTO trat.envio_relatorio
    (aluno_id, unidade, periodo, inicio_periodo, fim_periodo, teste, arquivo)
  VALUES
    (registrar_envio_relatorio.aluno_id, registrar_envio_relatorio.unidade,
     registrar_envio_relatorio.periodo, registrar_envio_relatorio.inicio_periodo,
     registrar_envio_relatorio.fim_periodo, registrar_envio_relatorio.teste,
     registrar_envio_relatorio.arquivo)
  ON CONFLICT DO NOTHING;
$$;

REVOKE ALL ON FUNCTION api.relatorios_enviados(text, date, boolean) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION api.registrar_envio_relatorio(uuid, text, text, date, date, boolean, text)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION api.relatorios_enviados(text, date, boolean) TO service_role;
GRANT EXECUTE ON FUNCTION api.registrar_envio_relatorio(uuid, text, text, date, date, boolean, text)
  TO service_role;

-- A API do Supabase passa a enxergar as funções novas sem esperar.
NOTIFY pgrst, 'reload schema';
