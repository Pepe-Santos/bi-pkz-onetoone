# Dados — Modelagem & Banco

**Branch:** `dados` · **Membros:** Micael, Rafael, Iago

Estrutura o banco novo do projeto (schema `novo`) e carrega nele os dados do app, a partir de uma foto congelada da origem: diagnóstico da base atual, modelo de dados, reestruturação e conferência origem × destino. O grupo de Desenvolvimento lê direto do `novo`; mudanças de estrutura nas tabelas que ele usa são avisadas antes.

## Escopo

- Dicionário de dados e domínios (Atleta, Treino, Avaliação).
- Catálogo de métricas: unidade, direção, conversão e faixa plausível de cada teste.
- `ENT-001` — modelo de dados documentado (homologação no marco M2).
- `ENT-002` — base reestruturada: construída, carregada e conferida no ensaio pela Frente 1 (tarefas 1.1 a 1.7, em [`migracoes/`](migracoes/)); na `main` desde 21/10.
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
| [`migrations/`](migracoes/migrations/) | DDL 001–011: 43 tabelas e 5 views no schema `novo`, um arquivo por domínio; 012: políticas de acesso por papel (Frente 3), aplicada no ensaio em 26/10 |
| [`mapeamento/`](migracoes/mapeamento/) | De/para coluna a coluna, origem → destino (só estrutura e regras, sem dados) e o **catálogo das 109 métricas** (`avaliacao_metricas.csv`: unidade, direção, conversão e faixa) |
| [`carga/`](migracoes/carga/) | Scripts de carga 10–80 por domínio e o mestre `99_carga_mestre.sql`; todos podem rodar mais de uma vez sem duplicar |
| [`conferencia/`](migracoes/conferencia/) | Conferências só de leitura: estrutura do DDL, cobertura do mapeamento (`01`, reproduzível), papéis × unidade (`02`), saldo de créditos (`03`) e conferência geral origem × destino (`99`) |
| [`ensaio/`](migracoes/ensaio/) | Foto da origem, estrutura da origem para teste local e dados inventados |

Regras do grupo: [`CONVENCOES.md`](migracoes/CONVENCOES.md) · decisões em aberto: [`PENDENCIAS.md`](migracoes/PENDENCIAS.md).

### Segurança e dicionário: [`seguranca/`](seguranca/) e [`dicionario/`](dicionario/) (Frente 3, Iago)

- [`seguranca/matriz-papeis.md`](seguranca/matriz-papeis.md): quem lê o quê, por papel; é a especificação da migration 012.
- [`seguranca/decisoes-dado-sensivel.md`](seguranca/decisoes-dado-sensivel.md): as decisões de gestão que faltam sobre dado sensível (pendências 4, 5 e 11).
- [`dicionario/`](dicionario/): dicionário de dados do `novo`, coluna a coluna, com a sensibilidade de cada uma.
- [`plano-projeto-definitivo.md`](plano-projeto-definitivo.md): passo a passo da virada para o projeto definitivo (tarefa 3.6, proposta).

### Modelo conceitual: [`modelo/conceitual/`](modelo/conceitual/)

Notação de Chen, em 7 diagramas (visão geral e 6 domínios). A v2 (16/10) mostra em verde, com etiquetas M1–M24, o que mudou na construção do banco, e tem 2 páginas de registro de mudanças.

- `Modelo_Conceitual_Chen_PKZ_OnetoOne_v2.pdf`: o modelo atual.
- `fontes-dot/`: fontes da v1 (Graphviz).
- `fontes-dot-v2/`: fontes da v2 e o gerador (`python gerar_v2.py` refaz os PDFs em `fontes-dot-v2/pdf/`; precisa do Graphviz e do Playwright).

## Regras

- Só estrutura, scripts e contagens: nenhum dado real, dump ou CSV com registros da produção ou da cópia. Os CSV de `migracoes/mapeamento/` descrevem colunas e regras, sem nenhuma linha de dado (o README principal permite mapeamentos em CSV; o `.gitignore` da pasta os libera).
- Mudança de estrutura em tabela do `novo` usada pelo Desenvolvimento: avisar o grupo **antes** (combinado de 20/10) e pedir revisão do Desenvolvimento no PR.
