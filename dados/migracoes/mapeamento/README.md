# Mapeamento de/para (tarefa 1.3)

Especificação dos scripts de carga: para cada coluna do destino (`novo`), de onde ela vem em `origem`, como é transformada e quando o registro entra com pendência ou é rejeitado. Feito em 14/10/2026 sobre a foto de 12/10.

**Nenhum arquivo daqui tem dado da origem.** Só estrutura, regras e contagens.

**Pré-requisito:** as migrations **009**, **010** e **011** aplicadas. Os scripts 10 (colunas de créditos padrão) e 40 (grade compartilhada, `intervalo_min`, `novo.grade_do_horario`) não funcionam sem a 009; a conferência de saldo do 30 usa a regra da 011.

Revisado em 15/10 por dois revisores independentes; as correções estão no fim deste arquivo.

## Arquivos

Um CSV por script de carga. Os 8 cobrem os 6 domínios do modelo conceitual:

| Arquivo | Script | Tabelas de destino |
|---|---|---|
| `referencia.csv` | 10 | unidade, servico, configuracao_unidade, plano, plano_beneficio, papel |
| `cadastro.csv` | 20 | pessoa, perfil_usuario, papel_usuario, aluno, aluno_servico, responsavel_aluno, profissional, profissional_servico |
| `comercial.csv` | 30 | matricula, renovacao, credito_lancamento |
| `agenda.csv` | 40 | horario_grade, bloqueio_agenda, bloqueio_grade, agendamento, sessao_treino, lista_espera, feedback_treino |
| `relatorio.csv` | 50 | catalogo_item, relatorio_treino, relatorio_item |
| `avaliacao.csv` | 60 | metrica, avaliacao e avaliacao_medida (teste físico e semanal) |
| `atendimento.csv` | 70 | avaliacao e avaliacao_medida (fisioterapia), anamnese, atendimento, evolucao |
| `documentos.csv` | 80 | arquivo, evento_auditoria + tabelas só com estrutura |
| `avaliacao_metricas.csv` | 60 | catálogo das 109 métricas (código, unidade, direção, lado, origem, pendência) |

## Colunas

| Coluna | O que é |
|---|---|
| `tabela_destino`, `coluna` | coluna em `novo`. `—` = decisão de **não migrar** a coluna da origem |
| `tipo` | tipo no DDL |
| `origem` | `origem.tabela.coluna`; várias separadas por `\|` (depois da primeira, `\| coluna` é da mesma tabela). Vazio = gerado na carga |
| `transformacao` | como o valor é calculado |
| `regra_pendencia_ou_rejeicao` | texto da pendência gravada, ou `carga_rejeitado` quando não dá para gravar |

## Conferência feita

- As 451 colunas das tabelas de `novo` (002 a 009) têm pelo menos uma linha aqui.
- As 365 colunas das 28 tabelas de `origem` aparecem como origem de alguma coluna ou numa decisão de não migrar, com motivo.
- Toda coluna citada existe.

## O que a origem mostrou (e muda a carga)

1. **Admins atuando como profissional.** 46 agendamentos, 62 relatórios, 2 testes físicos e 2 avaliações de fisio têm como professor ou avaliador um usuário só com papel `admin`. Para a FK não quebrar, eles entram em `profissional`, com pendência (nova pendência 10).
2. **Crédito: o colchete é o saldo, não o serviço.** Em `reason`, `[treino]`/`[fisio]`/`[nutri]` dizem de qual saldo o crédito saiu. Há casos como "Solicitação: fisioterapeuta [treino]" (psicologia também desconta de treino). O lançamento fica no saldo do colchete, com pendência.
3. **Bloqueios usam a numeração ISO.** Em `schedule_blocks.weekday`, 1 = segunda e 7 = domingo; o destino usa `dow`, onde 0 = domingo (conversão: `% 7`). `weekday` nulo em bloqueio permanente = vale todos os dias.
4. **A capacidade do app conta pela duração.** Um horário está ocupado por quem começou antes e ainda não terminou. Fisio, nutri e psico têm capacidade 1, **compartilhada entre as duas unidades**. Treino tem capacidade 6, e 10 no sábado às 08:00. Isso levou à migration 009.
5. **Duração do agendamento** (para `hora_fim`): treino One to One a partir das 17h = 60 min; plano express = 30 min; treino = `training_duration_min`; fisio = 15 min (60 min no be_the_one); nutri e psico = 60 min.
6. **`pkz_data` da fisio:** o sufixo final `_dir` das chaves `post_*` significa **direção do desvio** (Anterior, Interna...), não "direito". O lado vem do nome do campo (`tibia_dir_valor`, `tibia_dir_dir`). Ali também ficam 8 caminhos de arquivo (fotos posturais e carimbo), que vão para `arquivo`.
7. **Auditoria com dado pessoal:** alguns tipos de evento trazem dado pessoal no `payload`. As chaves `athlete_name`, `phone`, `full_name` e `username` são removidas na carga (pendência 11, para a Frente 3 confirmar).
8. **Duas colunas novas** em `app_settings` (`credits_fisio_standard`, `credits_nutri_standard`) entraram depois do backup de 26/08. O arquivo `ensaio/origem_estrutura_local.sql` foi atualizado.
9. **Coisas que simplificam:** nenhum responsável secundário na foto; catálogo de materiais e tecnologias 100% casado (só 5 textos livres em `materials_other`); nenhum caminho de arquivo ligado a dois alunos (523 caminhos distintos); `file_path` e `pdf_storage_path` dos relatórios são o mesmo caminho em 205 de 205.
10. **Dois alunos One to One sem plano.** Eles entram no plano `one_to_one_sem_plano`, com pendência. Sem esse plano ficariam sem matrícula e, portanto, sem unidade.
11. **Créditos não são cumulativos** (achado na carga de 15/10). A renovação redefine o saldo: o lançamento de renovação traz `delta = cota`, não a diferença. O saldo é a soma desde a última renovação do serviço (migration 011); somar o extrato inteiro inflava o saldo.

