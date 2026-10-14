# Back-end

**Branch:** `backend` · **Equipe:** Ewerton Arrais, Miguel Veiga, Felipe

Lê o banco do app (somente leitura), transforma os dados e os expõe como contrato para Relatórios e Front-end.

## Escopo

- Conexão com a origem via `postgres_fdw` (schema `origem_pkz`) e usuário com leitura apenas nas tabelas usadas.
- Schema `core` (modelo canônico) e carga horária em SQL com Supabase Cron, numa transação única.
- Conversão de unidades pelo catálogo de métricas e lista de revisão para valores implausíveis.
- Schema `api` com as 10 views consumidas pela API REST do Supabase.
- Segurança: RLS por unidade, chave de serviço só no servidor.
- Plano B: extração em Python agendada, caso o FDW não suba.

**Fora do escopo:** cadastro, agenda, login, cobrança, telas e geração de PDF.

## Estrutura sugerida

```
backend/
├── sql/
│   ├── 01_origem/     # FDW e foreign tables
│   ├── 02_core/       # tabelas do modelo canônico
│   ├── 03_carga/      # funções de carga e agendamento
│   └── 04_api/        # views da API
└── plano-b/           # extração em Python
```

## Regras

- Mudança em view da `api` = PR revisado também por Relatórios e Front-end.
- Teste com dados sintéticos; nada da produção ou da cópia no repositório.
