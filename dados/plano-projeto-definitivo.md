# Plano do projeto definitivo (tarefa 3.6)

> Frente 3 · Iago · 23/10/2026 · **proposta, aguardando aprovação do grupo**.
>
> Fecha a tarefa 3.6 e dá o encaminhamento da pendência 7 (nome do schema definitivo e quem cria o
> projeto). O que está decidido vem de [PENDENCIAS.md](migracoes/PENDENCIAS.md); o que falta decidir
> está na seção 1, com a recomendação desta frente.

## Onde estamos

Hoje tudo roda no **projeto de ensaio**, que é a cópia descaracterizada do banco de produção mantida
pelo Dev Lucas. Nele:

| Schema | O que é |
|---|---|
| `public` | o app em uso, que continua mudando (rotinas automáticas às 00:00 e 00:15) |
| `origem` | foto congelada das 28 tabelas, de 12/10 |
| `novo` | o banco construído: 43 tabelas, 5 views, 12 migrations (a 012 é a das políticas de acesso, aplicada em 26/10) |

A decisão de 12/10 é que o destino definitivo é **um projeto Supabase separado do app**. Lá o arranjo é o
mesmo, então os scripts rodam sem mudança: é por isso que a virada é um roteiro, e não uma reescrita.

## 1. O que falta decidir (pendência 7)

| # | Decisão | Opções | Recomendação da Frente 3 |
|---|---|---|---|
| 7.1 | **Nome do schema definitivo** | manter `novo`; ou `core`; ou `pkz` | **Manter `novo`.** Trocar o nome obriga a mexer em 12 migrations (inclusive a política 012), 8 cargas e 5 conferências. O nome não aparece para quem consome: o consumo é pelo schema `api` |
| 7.2 | **Quem cria o projeto** | gerência (Pedro/Lucas); o cliente; o Dev Lucas | **A gerência**, numa conta do projeto e não numa conta pessoal. Hoje o ensaio depende da conta do Dev Lucas |
| 7.3 | **Quem administra** | uma pessoa; a gerência + a Frente 1 | **Dois donos**, para ninguém ficar bloqueado. Papel de administrador só para esses dois |
| 7.4 | **Plano do Supabase** | gratuito; pago | **Precisa de resposta antes da virada.** O gratuito pausa projeto sem uso e não tem backup automático — e o banco definitivo guarda dado real de 105 menores |
| 7.5 | **O que acontece com `origem` depois** | apagar; guardar | **Guardar até a conferência da carga definitiva ser aprovada, e só então apagar.** A contagem fica preservada em `carga_gabarito`, que não se apaga |

## 2. Passo a passo da virada

Cada passo diz quem executa e o que tem de dar certo antes de seguir. Nada aqui roda na produção do
cliente: o único contato com ela é o dump do passo 1, que é leitura.

### Passo 1 — Dump congelado da produção
**Quem:** Back-end do cliente, com a gerência · **Depende de:** 7.2 e 7.4 resolvidos

Pedir ao cliente um dump da produção e restaurá-lo em `public` no projeto novo. O dump precisa ter
**data e hora anotadas**: a produção muda todo dia por rotina automática, então a foto só faz sentido
com o instante registrado.

**Conferir:** as 28 tabelas chegaram e a contagem de cada uma bate com o que o cliente informou.

### Passo 2 — Congelar a origem
**Quem:** Frente 1 · **Arquivo:** `migracoes/ensaio/congelar_origem.sql`

Aplicar antes a `001_infra_carga.sql`, depois rodar o congelamento. Ele cria `origem` com a cópia das 28
tabelas, liga RLS, tira acesso de `anon` e `authenticated` e registra o gabarito com o rótulo
`congelamento-AAAA-MM-DD` da data do dump.

**Conferir:** `novo.carga_gabarito` tem as 28 tabelas com o rótulo novo, e `origem` não está exposta na
API.

