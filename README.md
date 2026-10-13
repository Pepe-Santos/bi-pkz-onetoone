# Projeto BI / SQL

Este projeto cria os schemas iniciais e configura uma conexão FDW para um banco remoto.

## Estrutura
- `01_schemas.sql`: cria os schemas `origem`, `trat` e `api`
- `02_fdw.sql`: configura o PostgreSQL Foreign Data Wrapper para acessar o banco remoto
- `.env`: arquivo local com as variáveis de ambiente

## Arquivo .env
Crie um arquivo `.env` na raiz do projeto com este formato:

```env
SUPABASE_DB_URL=postgresql://usuario:senha@host:5432/banco
REMOTO_HOST=host_remoto
REMOTO_PORT=5432
REMOTO_DB=nome_do_banco_remoto
REMOTO_USER=usuario_remoto
REMOTO_PASSWORD=senha_remota
```

---

## Linux / macOS
No terminal, na raiz do projeto:

```bash
set -a
source .env
set +a

psql "$SUPABASE_DB_URL" -f 01_schemas.sql
psql "$SUPABASE_DB_URL" \
  -v REMOTO_HOST="$REMOTO_HOST" \
  -v REMOTO_PORT="$REMOTO_PORT" \
  -v REMOTO_DB="$REMOTO_DB" \
  -v REMOTO_USER="$REMOTO_USER" \
  -v REMOTO_PASSWORD="$REMOTO_PASSWORD" \
  -f 02_fdw.sql
```

---

## Windows (PowerShell)
No PowerShell, na raiz do projeto:

```powershell
$env:SUPABASE_DB_URL = "postgresql://usuario:senha@host:5432/banco"
$env:REMOTO_HOST = "host_remoto"
$env:REMOTO_PORT = "5432"
$env:REMOTO_DB = "nome_do_banco_remoto"
$env:REMOTO_USER = "usuario_remoto"
$env:REMOTO_PASSWORD = "senha_remota"

psql "$env:SUPABASE_DB_URL" -f .\01_schemas.sql
psql "$env:SUPABASE_DB_URL" `
  -v REMOTO_HOST="$env:REMOTO_HOST" `
  -v REMOTO_PORT="$env:REMOTO_PORT" `
  -v REMOTO_DB="$env:REMOTO_DB" `
  -v REMOTO_USER="$env:REMOTO_USER" `
  -v REMOTO_PASSWORD="$env:REMOTO_PASSWORD" `
  -f .\02_fdw.sql
```

Ou, se quiser carregar o `.env` em uma sessão do PowerShell:

```powershell
Get-Content .env | ForEach-Object {
    if ($_ -match "^\s*#" -or $_ -match "^\s*$") { return }
    $key, $value = $_ -split "=", 2
    $env:$key = $value.Trim('"')
}
```

## Segredos
- A `SUPABASE_SECRET_KEY` ignora todas as permissões. Só vai no `.env` do backend/gerador de relatórios.
- Nunca no GitHub, no front ou em chat. Se vazar: *Project Settings → API Keys*, gere outra e apague a antiga.
- O front usa apenas a publishable key.

## Storage
- Bucket `relatorios` é privado (criado por `sql/03_storage.sql`).
- Usuários acessam os PDFs por URL assinada, gerada pelo backend.

---
