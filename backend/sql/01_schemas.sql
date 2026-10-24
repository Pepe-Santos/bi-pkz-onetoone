-- Cria os schemas do Grupo de Desenvolvimento. Pode rodar quantas vezes quiser (IF NOT EXISTS).
-- Roda no mesmo projeto Supabase do banco novo do grupo de Dados. Não cria nem altera
-- os schemas novo, origem e public, que pertencem ao grupo de Dados e ao app.
CREATE SCHEMA IF NOT EXISTS trat;    -- regras de tratamento e dados tratados
CREATE SCHEMA IF NOT EXISTS api;     -- views finais que a API expõe

-- Permite que a API automática (PostgREST) leia o schema api: authenticated é o usuário
-- logado; service_role é quem chama com a secret key (gerador de relatórios).
GRANT USAGE ON SCHEMA api TO authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA api GRANT SELECT ON TABLES TO authenticated, service_role;
GRANT SELECT ON ALL TABLES IN SCHEMA api TO authenticated, service_role;
