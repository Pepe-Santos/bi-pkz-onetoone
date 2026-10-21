# Convenções do banco e da carga

Valem para todo o grupo. Mudança aqui é combinada com os três antes de entrar no repositório.
Status: **proposta do Micael (12/10)**, atualizada em 15/10. Decisões tomadas desde então estão em [PENDENCIAS.md](PENDENCIAS.md) (seção Decididas).

> **Mudança de 12/10:** os scripts leem de `origem.` e não mais de `public.`. Quem já tem rascunho com `public.` troca por `origem.` (só o prefixo; tabelas e colunas são as mesmas).

## 1. Nomes

- Português, `snake_case`, sem acento: `avaliacao_medida`, `data_nascimento`.
- Tabela no singular: `aluno`, `avaliacao`, `arquivo`.
- Chave estrangeira: `<tabela>_id` (`aluno_id`, `unidade_id`). Exceção quando o papel importa mais que a tabela: `avaliador_id`, `enviado_por`.
- Schema do destino: `novo` (provisório até o nome definitivo do projeto separado).
- Schema de leitura: **`origem`** — a foto congelada das tabelas do app (ver [README](README.md#o-ensaio)). Os scripts leem **só** de `origem.<tabela>`, **nunca** de `public.<tabela>`. Os nomes de tabela e coluna são os mesmos de `public`.
- Valores de catálogo em texto minúsculo, sem acento: `teste_fisico`, `consolidada`, `dir`, `esq`.

## 2. Chaves

- Chave primária em `uuid`.
- **Reaproveitar o UUID de origem** quando a entidade nova corresponde direto a uma antiga:
  `aluno.id = athletes.id`, `avaliacao.id = physical_test_sessions.id`.
- Quando a entidade nasce de uma divisão ou agrupamento (ex.: um `arquivo` por caminho, vindo de 9 colunas diferentes), a chave de reexecução é uma coluna `id_origem` ou uma combinação única declarada no DDL (`unique (...)`).
- **`profissional.id` = `profiles.id`** (o ID do usuário de login; decidido em 13/10, ver PENDENCIAS.md). Assim `evaluator_id`, `physio_id`, `professional_id`, `actor_id`, `uploaded_by` e `professor_id` da origem viram chave estrangeira direto, sem tabela de tradução. Ids de usuário que não são profissional (`created_by`, `actor_id`) apontam para `perfil_usuario.usuario_id`, que também é o `profiles.id`.

## 3. Colunas padrão

| Coluna | Onde | Regra |
|---|---|---|
| `criado_em timestamptz not null default now()` | todas as tabelas de negócio | Na carga, recebe o `created_at` da origem quando existir. |
| `atualizado_em timestamptz not null default now()` | todas as tabelas de negócio | O `on conflict do update` grava `now()`. |
| `pendencia text` | tabelas onde um registro pode entrar com dúvida | Nunca bloqueia a carga. Várias pendências separadas por `; `. Use `novo.juntar_pendencia(pendencia, '...')`. |

## 4. Regras de todo script de carga

Modelo pronto em [`carga/_modelo.sql`](carga/_modelo.sql).

1. `\set ON_ERROR_STOP on`, depois `begin` … `commit`: tudo ou nada.
2. Logo depois do `begin`: `select set_config('novo.modo_carga', 'on', true);`
3. Rejeitados entram com `on conflict (script, tabela_origem, id_origem, motivo) do nothing` (chave única da 010): rodar de novo não duplica. **Não use `delete` nem `drop`** nos scripts: o conector do Supabase trava esperando uma confirmação que não aparece no app (15/10).
4. Registra rejeitados **antes** de carregar, um `insert` por regra, com motivo legível.
5. Carrega com `insert ... select ... on conflict (...) do update` (ou `do nothing` quando não há o que atualizar). Rodar duas vezes não duplica.
6. Marca pendências com `update ... set pendencia = novo.juntar_pendencia(...)`.
7. Termina gravando em `novo.carga_execucao`. `linhas_carregadas` = **total** no destino do domínio, para que a segunda execução dê o mesmo número.
8. Lê de `origem`, grava em `novo`. Nunca lê nem grava em `public` (é o app vivo). Nunca roda na produção.
9. Dúvida de regra de negócio não é decidida no script: o registro entra com `pendencia` e a dúvida vai para a lista de pendências do grupo.

**Rejeitar ou marcar pendência?**

| Situação | O que fazer |
|---|---|
| Não dá para gravar sem quebrar o banco (aponta para aluno inexistente, chave duplicada, campo obrigatório vazio) | `carga_rejeitado` |
| Dá para gravar, mas há dúvida de regra (unidade de medida, formato antigo, valor fora da faixa) | Grava, com `pendencia` |
| Dado que decidimos não migrar (ex.: `student_tests` sem resultado) | Não entra; a decisão fica registrada no mapeamento e no `observacao` da execução |

## 5. Nome do script na tabela de registro

Desde 13/10, a construção (DDL e todos os scripts) é da Frente 1 (Micael); a Frente 2 (Rafael) revisa e confere; a Frente 3 (Iago) cuida de acesso e consumo.

O campo `script` de `carga_execucao` e `carga_rejeitado` é o **nome do domínio**, sem número:

| Ordem | Arquivo | `script` |
|---|---|---|
| 10 | `carga/10_carga_referencia.sql` | `referencia` |
| 20 | `carga/20_carga_cadastro.sql` | `cadastro` |
| 30 | `carga/30_carga_comercial.sql` | `comercial` |
| 40 | `carga/40_carga_agenda.sql` | `agenda` |
| 50 | `carga/50_carga_relatorio.sql` | `relatorio` |
| 60 | `carga/60_carga_avaliacao.sql` | `avaliacao` |
| 70 | `carga/70_carga_atendimento.sql` | `atendimento` |
| 80 | `carga/80_carga_documentos_auditoria.sql` | `documentos` |
| 99 | `carga/99_carga_mestre.sql` | — |

A ordem importa: cada script só referencia o que os anteriores já carregaram.

## 6. Triggers

- Triggers de regra de negócio (ex.: avaliação `consolidada` não pode ser alterada) consultam `novo.em_modo_carga()` e deixam a carga passar.
- `novo.em_modo_carga()` só é verdadeiro quando a transação ligou o modo **e** o usuário é membro do papel `postgres` (quem roda a carga). Outro usuário que ligue o parâmetro não ganha nada (009).
- Toda função nova em `novo` usa nomes qualificados (`novo.tabela`) e é criada com `set search_path = ''` (ou entra no laço do fim da 009). O advisor do Supabase acusa função sem `search_path` fixo.
- Ninguém desliga trigger com `alter table ... disable trigger` nem `session_replication_role`: isso também desliga as chaves estrangeiras.

## 7. Segurança

- RLS ligado em **toda** tabela nova, no mesmo arquivo que a cria (`alter table ... enable row level security`). As políticas por papel vêm depois; até lá, nada fica aberto pela API.
- Dado clínico (anamnese, fisioterapia, arquivos de fisio) fica em tabela própria ou com coluna `confidencialidade`, para a política de acesso poder separar.
  - **Exceção decidida em 15/10:** as medidas de fisioterapia ficam em `avaliacao`/`avaliacao_medida` (`tipo = 'fisioterapia'`) e os atendimentos de fisio, nutrição e psicologia em `atendimento`, sem coluna `confidencialidade`. O próprio dado já diz que é clínico: a política de acesso (Frente 3) filtra por `avaliacao.tipo` e `atendimento.servico_id`. `anamnese` (restrito) e `arquivo` (normal/clínico/restrito) seguem a regra.
- Fora do Git: dados (CSV, dumps, planilhas com dados), `.env`, chaves, senhas, strings de conexão.
- Nenhum dado pessoal em commit, comentário, exemplo, issue ou mensagem: CPF, e-mail, telefone, endereço, nome de aluno, nome de arquivo de aluno. Use contagens e exemplos inventados.

## 8. Migrations (DDL)

- Um arquivo por domínio em `migrations/`, numerado: `001_infra_carga.sql`, `002_fundacao.sql`, `0xx_<dominio>.sql`.
- Migration já aplicada no ensaio **não é editada**: mudança vira um arquivo novo (`0yy_ajuste_<o_que>.sql`). Exceção: antes do primeiro ensaio geral, ajustes podem ir no próprio arquivo, avisando o grupo.
- Toda chave estrangeira ganha índice.

## 9. Git

- Branch por tarefa (`micael/60-avaliacao`), pull request para `main`, revisão de outra pessoa do grupo antes de juntar.
- Mensagem de commit em português, no imperativo: `Adiciona carga de avaliação física`.
