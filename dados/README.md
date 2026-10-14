# Dados — Modelagem & Banco

**Branch:** `dados` · **Equipe:** Rafael, Iago, Micael

Define como os dados do projeto são organizados: diagnóstico da base atual, modelo de dados e reestruturação.

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

## Regras

- Só estrutura e scripts: nenhum dado real, dump ou CSV da produção ou da cópia.
- Mudança no modelo que afete o `core` ou a `api` = PR revisado também pelo Back-end.