## Migration 009

`migrations/009_ajuste_mapeamento.sql` (o cabeçalho lista tudo). O que mexe na carga:

- `configuracao_unidade` + `creditos_fisio_padrao`, `creditos_nutri_padrao`;
- `horario_grade.unidade_id` aceita nulo (grade compartilhada), chave única `nulls not distinct`, e `intervalo_min` (15, 30 ou 60);
- capacidade conferida no intervalo inteiro do agendamento (decisão de 15/10); serviço especializado sem grade = 1 compartilhada;
- `renovacao`: chave (aluno, serviço, periodicidade, competência) e periodicidade obrigatória;
- a matrícula só aceita plano da mesma unidade.

Ela tem `drop constraint`, então o conector do Supabase pede confirmação ao aplicar.

## Diferenças em relação ao handoff de 13/10

- Agenda: não existe tabela `sessao` para agrupar, e a regra do "professor mais frequente" deixa de existir. O profissional vem de cada agendamento. `sessao_treino` só para treino com presença.
- Arquivo: não existe `arquivo_vinculo`. As ligações são FKs (`relatorio_id`, `avaliacao_id`, `atendimento_id`).
- Métricas de fisioterapia: além das 14 de goniometria e do Appley, entram as de força, relação, mobilidade e postura do `pkz_data` (109 métricas no total).

## Correções da revisão de 15/10

| Onde | O que mudou |
|---|---|
| avaliacao.csv | altura e peso nulos não geram linha (quebraria o CHECK de `avaliacao_medida`); single/cross hop e distância do VO2 abaixo de 10 entram com pendência (limiar provisório) |
| relatorio.csv | material e tecnologia vêm só das tabelas de catálogo; os arrays só criam itens nos outros 6 domínios (evita linha duplicada no mesmo `on conflict`). Texto livre de `*_other` vira um item `outro_<slug>` por texto, com pendência 'não classificado': assim a coordenação reclassifica item a item, em vez de um "não classificado" único que misturaria tudo |
| documentos.csv | `username` também sai do payload; `assign_booking_professor` padronizado como `assign_professor`; unidade do evento de agendamento vem de `novo.agendamento`; `img_mob_*` = `imagem_mobilidade` |
| cadastro.csv | admin que atua como profissional ganha serviço também pelos relatórios, testes físicos e avaliações de fisio |
| comercial.csv | chave da renovação com periodicidade; '(N/N)' = competência MM/AAAA (bate em 173/173) |
| agenda.csv | sábado 08:00 com capacidade 10 só no início das 08:00 (One to One: faixa 08:00–08:30); profissional do agendamento de especialista vem da evolução quando falta (15); bloqueio com data nula é rejeitado (a coluna passou a aceitar nulo) |
| atendimento.csv | Appley 'Não avaliado' não gera medida |
| referencia.csv | `renovacao_dia_semana` convertido para `dow` (igual à grade e ao bloqueio) |

## Ajustes da implementação dos scripts 60–80 (16/10)

| Onde | O que mudou |
|---|---|
| avaliacao.csv, atendimento.csv | chave do `data` ou do `pkz_data` sem métrica no catálogo vai para `carga_rejeitado` com o nome da chave (0 na foto); avaliador sem profissional no destino fica nulo, com pendência (0 na foto) |
| documentos.csv | aluno inexistente também rejeita o caminho; o rejeitado guarda `md5(caminho)` como id, não o caminho; dono (relatório, avaliação, atendimento) que não entrou no destino perde o vínculo, com pendência |
