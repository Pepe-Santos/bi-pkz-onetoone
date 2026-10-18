# Projeto BI — PKZ × One to One

Camada de dados e indicadores para as duas unidades do cliente, construída **sobre** o aplicativo operacional atual (feito no Lovable), sem alterá-lo.

| Unidade | Público | Relatório |
|---|---|---|
| **Playmakerz Lab (PKZ)** — Loja G | Treino funcional infantil (ex.: Sub 12, Sub 14/15; futebol e futsal) | Evolução nos testes físicos, para **pais e responsáveis** |
| **One to One Studio (OTO)** — Loja I | Personal para jovens adultos e adultos | Histórico de treinos, carga e progressão, para o **aluno** |

> **Repositório público.** Tudo o que for enviado aqui fica visível para qualquer pessoa. Dados do cliente, credenciais e a documentação confidencial ficam fora — veja [Regras do repositório](#regras-do-repositório) antes do primeiro commit.

---

## Entregas

1. **Dashboards** de treino e rendimento (painel gerencial `DSH-001`, evolução do atleta `DSH-003`, painel comparativo).
2. **Relatórios automáticos** em PDF a partir de template fixo — semanal, mensal e anual, para cada unidade (6 layouts).
3. **Banco de dados reestruturado** que sustenta os dois itens acima.

**Objetivo final:** envio automático dos relatórios mensais por e-mail.

### Requisitos estruturantes

- **Somente leitura na origem** — o banco do app do cliente nunca recebe escrita do projeto.
- **Transformação independente da origem** — uma nova origem exige só um novo mapeamento.
- **Relatórios padronizados**, gerados automaticamente a partir de template fixo.
- **LGPD** — há dados de menores e de saúde (dor): coleta mínima, controle de acesso e consentimento do responsável.

---

## Arquitetura

```
Banco do app (Lovable / Supabase) ── somente leitura
        │  postgres_fdw
        ▼
origem_pkz        tabelas do app enxergadas via FDW (6 de 28 tabelas + 1 opcional)
        │  carga horária em SQL (Supabase Cron), transação única
        ▼
core              modelo canônico: atleta, profissional, avaliacao, medida,
        │         sessao_treino, agendamento, metrica (catálogo)
        ▼
api               10 views expostas pela API REST do Supabase
        │
        ▼
Consumidores      front-end · dashboards · relatórios (PDF) · IA
```

- **Carga:** lê a origem, abre o JSON das avaliações, converte unidades pelo catálogo, separa valores implausíveis numa lista de revisão e confere contagens — qualquer divergência desfaz tudo e os dados anteriores continuam servindo.
- **Plano B** se o FDW não subir: extração em Python agendada.
- **Views da API:** `atleta`, `evolucao`, `comparacao`, `reavaliacao`, `ultimo_treino`, `agenda_dia`, `treino_mes`, `relatorio_pendente`, `indicador_mes`, `revisao_dados`.

### Stack

| Camada | Tecnologia |
|---|---|
| Banco e transformação | PostgreSQL (Supabase), `postgres_fdw`, SQL, Supabase Cron |
| API | API REST automática do Supabase sobre o schema `api` |
| Relatórios | Template HTML/CSS · Chart.js ou SVG · Puppeteer ou Playwright → PDF · endpoint de geração |
| Front-end | Sistema administrativo (31 telas, mobile-first) e painel comparativo |
| Dashboard | **A definir** — Power BI, aplicação própria ou extensão do app |

### Regras de negócio provisórias

- Melhor tentativa válida por teste · “estável” = variação < 2% · reavaliação vence em 90 dias.
- Presença = presentes ÷ (presentes + faltas) · “hoje” no fuso de São Paulo.
- **PKZ:** atributos de 0 a 99 vs. atletas da mesma idade e sexo; nível por letra (E ≤ 20 · D 21–40 · C 41–60 · B 61–80 · A > 80).
- **One to One:** tonelagem, PSE (0–10), RIR, 1RM estimado por Epley, carga aguda/crônica (faixa segura 0,8–1,3), assimetria (limite 10%).
- Percentis por grupo **adiados** — faltam sexo e modalidade no cadastro.

---

## Equipes e estrutura do repositório

Cada grupo trabalha na sua branch e nas suas pastas. Hoje as pastas estão vazias; o código entra conforme as tasks do ClickUp forem executadas.

| Grupo | Branch | Pastas | Membros | Escopo |
|---|---|---|---|---|
| **Desenvolvimento** | `backend` | [`backend/`](backend/) · [`relatorios/`](relatorios/) · [`frontend/`](frontend/) | Ewerton Arrais, Miguel Veiga, Gian¹, Henrique, Christian, Rafael¹ | Desenvolver a aplicação, a área de tratamento de dados e a API que será consumida; automatizar a geração e o envio dos relatórios por e-mail |
| **Dados** | `dados` | [`dados/`](dados/) | Micael, Rafael¹, Iago | Consumir os dados tratados pelo back-end e estruturar o banco próprio |
| **QA** | `qa` | [`qa/`](qa/) | Roger, Gian¹, Mariana | Testar a qualidade do projeto e a usabilidade |
| **Documentação** | `documentacao` | [`docs/`](docs/) | Gabriel Melo, Gabriel Lima | Comunicar com as áreas e manter a documentação profissional e visualmente agradável até a entrega final, com algumas entregas semanais |
| **Gerência** | — | — | Lucas e Pedro | Coordenação, interlocução com o cliente e revisão de PRs |

¹ Rafael e Gian participam de dois grupos.

**Contrato entre grupos:** as views do schema `api` são o contrato entre Desenvolvimento, Dados e QA. Mudança em view = PR revisado pelos três grupos.

---

## Status e cronograma

- **Kickoff:** 26/08/2026 · **Fase atual:** Fase 1 — Fundação
- `ENT-001` Modelo de dados documentado — primeira versão completa, **aguardando homologação (marco M2)**
- `ENT-002` Base reestruturada — não iniciado, por decisão, até o M2 (pré-requisito das Fases 3 a 5)

| Frente | Situação |
|---|---|
| Modelagem & Banco | Diagnóstico concluído · proposta de modelo a validar |
| Back-end | Validado localmente (PostgreSQL 16, dados sintéticos) · implantação pendente |
| Relatórios | Layouts definidos · implementação planejada |
| Front-end | Comparativo e protótipo concluídos · validação com o cliente |

### Plano de produção (autorizado)

As tasks estão no **ClickUp**. A meta é produzir **~33% do projeto por semana** e fechar com **duas semanas de margem antes da P2**, reservadas para integração entre os grupos e correção de erros.

**Prazo: todas as tasks concluídas até 04/11.**

| Período | Meta | Foco |
|---|---|---|
| Semana 1 | 33% | Banco e back-end implantados; carga rodando na cópia; contrato das views fechado |
| Semana 2 | 66% | Templates de relatório consumindo a API; telas e painel ligados aos dados reais |
| Semana 3 | 100% | Os 6 relatórios gerados em PDF; dashboards; envio por e-mail |
| Semanas 4–5 | Margem | **Integração, testes ponta a ponta e correções** — sem features novas |
| — | **P2** | Entrega |

> As datas exatas de cada semana seguem o ClickUp.

### Decisões em aberto (gerência)

1. Plataforma do dashboard (Power BI, aplicação própria ou extensão do app) — muda o modelo dimensional.
2. Quem opera o envio automático por e-mail (disparo e provedor).
3. Relação entre o pipeline de extração (Python) e a camada analítica no mesmo banco (FDW + SQL).
4. Verificação de segurança da produção com o back-end do cliente.

Decisões já tomadas: **AQ-002** evoluir o app em fases (sem migração de uma vez) · **AQ-001** unidade vira entidade própria no banco.

---

## Como contribuir

```
main            ← protegida: só entra por Pull Request aprovado
├── backend     ← branch do grupo
│   └── backend/CU-86abc-views-api   ← branch da task (opcional)
├── dados
├── qa
└── documentacao
```

1. Trabalhe na branch do seu grupo (`backend`, `dados`, `qa` ou `documentacao`). Para tasks maiores, crie uma branch a partir dela com o ID do ClickUp: `grupo/CU-<id>-descricao-curta`.
2. Commits pequenos e descritivos, em português.
3. Para levar à `main`, abra um **Pull Request** da branch do grupo para a `main`. Ele precisa de **1 aprovação** de outra pessoa. Se mexer em views da `api`, peça revisão também de Dados e QA.
4. Antes de abrir o PR, traga a `main` para a sua branch (`git pull origin main`) e resolva os conflitos.
5. Ninguém faz push direto na `main`.

## Regras do repositório

- **Nunca** versionar credenciais (`.env`, chaves do Supabase, service role). Use `.env.example` com valores vazios.
- **Nunca** versionar dados da produção ou da cópia: CPF, nomes, fotos, dados de saúde, dumps, CSVs. Para testes, use dados sintéticos.
- Os layouts com atleta real (Anexo A da documentação) **não** entram aqui — só versões com dados fictícios.
- A documentação geral (`DOC-PKZ-OTO-001`) é confidencial e fica na pasta compartilhada da equipe; em `docs/` vão apenas resumos, decisões e diagramas sem dados do cliente.
- Achados de segurança do banco do cliente são tratados só nos canais internos — nunca em issues, PRs ou commits.
