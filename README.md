# Projeto BI — PKZ × One to One

Camada de dados e indicadores para as duas unidades do cliente, construída **sobre** o aplicativo operacional atual (feito no Lovable), sem alterá-lo.

| Unidade | Público | Relatório |
|---|---|---|
| **Playmakerz Lab (PKZ)** — Loja G | Treino funcional infantil (ex.: Sub 12, Sub 14/15; futebol e futsal) | Evolução nos testes físicos, para **pais e responsáveis** |
| **One to One Studio (OTO)** — Loja I | Personal para jovens adultos e adultos | Histórico de treinos, carga e progressão, para o **aluno** |

> **Repositório privado**, de uso exclusivo da equipe do projeto. Mesmo assim, credenciais, dados pessoais do cliente e a documentação confidencial ficam fora — veja [Regras do repositório](#regras-do-repositório) antes do primeiro commit.

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
        │  foto congelada da origem                         ┐
        ▼                                                   │
origem            cópia congelada das tabelas do app        │ grupo de Dados
        │  carga + conferência origem × destino             │ (dados/migracoes/)
        ▼                                                   │
novo              banco reestruturado: 43 tabelas e 5 views ┘
        │  lido direto (o Desenvolvimento só lê)            ┐
        ▼                                                   │
trat              regras de tratamento: parâmetros,         │ grupo de Desenvolvimento
        │         catálogo de testes, medidas padronizadas  │ (backend/sql/)
        ▼                                                   │
api               views expostas pela API REST do Supabase  ┘
        │
        ▼
Consumidores      relatórios em PDF e envio por e-mail · telas e dashboards
```

- **Um projeto Supabase só.** Hoje é o projeto de ensaio do Lucas; o projeto definitivo vem depois (tarefa 3.6 do grupo de Dados) e os scripts dos dois grupos recriam tudo nele.
- **Quem escreve onde:** o grupo de Dados controla `origem` e `novo` pelo histórico de migrações do Supabase. O Desenvolvimento só cria objetos em `trat`, em `api` e no bucket privado `relatorios`, e nunca escreve em `origem`, `novo` ou `public`.
- **Carga:** script mestre com cargas por domínio; o que não passa nas regras vai para uma tabela de rejeitados, e a conferência compara origem e destino tabela a tabela. Detalhes em [`dados/migracoes/`](dados/migracoes/).
- **Leitura direta (combinado em 20/10):** as views do `trat` leem as tabelas do `novo` sem uma camada de views intermediária. Em troca, o grupo de Dados avisa antes de mudar a estrutura de uma tabela usada pelo Desenvolvimento.
- **Catálogo de testes:** os códigos da `novo.metrica` são o padrão. O `trat` guarda só o que falta lá (faixa plausível e conversão).
- **Views da API:** contrato em [`backend/docs/api.md`](backend/docs/api.md). Primeiro as de avaliação (`atleta`, `evolucao`, `comparacao`, `reavaliacao`); as de treino do One to One (`ultimo_treino`, `treino_mes`) vêm em seguida.

### Stack

| Camada | Tecnologia |
|---|---|
| Banco e transformação | PostgreSQL (Supabase) e SQL: migrações do Supabase no grupo de Dados, scripts idempotentes no Desenvolvimento |
| API | API REST automática do Supabase sobre o schema `api` |
| Arquivos | Supabase Storage, bucket privado `relatorios` para os PDFs |
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

Cada grupo trabalha na sua branch e nas suas pastas, e o código chega à `main` por Pull Request conforme as tasks do ClickUp são executadas.

| Grupo | Branch | Pastas | Membros | Escopo |
|---|---|---|---|---|
| **Desenvolvimento** | `backend` | [`backend/`](backend/) · [`relatorios/`](relatorios/) · [`frontend/`](frontend/) | Ewerton Arrais, Miguel Veiga, Gian¹, Henrique, Christian, Rafael¹ | Ler o banco novo e montar o tratamento (`trat`) e a API (`api`); desenvolver a aplicação; automatizar a geração e o envio dos relatórios por e-mail |
| **Dados** | `dados` | [`dados/`](dados/) | Micael, Rafael¹, Iago | Congelar a origem, estruturar o banco novo (`novo`), carregar os dados e conferir origem × destino |
| **QA** | `qa` | [`qa/`](qa/) | Roger, Gian¹, Mariana | Testar a qualidade do projeto e a usabilidade |
| **Documentação** | `documentacao` | [`docs/`](docs/) | Gabriel Melo, Gabriel Lima | Comunicar com as áreas e manter a documentação profissional e visualmente agradável até a entrega final, com algumas entregas semanais |
| **Gerência** | — | — | Lucas e Pedro | Coordenação, interlocução com o cliente e revisão de PRs |

¹ Rafael e Gian participam de dois grupos.

**Contratos entre grupos:**
- **Tabelas do `novo` usadas pelo Desenvolvimento** — mudança de estrutura é avisada antes pelo grupo de Dados.
- **Views do schema `api`** — contrato com relatórios, telas e QA. Mudança em view = PR revisado também por QA.

---

## Status e cronograma

- **Kickoff:** 26/08/2026 · **Fase atual:** Fase 1 — Fundação
- `ENT-001` Modelo de dados documentado — primeira versão completa, **aguardando homologação (marco M2)**
- `ENT-002` Base reestruturada — construída, carregada e conferida no ensaio (grupo de Dados); políticas de acesso aplicadas no ensaio em 26/10. A execução no projeto definitivo segue o plano da tarefa 3.6 (`dados/plano-projeto-definitivo.md`)

| Frente | Situação |
|---|---|
| Modelagem & Banco | Banco reestruturado no ensaio: 43 tabelas, carga conferida (19/19, 0 rejeitados) · políticas de acesso por papel aplicadas (migration 012) · projeto definitivo pendente (3.6) |
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
3. Verificação de segurança da produção com o back-end do cliente.

Decisões já tomadas:
- **AQ-002** evoluir o app em fases (sem migração de uma vez) · **AQ-001** unidade vira entidade própria no banco.
- **Pipeline (15/10 e 20/10):** o grupo de Dados carrega o banco novo e o Desenvolvimento lê direto dele, no mesmo projeto Supabase. A conexão remota por `postgres_fdw` e a extração em Python saíram do plano.

---

## Como contribuir

```
main                          ← só entra por Pull Request aprovado
├── backend                   ← branch do grupo
│   └── docs/leitura-direta-novo   ← branch da task (opcional)
├── dados
├── qa
└── documentacao
```

1. Trabalhe na branch do seu grupo (`backend`, `dados`, `qa` ou `documentacao`). Para tasks maiores, crie uma branch a partir dela no formato `<tipo>/<assunto>` — ex.: `feat/conferencias-origem`, `docs/leitura-direta-novo` — e cite o ID da task do ClickUp no PR. (O formato `backend/...` não funciona: o git não cria uma branch com esse prefixo enquanto existir a branch `backend`.)
2. Commits pequenos e descritivos, em português.
3. Para levar à `main`, abra um **Pull Request** para a `main`. Ele precisa de **1 aprovação** de outra pessoa. Se mexer em views da `api`, peça revisão também de QA.
4. Antes de abrir o PR, traga a `main` para a sua branch (`git pull origin main`) e resolva os conflitos.
5. Ninguém faz push direto na `main`. **Atenção:** no plano atual do GitHub, repositório privado não tem proteção de branch, então o GitHub não bloqueia o push — a regra vale pelo combinado da equipe.

## Regras do repositório

- **Nunca** versionar credenciais (`.env`, chaves do Supabase, service role). Use `.env.example` com valores vazios.
- **Nunca** versionar dados da produção ou da cópia: CPF, nomes, contatos, fotos, dados de saúde, dumps ou CSVs com registros. Para testes, use dados sintéticos.
- Pode entrar: estrutura (DDL, mapeamentos de coluna em CSV), contagens e IDs técnicos (UUID) usados em conferências.
- Os layouts com atleta real (Anexo A da documentação) **não** entram aqui — só versões com dados fictícios.
- A documentação geral (`DOC-PKZ-OTO-001`) é confidencial e fica na pasta compartilhada da equipe; em `docs/` vão apenas resumos, decisões e diagramas sem dados do cliente.
- Achados de segurança do banco do cliente são tratados só nos canais internos — nunca em issues, PRs ou commits.
