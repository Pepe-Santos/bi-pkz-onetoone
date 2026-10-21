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

### Como refazer a conferência (reproduzível)

`conferencia/01_cobertura_mapeamento.py` lê as colunas reais do banco no `information_schema` e compara com estes CSVs. Só lê; sai com código 1 se achar erro. Precisa de Python 3 (só biblioteca padrão) e do `psql`, ou de um CSV exportado do `information_schema` (instruções no cabeçalho do script).

```powershell
cd dados/migracoes
python conferencia/01_cobertura_mapeamento.py --detalhe cobertura.csv
```

Classes usadas (a regra exata está no cabeçalho do script):

| Lado | Classe | Quando |
|---|---|---|
| origem | `direta` | citada só em linhas cuja transformação começa com "direto" |
| origem | `transformada` | citada em pelo menos uma linha com outra transformação |
| origem | `nao_migrada` | citada só em decisões de não migrar (`tabela_destino` = `—`) |
| destino | `direta` | todas as linhas dela começam com "direto" |
| destino | `transformada` | alguma linha tem origem e outra transformação |
| destino | `gerada` | nenhuma linha tem origem: calculada na carga (id novo, `now()`, pendência...) |

Resultado na estrutura do ensaio (21/10; a estrutura local de teste é idêntica, conferido por hash das listas de colunas):

| Lado | Colunas | direta | transformada | não migrada | gerada | erros |
|---|---|---|---|---|---|---|
| origem (28 tabelas) | 365 | 153 | 128 | 84 | — | 0 |
| destino (40 tabelas, sem `carga_*`) | 451 | 172 | 96 | — | 183 | 0 |

`--detalhe` grava a classe de cada coluna num CSV, para conferir uma a uma.

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

## Papéis e unidade (`papel_usuario.unidade_id`)

`unidade_id` nula quer dizer **o papel vale para todas as unidades**. Ela só é preenchida quando o próprio papel da origem diz a unidade: no app, só `professor_pkz` e `professor_one_to_one` carregam unidade. Nenhum outro papel da origem tem informação de unidade, então a carga não inventa uma.

| Papel novo | Papel na origem | Unidade | Por quê | No ensaio |
|---|---|---|---|---|
| `professor` | `professor_pkz` | PKZ | o papel diz a unidade | 8 |
| `professor` | `professor_one_to_one` | One to One | o papel diz a unidade | 10 |
| `professor` | `professor` (sem sufixo) | todas | a origem não diz a unidade (pendência 15) | 1 |
| `especialista` | `fisioterapeuta`, `nutricionista`, `psicologo` | todas | a agenda de fisio, nutri e psico é compartilhada entre as unidades (migration 009) | 7 |
| `admin` | `admin` | todas | administra o app inteiro | 8 |
| `responsavel` | `responsavel` | todas | a unidade vem da matrícula do aluno, não do papel | 116 |
| `recepcao` | `recepcao` | todas | papel sem destino definido (pendência na carga) | 3 |
| | | | **total** | **153** (135 globais, 18 por unidade) |

No conceitual, isso é o relacionamento "atua em": ele é opcional para o papel. No lógico, escolhemos guardar "todas as unidades" como nulo, em vez de repetir a linha uma vez por unidade. A chave única é `(usuario_id, papel_id, unidade_id)` com `nulls not distinct`, então não existe papel global duplicado. Quem precisar de uma linha por unidade faz `join novo.unidade u on u.id = pu.unidade_id or pu.unidade_id is null`.

Conferência: `conferencia/02_papel_unidade.sql` (distribuição e violações da regra; a consulta 3 tem que voltar vazia).

## Saldo de créditos: as duas conferências

Há duas conferências de saldo no projeto, e elas **não medem a mesma coisa**. Os números de uma não confirmam nem contradizem os da outra sem a ponte abaixo.

| | A — carga 30 + migration 011 (Frente 1) | B — conferência 5 da tarefa 2.1 (Frente 2) |
|---|---|---|
| Universo | todo par (aluno, serviço): 106 alunos × 3 saldos = **318 pares** | só pares (atleta, serviço) com uma renovação cujo texto identifica o serviço: **196 pares** |
| Serviço de cada lançamento | o colchete `[treino]`/`[fisio]`/`[nutri]` diz de qual saldo saiu; sem colchete, pelo texto; renovação genérica ("Renovação mensal (10/2026)") = treino | pelo texto, fisio > nutri > treino/PKZ, sem olhar o colchete; renovação genérica fica de fora |
| Ponto de partida | a última renovação do serviço, **somando o delta dela**, que é a cota do plano | **10** fixo, mais os lançamentos depois da última renovação |
| Sem renovação | soma do extrato inteiro | o par não entra |
| Resultado na foto de 12/10 | 3 pares divergentes (3 alunos: 2 em fisio, 1 em nutri) | 195 de 196 divergentes |

**A ponte** (`conferencia/03_saldo_credito.sql` calcula tudo sobre a mesma foto):

| Recorte | Pares | Divergentes pelo critério A | Partindo de 10 | Partindo da cota da renovação |
|---|---|---|---|---|
| Universo B | 196 | 0 | 195 | 0 |
| Universo A fora de B | 122 | 3 | — | — |
| Universo A inteiro | 318 | 3 | — | — |

Como ler:

- **Dentro do universo B, os dois critérios concordam** quando o ponto de partida é a cota da renovação: 0 divergências. As 195 divergências vêm só do "reinicia em 10": a cota varia por plano (1 a 20 créditos) e só 5 das renovações da foto têm cota 10. O app grava a cota no `delta` da renovação, e é essa cota que vale.
- **As 3 divergências do critério A estão todas fora do universo B**: são pares sem renovação identificável pelo texto, em que o saldo é a soma do extrato. É a pendência 13.
- Os resultados da A são contados por par (aluno, serviço). "3 alunos" e "3 pares" coincidem só porque cada aluno divergente diverge em um serviço.

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
