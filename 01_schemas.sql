-- Cria os schemas do projeto. Pode rodar quantas vezes quiser (IF NOT EXISTS).
CREATE SCHEMA IF NOT EXISTS origem;  -- tabelas "virtuais" vindas do banco do grupo de Dados (FDW)
CREATE SCHEMA IF NOT EXISTS trat;    -- views de dados tratados
CREATE SCHEMA IF NOT EXISTS api;     -- views finais que a API expõe

-- Permite que a API automática (PostgREST) leia o schema api
GRANT USAGE ON SCHEMA api TO anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA api GRANT SELECT ON TABLES TO anon, authenticated;
