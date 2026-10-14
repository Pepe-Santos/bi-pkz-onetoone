# QA — Testes de qualidade

**Branch:** `qa`

Garante que os dados, a API e os relatórios estão corretos antes de chegarem ao cliente. É a frente que conduz as **duas semanas de margem antes da P2**.

## Escopo

- **Dados:** contagens origem × `core`, conversão de unidades, valores fora da faixa plausível, duplicidades.
- **Regras de negócio:** presença, variação “estável” (< 2%), reavaliação em 90 dias, nível por letra (PKZ), 1RM por Epley, carga aguda/crônica (0,8–1,3), assimetria (10%).
- **API:** cada view devolve os campos e formatos do contrato com Relatórios e Front-end.
- **Relatórios:** os 6 layouts gerados com dados curtos, longos e incompletos; fontes, gráficos e página no tamanho certo.
- **Segurança e LGPD:** sem acesso anônimo, cada unidade vê só os próprios dados, nenhum dado sensível fora da origem.
- **Integração:** testes ponta a ponta da origem até o PDF enviado por e-mail.

## Estrutura sugerida

```
qa/
├── casos-de-teste/   # checklists e casos por frente
├── dados-sinteticos/ # massas de teste fictícias (geradas por script)
├── sql/              # testes de integridade e de regras
└── e2e/              # testes ponta a ponta
```

## Regras

- Bug encontrado vira task no ClickUp, com a frente responsável e o passo a passo para reproduzir.
- Só dados sintéticos; nenhum dado real de aluno, nem para reproduzir um bug.
