# Desenvolvimento — Back-end

**Branch:** `backend` · **Grupo:** Desenvolvimento · **Membros:** Ewerton Arrais, Miguel Veiga, Gian, Henrique, Christian, Rafael

O grupo de Desenvolvimento cuida da aplicação, da área de tratamento de dados, da API que será consumida e da automação da geração e do envio dos relatórios por e-mail. Esta pasta guarda a parte de back-end; os relatórios ficam em [`relatorios/`](../relatorios/) e as telas em [`frontend/`](../frontend/), todos na mesma branch.

## Escopo do back-end

- Conexão com a origem via `postgres_fdw` (schema `origem_pkz`) e usuário com leitura apenas nas tabelas usadas.
- Schema `core` (modelo canônico) e carga horária em SQL com Supabase Cron, numa transação única.
- Conversão de unidades pelo catálogo de métricas e lista de revisão para valores implausíveis.
- Schema `api` com as 10 views consumidas pela API REST do Supabase.
- Segurança: RLS por unidade, chave de serviço só no servidor.
- Plano B: extração em Python agendada, caso o FDW não suba.

- Automação da geração dos relatórios (template → PDF) e do envio mensal por e-mail.

**Fora do escopo:** cadastro, agenda, login e cobrança, que continuam no app do cliente.

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

- Mudança em view da `api` = PR revisado também por Dados e QA.
- Teste com dados sintéticos; nada da produção ou da cópia no repositório.
