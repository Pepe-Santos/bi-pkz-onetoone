# QA: tratamento das medidas, PDF do PKZ e envio por e-mail

**Responsável:** Mariana · **Data:** 02/11/2026 · **Tasks:** Testar o tratamento das medidas da API · Testar o relatório PKZ em PDF · Testar o envio dos relatórios por e-mail

**Código testado**
- branch `backend`: scripts `01`, `04`, `05`, `06`, `07` e `08` do `backend/sql`;
- PR #25 (gerador PKZ ligado à API) e PR #26 (envio só pela API e `09_api_envio_relatorio.sql`), ainda abertos, testados pela branch `feat/lote-sem-senha-banco`.

**Como foi testado.** Num PostgreSQL 16 local, com uma cópia mínima do Supabase (papéis `anon`, `authenticated` e `service_role`, `auth.jwt()` e RLS no `novo` como na 012) e as views de consumo copiadas da 014 do grupo de Dados. Todos os dados são sintéticos. O PDF e o e-mail rodaram de ponta a ponta com uma API local que imita a do Supabase e um SMTP falso, sem enviar nenhum e-mail. Para repetir, veja [Como rodar](#como-rodar).

**Resultado:** 57 casos automáticos no tratamento e na API, com 51 OK e 6 falhas. Essas 6 falhas vêm de 3 bugs. Mais 4 bugs foram achados no PDF e no envio.

---

## Bugs encontrados

| # | Gravidade | Onde | Bug | Grupo |
|---|---|---|---|---|
| 1 | **Alta** | `06_api_avaliacoes.sql` | Usuário logado na API recebe **0 atletas** em `api.atleta`, `api.evolucao`, `api.comparacao` e `api.reavaliacao` | Desenvolvimento + Dados |
| 2 | Média | PR #25, `gerar_pdf.py` | O PDF de um período mostra dados de **depois** do período | Desenvolvimento (Henrique) |
| 3 | Média | PR #25, `gerar_pdf.py` | Single hop e cross hop: o gráfico **mistura lado direito e esquerdo**, e a tabela repete o nome sem dizer o lado | Desenvolvimento (Henrique) |
| 4 | Média | `05_trat_medidas.sql` | Tempo na velocidade máxima maior que o tempo total do VO2 é aceito como válido | Desenvolvimento |
| 5 | Baixa | `06_api_avaliacoes.sql` | Variação de 1,95% a 1,99% sai como "melhorou/piorou" em vez de "estável" | Desenvolvimento |
| 6 | Baixa | `06_api_avaliacoes.sql` | A reavaliação usa a data UTC, e não a de São Paulo | Desenvolvimento |
| 7 | Baixa | PR #25 e #26 | Detalhes do PDF e do resumo do lote (lista abaixo) | Desenvolvimento |

### 1. API vazia para quem entra com login (alta)

**O que acontece.** Com o token de um usuário PKZ, One to One ou `TODAS`, a `api.atleta` devolve 0 linhas. O mesmo vale para `evolucao`, `comparacao` e `reavaliacao`. Com a secret key devolve tudo, e por isso o PDF e o e-mail funcionam.

**Por quê.** Desde o PR #18, as views da `api` leem a `novo.vw_aluno` e a `novo.vw_avaliacao_medida`. Essas views foram criadas com `security_invoker = true` (013/014), e no PostgreSQL uma view `security_invoker` **aplica as permissões e o RLS de quem fez a consulta mesmo quando é lida por dentro de outra view**. O usuário da API não tem perfil no app, então o RLS da 012 esconde todos os alunos. Confirmado no banco local: só de tirar o `security_invoker` das duas views, o mesmo usuário PKZ passa a ver os 17 atletas.

É o mesmo problema que o Rafael já corrigiu na `api.presenca` e na `api.treino` (PR #23, "presenca e treino voltam a ler as tabelas do novo"). Nos testes, essas duas funcionam.

**Como reproduzir no Supabase.** Rode `python backend/scripts/testar_acesso.py`. O teste 2 ("com o usuário de teste") deve vir sem atletas.

**Impacto.** Quebra qualquer tela, dashboard ou painel que use login, e o teste 2 da task "Proteger a API". Não afeta o PDF nem o e-mail (secret key).

**Sugestão.** Fazer o `trat.medida` e o `trat.aluno_unidade`/`api.atleta` lerem as tabelas do `novo`, como na 08. A outra opção é o grupo de Dados criar versões sem `security_invoker` para uso interno do Desenvolvimento.

### 2. PDF com dados de depois do período (média)

No relatório **mensal de agosto/2026** de um atleta avaliado em 13/08 e de novo em 20/10:
- "Avaliação atual x anterior" compara **outubro com agosto**. O gerador usa a `api.comparacao`, que sempre traz as duas avaliações mais recentes;
- os gráficos de evolução vão até 20/10/2026;
- "Total de avaliações" mostra 5 e "Última avaliação" mostra 20/10/2026.

Isso importa já: o PR #26 diz que o próximo passo é rodar **o lote de agosto**, agora em novembro. **Sugestão:** filtrar a `evolucao` até o fim do período e calcular a comparação no próprio período, com a última avaliação até o fim do período contra a anterior a ela.

### 3. Lados misturados no gráfico (média)

O gerador agrupa a evolução só por `teste`. No single hop e no cross hop, os valores de direito e esquerdo viram uma linha só, em zigue-zague. Na tabela "atual x anterior" aparecem duas linhas "Cross hop" iguais, sem dizer qual é o lado. **Sugestão:** agrupar por `teste` + `lado` e escrever "(dir)" e "(esq)" no nome.

### 4. Tempo na velocidade máxima maior que o tempo total (média)

O catálogo diz que esse tempo "não pode passar do tempo total do teste", mas o `trat.medida` só confere a faixa de 1 a 900 s. Uma avaliação com tempo total de 300 s e 600 s na velocidade máxima entra como válida.

### 5. "Estável" arredondado antes da comparação (baixa)

A `api.comparacao` arredonda a variação para 1 casa e só depois compara com 2%. Uma variação de −1,96% vira −2,0% e sai como "melhorou", embora a regra seja menor que 2%. **Sugestão:** comparar com a variação sem arredondar e arredondar só a coluna exibida.

### 6. Data de "hoje" em UTC na reavaliação (baixa)

A `api.reavaliacao` usa `current_date`, que no Supabase é UTC. Das 21h à meia-noite de Brasília, os dias para vencer ficam 1 a menos. A 08 já usa a data de São Paulo. A consulta 9 do `22_supabase_verificacoes_gerais.sql` mostra a diferença no banco real.

### 7. Detalhes do PDF e do lote (baixa)

- A nota "Menor tempo = melhor resultado" é decidida pelo nome do teste ("sprint", "agilidade"). Por isso não aparece no Aquabag nem no Blazepod (tempo), onde menor também é melhor. O ideal é usar o campo `maior_melhor` da API.
- Um teste sem direção (altura, peso) com variação de 2% ou mais mostra o texto cru `sem_classificacao` na coluna Situação.
- Atleta sem avaliação no período: a seção "Evolução histórica" fica vazia, só com a nota de rodapé.
- No resumo do lote, os alunos One to One (que não têm gerador) entram em "sem dados", o que esconde que foram pulados.

### Aviso: hoje o PDF não tem nenhum gráfico

Nenhum teste do catálogo está com `confirmado = true`, porque falta a validação da PKZ. Por isso, no PDF, **todas** as comparações saem como "Em validação" e **todos** os gráficos são trocados por "Gráfico disponível depois que a PKZ validar este teste". O comportamento é o planejado, mas vale saber antes de mostrar o PDF ao cliente. Os gráficos foram testados marcando os testes como confirmados no banco local.

---

## O que passou

**Tratamento das medidas** (`qa/sql/10_testes_tratamento.sql`):
- **Conversão:** single hop, cross hop e altura em metros viram cm, e a distância do VO2 em km vira m. Um valor exatamente no corte (10 no single hop, 3 na altura) não é convertido e vai para revisão, como o esperado.
- **Valores impossíveis:** sprint de 10 m em 17 s, tempo total do VO2 de 6 s e slalom de 300 vão para `trat.revisao_dados` e não chegam à API. Os limites da faixa (por exemplo, Illinois 5,0 e 25,0) são aceitos. Valor só em texto vai para revisão como "valor não numérico".
- **Melhor tentativa:** o menor valor nos testes de tempo, o maior nos de distância e flexibilidade, e a média nos sem direção (peso, altura, slalom). Tentativa descartada não entra na conta.
- **Comparação:** −2,0% melhorou, −1,9% estável, +2,0% piorou, só uma avaliação dá "sem comparação", altura dá "sem classificação" e o anterior igual a zero é tratado sem quebrar. Os lados são comparados separadamente, já convertidos.
- **Reavaliação:** 59 dias → em dia (31 dias), 60 → a vencer (30), 90 → a vencer (vence hoje), 91 → vencida.
- **Carga:** a avaliação corrigida sai e fica só a correção. Uma correção em rascunho não esconde a original. Avaliação em rascunho e de fisioterapia não entram. Aluno sem matrícula vigente ou com matrícula vencida fica sem unidade.

**Treinos:** a `api.presenca` só traz treino até hoje e troca `aguardando_confirmacao` por `agendado`. A `api.treino` só traz relatório final até hoje e nenhum campo de dor.

**Acesso:** sem login (`anon`) é bloqueado. O usuário logado não lê o `trat`. Cada unidade só vê as próprias presenças. As funções do `09` (PR #26) só são executadas pela secret key: `anon` e `authenticated` são bloqueados.

**PDF** (PR #25, relatório mensal de agosto/2026):
- longo (5 avaliações, 12 testes, 8 treinos agendados no mês): 3 páginas, ou 6 com os gráficos. Presença de 71,4% = 5 ÷ (5 + 2), como na regra. Nomes longos de atleta e de teste quebram a linha sem sobrepor;
- curto (1 avaliação, 3 testes): 2 páginas, tudo como "Sem comparação"/"Em validação";
- incompleto (só frequência, sem idade nem categoria): 1 página, com "—" nos campos vazios;
- atleta sem nada no período: o PDF não é gerado, como o esperado.

**Envio em lote** (PR #26, com o SMTP falso):
1. a simulação lista os 5 alunos com dados em agosto e não envia nada;
2. com `--limite 2`, envia 2, guarda os PDFs em `teste/pkz/mensal/2026-08-01/<uuid>.pdf` e registra em `trat.envio_relatorio`;
3. ao rodar de novo, envia só os 3 que faltavam;
4. ao rodar uma terceira vez, não envia nada ("5 já enviados");
5. com um destinatário fora de `EMAILS_TESTE`, para antes de enviar.

Todos os e-mails foram para o endereço de teste, com `[TESTE · nome]` no assunto e o PDF anexo.

---

## O que falta (precisa dos dados reais, no Supabase)

São só consultas de leitura. Rodar no SQL Editor:

1. `qa/sql/20_supabase_escolher_atletas.sql`: sugere um atleta por situação (histórico longo, uma avaliação, One to One, valor convertido, valor em revisão, sem unidade, reavaliação vencida, nunca avaliado). Esses são os atletas de referência.
2. `qa/sql/21_supabase_conferir_atleta.sql`: para cada atleta de referência, troque o UUID e compare tentativa por tentativa com a tela do app (valor no app → tratado → resultado na API). A segunda consulta mostra medidas que não chegam ao `trat`.
3. `qa/sql/22_supabase_verificacoes_gerais.sql`: cobertura do catálogo, totais, revisões e conversões por teste, e quantos casos reais os bugs 4, 5 e 6 afetam.
4. `python backend/scripts/testar_acesso.py` para confirmar o bug 1 no Supabase.

Na planilha de conferência, use só o `atleta_id` (UUID). Nome, PDF real e resultados com dados de aluno não entram no GitHub.

## Como rodar

Num PostgreSQL local (nunca no Supabase), na branch `backend`:

```bash
PGURL=postgresql://postgres@localhost:5432/postgres bash qa/rodar_testes_local.sh
```

Depois dos testes, o script carrega a massa dos PDFs (`qa/sql/02_dados_relatorio.sql`) no `qa_local`. PDF e e-mail de ponta a ponta, na branch do PR #26:

```bash
python qa/e2e/api_local.py --banco postgresql://postgres@localhost/qa_local &
export SUPABASE_URL=http://127.0.0.1:54321 SUPABASE_SECRET_KEY=local
python gerador_pkz/gerar_pdf.py 00000000-0000-0000-0000-000000000a41 --periodo mensal --referencia 2026-08-20
python qa/e2e/rodar_lote_local.py --periodo mensal --referencia 2026-08-20 --simular
```
