-- Registro dos relatórios já enviados por e-mail (relatorios/enviar_lote.py), para não
-- reenviar o mesmo período ao mesmo aluno. Pode rodar quantas vezes quiser (IF NOT EXISTS).
-- Não depende do novo: pode rodar logo depois do 01_schemas.sql. Os scripts 05 e 06 não
-- mexem nesta tabela.
--
-- Só o enviar_lote.py escreve aqui, pela conexão direta ao banco (SUPABASE_DB_URL). A tabela
-- não fica na API: o schema trat não está em Exposed schemas.
CREATE TABLE IF NOT EXISTS trat.envio_relatorio (
  aluno_id       uuid        NOT NULL,                  -- = novo.vw_aluno.aluno_id
  unidade        text        NOT NULL CHECK (unidade IN ('PKZ', 'ONE_TO_ONE')),
  periodo        text        NOT NULL CHECK (periodo IN ('semanal', 'mensal', 'anual')),
  inicio_periodo date        NOT NULL,
  fim_periodo    date        NOT NULL,
  teste          boolean     NOT NULL,                  -- true: enviado em modo teste (para o grupo, não para o aluno)
  arquivo        text        NOT NULL,                  -- caminho do PDF no bucket relatorios
  enviado_em     timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (aluno_id, periodo, inicio_periodo, teste)
);

COMMENT ON TABLE trat.envio_relatorio IS
  'Um registro por relatório enviado por e-mail (aluno, período e modo). O envio de teste não impede o envio real do mesmo período. Sem e-mail nem nome do aluno: só o UUID.';