### Passo 3 — Migrations
**Quem:** Frente 1 · **Arquivos:** `migrations/001` a `012`, em ordem

A 012 é a das políticas de acesso. Ela entra aqui, junto das outras, e não depois: tabela nova nasce
fechada, e assim a política nasce com ela.

**Conferir:** `conferencia/00_estrutura_ddl.sql` com as quatro primeiras consultas vazias.

### Passo 4 — Carga
**Quem:** Frente 1 · **Arquivo:** `carga/99_carga_mestre.sql`, de dentro de `dados/migracoes`

Rodar o mestre, conferir que a conferência do fim deu `ok` em todas as linhas, e **rodar de novo**:
nenhuma contagem pode mudar. É o mesmo ensaio geral do item "Rodar" do
[README](migracoes/README.md), agora no projeto definitivo.

**Conferir:** `conferencia/99_conferencia_geral.sql` sem divergência e `novo.carga_rejeitado` vazia.

### Passo 5 — Conferência independente
**Quem:** Frente 2 · **Arquivos:** `conferencia/` (preflight e destino)

Repetir o preflight e as conferências de destino, como no relatório final da Frente 2. Os números
esperados mudam, porque a foto é outra: o gabarito do passo 2 é a nova referência.

**Conferir:** nenhum inconclusivo sem tratamento e nenhuma divergência sem explicação.

### Passo 6 — Acesso e consumo
**Quem:** Frente 3

1. Conferir que as políticas da 012 estão valendo, com o teste por papel (um `select` por papel,
   comparando o que aparece).
2. Criar o schema `api` e publicar as views de consumo.
3. Expor **somente** o `api` em Project Settings → Data API → Exposed schemas. `novo` e `origem` ficam
   de fora.
4. Conferir que `anon` não lê nada e que `authenticated` só vê o que a matriz permite.

**Conferir:** a chamada de uma view com o cabeçalho `Accept-Profile: api` responde, e a mesma chamada
sem login não responde.

### Passo 7 — Virada do consumo
**Quem:** Desenvolvimento, avisando o grupo

Apontar o back-end e os relatórios para o projeto novo. A partir daqui, o projeto de ensaio deixa de ser
a fonte.

### Passo 8 — Encerrar o ensaio
**Quem:** gerência · **Depende de:** 7.5

Com a conferência do passo 5 aprovada, apagar `origem` no projeto definitivo (se for essa a decisão) e
encerrar o uso do projeto de ensaio. O schema `novo_pre_ensaio_geral` e as tabelas `avulsa_*`, que
ficaram da construção, também saem — o grupo já tinha pendente autorizar isso.

## 3. O que pode dar errado

| Risco | Efeito | O que reduz |
|---|---|---|
| Dump da produção demora a vir | Tudo para no passo 1 | Pedir agora, antes de os outros passos ficarem prontos |
| Dump chega com estrutura diferente da foto de 12/10 | Mapeamento e carga quebram | Rodar `conferencia/01_cobertura_mapeamento.py` logo depois do passo 2: ele acusa coluna nova ou que sumiu |
| Projeto no plano gratuito | Sem backup automático e pausa por inatividade | Decisão 7.4 antes da virada |
| Políticas aplicadas depois do consumo | Janela com dado aberto | A 012 entra no passo 3, junto das migrations |
| `api` exposto antes das políticas | Dado legível sem filtro | Passo 6 na ordem: política, depois view, depois exposição |
| Produção continua mudando depois do dump | O banco novo nasce desatualizado | Recarga com foto nova, combinada no grupo; os scripts não duplicam |

## 4. Pronto quando

- As cinco decisões da seção 1 respondidas e anotadas em [PENDENCIAS.md](migracoes/PENDENCIAS.md), com
  quem decidiu e quando.
- Este passo a passo aprovado pelo grupo.
- Os passos 1 a 6 executados, cada um com a sua conferência.
