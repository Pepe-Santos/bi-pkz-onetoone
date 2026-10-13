-- Conecta ao banco do grupo de Dados (somente leitura).
-- As credenciais NÃO ficam aqui: vêm de variáveis do psql (veja o README).
CREATE EXTENSION IF NOT EXISTS postgres_fdw;

DROP SERVER IF EXISTS dados_remoto CASCADE;  -- permite refazer do zero
CREATE SERVER dados_remoto
  FOREIGN DATA WRAPPER postgres_fdw
  OPTIONS (host :'REMOTO_HOST', port :'REMOTO_PORT', dbname :'REMOTO_DB');

CREATE USER MAPPING FOR postgres
  SERVER dados_remoto
  OPTIONS (user :'REMOTO_USER', password :'REMOTO_PASSWORD');

-- Traz as tabelas remotas para o schema origem.
-- Troque 'public' pelo schema onde estão os dados do grupo de Dados.
IMPORT FOREIGN SCHEMA public FROM SERVER dados_remoto INTO origem;
