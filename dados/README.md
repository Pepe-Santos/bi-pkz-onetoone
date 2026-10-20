# Dados — Modelagem & Banco

**Branch:** `dados` · **Membros:** Micael, Rafael, Iago

Consome os dados tratados pelo back-end e estrutura o banco próprio do projeto: diagnóstico da base atual, modelo de dados e reestruturação.

## Escopo

- Dicionário de dados e domínios (Atleta, Treino, Avaliação).
- Catálogo de métricas: unidade, direção, conversão e faixa plausível de cada teste.
- `ENT-001` — modelo de dados documentado (homologação no marco M2).
- `ENT-002` — base reestruturada, executada em 7 fases após o M2.
- Modelo analítico em estrela (7 dimensões, 6 fatos) para os dashboards.
- Modelo conceitual do banco (seção 5.3 da documentação geral).

## Estrutura sugerida

```
dados/
├── dicionario/    # dicionário de dados e domínios
├── modelo/        # diagramas (conceitual, lógico, estrela)
├── catalogo/      # catálogo de métricas
└── migracoes/     # scripts de reestruturação por fase
```

## O que já está aqui

### Banco reestruturado: [`migracoes/`](migracoes/) (Frente 1, Micael)

Estrutura nova do banco (DDL) e scripts que carregam os dados do app para ela, testados no ensaio sobre uma foto congelada da origem. Comece pelo [README da pasta](migracoes/README.md).

| Pasta | O que tem |
|---|---|
| [`migrations/`](migracoes/migrations/) | DDL 001–011: 43 tabelas e 5 views no schema `novo`, um arquivo por domínio |
| [`mapeamento/`](migracoes/mapeamento/) | De/para coluna a coluna, origem → destino (só estrutura e regras, sem dados) e o **catálogo das 109 métricas** (`avaliacao_metricas.csv`: unidade, direção, conversão e faixa) |
| [`carga/`](migracoes/carga/) | Scripts de carga 10–80 por domínio e o mestre `99_carga_mestre.sql`; todos podem rodar mais de uma vez sem duplicar |
| [`conferencia/`](migracoes/conferencia/) | Conferência da estrutura e conferência geral origem × destino (só leitura) |
| [`ensaio/`](migracoes/ensaio/) | Foto da origem, estrutura da origem para teste local e dados inventados |

Regras do grupo: [`CONVENCOES.md`](migracoes/CONVENCOES.md) · decisões em aberto: [`PENDENCIAS.md`](migracoes/PENDENCIAS.md).

### Modelo conceitual: [`modelo/conceitual/`](modelo/conceitual/)

Notação de Chen, em 7 diagramas (visão geral e 6 domínios). A v2 (16/10) mostra em verde, com etiquetas M1–M24, o que mudou na construção do banco, e tem 2 páginas de registro de mudanças.

- `Modelo_Conceitual_Chen_PKZ_OnetoOne_v2.pdf`: o modelo atual.
- `fontes-dot/`: fontes da v1 (Graphviz).
- `fontes-dot-v2/`: fontes da v2 e o gerador (`python gerar_v2.py` refaz os PDFs em `fontes-dot-v2/pdf/`; precisa do Graphviz e do Playwright).

## Regras

- Só estrutura e scripts: nenhum dado real, dump ou CSV da produção ou da cópia. Os CSV de `migracoes/mapeamento/` são a exceção liberada no `.gitignore` da pasta: descrevem colunas e regras, sem nenhuma linha de dado.
- Mudança no modelo que afete o `core` ou a `api` = PR revisado também pelo Desenvolvimento.
