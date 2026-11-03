#!/usr/bin/env bash
# Roda os testes de QA do back-end num PostgreSQL LOCAL (nunca no Supabase).
# Uso: na raiz do repositório, na branch backend (ou com os scripts de backend/sql):
#   PGURL=postgresql://postgres@localhost:5432/postgres bash qa/rodar_testes_local.sh
# Cria (e recria) o banco qa_local.
set -euo pipefail
PGURL="${PGURL:-postgresql://postgres@localhost:5432/postgres}"
DB_URL="${PGURL%/*}/qa_local"
psql "$PGURL" -qc 'DROP DATABASE IF EXISTS qa_local' -c 'CREATE DATABASE qa_local'
for f in qa/sql/00_ambiente_local.sql backend/sql/01_schemas.sql \
         backend/sql/04_trat_parametros_catalogo.sql qa/sql/01_dados_sinteticos.sql \
         backend/sql/05_trat_medidas.sql backend/sql/06_api_avaliacoes.sql \
         backend/sql/08_api_treinos.sql; do
  psql "$DB_URL" -q -v ON_ERROR_STOP=1 -f "$f" >/dev/null 2>&1 || { echo "Falhou em $f"; exit 1; }
done
psql "$DB_URL" -q -f qa/sql/10_testes_tratamento.sql

# Massa dos PDFs e tabela de envios, para os testes de ponta a ponta (qa/e2e/)
psql "$DB_URL" -q -v ON_ERROR_STOP=1 -f qa/sql/02_dados_relatorio.sql >/dev/null
psql "$DB_URL" -q -v ON_ERROR_STOP=1 -f backend/sql/07_trat_envio_relatorio.sql >/dev/null
if [ -f backend/sql/09_api_envio_relatorio.sql ]; then
  psql "$DB_URL" -q -v ON_ERROR_STOP=1 -f backend/sql/09_api_envio_relatorio.sql >/dev/null
fi
echo "Banco qa_local pronto para qa/e2e/api_local.py"
