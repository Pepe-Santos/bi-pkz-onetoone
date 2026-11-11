# Frente 3 · 3.1 — Matriz de papéis × tabelas

> Iago · atualizado em 22/10/2026 · vira a especificação da 3.3 (políticas RLS).
>
> Refeito contra o banco real: o schema `novo` ficou pronto em 21/10 (Frente 1, PR #5) com
> **43 tabelas e 5 views**. A primeira versão desta matriz usava os 9 papéis do app; o modelo novo tem
> **5**. Fontes: estrutura lida do banco em 22/10.
>
> Legenda: **[Fato]** lido do banco · **[Proposta]** desta frente · **[Pendência]** depende de decisão.

## Situação do acesso hoje

**[Fato] O banco está carregado e inalcançável.** Três camadas de fechadura, todas ativas:

1. Todas as 43 tabelas têm RLS ligado e **nenhuma política**.
2. Nenhum papel tem `USAGE` no schema `novo` — nem `authenticated`, nem `service_role`.
3. O schema não está exposto na Data API.

Ou seja: enquanto a 3.3 não entrar, nem o back-end lê o banco novo, mesmo tendo sido combinado em
20/10 que ele leria direto. É o que trava a próxima etapa do projeto.

**[Fato] As 5 views respeitam o RLS.** Todas têm `security_invoker = true`, então elas aplicam a
política de quem consulta, e não a do dono. Sem isso, qualquer política de tabela seria contornável
pela view. A Frente 1 acertou nesse ponto.

## Os 5 papéis

**[Fato]** `novo.papel` e `novo.papel_usuario`: 153 vínculos, 18 deles com unidade.

| Papel | O que era no app | Escopo |
|---|---|---|
| `admin` | admin | tudo |
| `recepcao` | recepcao | operacional das duas unidades, sem dado clínico |
| `professor` | professor, professor_pkz, professor_one_to_one | alunos da sua unidade |
| `especialista` | fisioterapeuta, nutricionista, psicologo | alunos que atende, no seu serviço |
| `responsavel` | responsavel | os próprios alunos |

**[Fato]** Unidade nula no vínculo quer dizer "todas as unidades": 135 vínculos globais e 18 por
unidade. Só professor usa unidade.

**[Proposta]** As equipes de Analytics, Relatório e Dashboard não entram como papel. Elas consomem as
views do schema `api`, com o papel de serviço do back-end, que passa por cima do RLS por desenho. O
controle nessa ponta é o que a view mostra, não a política.

## Como o escopo é resolvido

**[Fato]** A estrutura já tem tudo o que a política precisa:

| Escopo | Caminho no banco |
|---|---|
| Própria pessoa | `perfil_usuario.usuario_id = auth.uid()` → `pessoa_id` |
| Próprio aluno | `responsavel_aluno(aluno_id, pessoa_id)` |
| Própria unidade | `papel_usuario.unidade_id` × `matricula.unidade_id` |
| Aluno que atende | `profissional_id` em agendamento, atendimento, avaliação ou relatório; para dado clínico, só no serviço do dado |
| Clínico | `anamnese.confidencialidade` e `arquivo.confidencialidade` |

## A matriz

Leitura (L). Escrita não entra: quem grava em `novo` é a carga, com papel privilegiado. Sem política de
escrita, `authenticated` não grava nada — e isso é proposital.

| Grupo de tabelas | admin | recepção | professor | especialista | responsável |
|---|---|---|---|---|---|
| Referência: unidade, servico, plano, plano_beneficio, papel, metrica, catalogo_item | L | L | L | L | L |
| `configuracao_unidade` | L | L | — | — | — |
| `pessoa` | L | L | L (sua unidade) | L (quem atende) | L (próprio + seus alunos) |
| `perfil_usuario`, `papel_usuario` | L | L | L (o próprio) | L (o próprio) | L (o próprio) |
| `aluno`, `aluno_servico`, `responsavel_aluno` | L | L | L (sua unidade) | L (quem atende) | L (seus alunos) |
| `profissional`, `profissional_servico` | L | L | L | L | L |
| `matricula`, `renovacao`, `credito_lancamento` | L | L | — | — | L (seus alunos) |
| `horario_grade`, `bloqueio_agenda`, `bloqueio_grade` | L | L | L | L | L |
| `agendamento`, `sessao_treino`, `lista_espera`, `feedback_treino` | L | L | L (sua unidade ou seu atendimento) | L (quem atende) | L (seus alunos) |
| `relatorio_treino`, `relatorio_item` | L | L | L (sua unidade) | L (quem atende) | L (seus alunos) |
| `avaliacao`, `avaliacao_medida` | L | L | L (sua unidade) | L (quem atende) | L (seus alunos) |
| `atendimento`, `evolucao` | L | — | — | L (os seus) | — **[Pendência 5]** |
| `anamnese` | L | — | — | L (quem atende) | — **[Pendência 5]** |
| `arquivo` normal | L | L | L (sua unidade) | L (quem atende) | L (seus alunos) |
| `arquivo` clínico (39 de 523) | L | — | — | L (quem atende) | — **[Pendência 5]** |
| `consentimento` | L | L | — | — | L (o próprio) |
| `relatorio_emissao`, `relatorio_envio` | L | L | L (sua unidade) | — | L (seus alunos) |
| `notificacao` | L (a própria) | L (a própria) | L (a própria) | L (a própria) | L (a própria) |
| `evento_auditoria`, `acesso_dado_sensivel` | — | — | — | — | — **[Pendência 11]** |
| `carga_execucao`, `carga_rejeitado`, `carga_gabarito` | — | — | — | — | — |

**[Proposta]** Quatro regras que valem para a matriz inteira:

1. **Auditoria não se lê pela API.** `evento_auditoria` guarda `valor_anterior` e `valor_novo` em jsonb,
   que podem carregar dado pessoal (pendência 11). Até a decisão, nem o grant existe: leitura só por
   papel privilegiado.
2. **Clínico fecha por padrão.** Em `arquivo`, só `confidencialidade = 'normal'` segue o caminho aberto;
   qualquer outro valor, inclusive nulo ou um valor novo criado depois, cai na regra clínica.
3. **Professor não lê dado clínico.** Nem anamnese, nem atendimento, nem arquivo clínico.
4. **Responsável não lê o clínico do próprio filho** até a direção decidir (pendência 5). É a célula mais
   delicada da matriz: hoje o app deixa ver, e a versão proposta fecha.

## A migration

Está em [`dados/migracoes/migrations/012_politicas_rls.sql`](../migracoes/migrations/012_politicas_rls.sql).
Ela faz três coisas:

1. Abre o schema para `authenticated` e `service_role`, e deixa `anon` de fora.
2. Cria 10 funções que respondem quem sou eu e o que é meu (`tem_papel`, `e_staff`, `pessoa_atual`,
   `tem_unidade`, `aluno_sob_responsavel`, `aluno_na_minha_unidade`, `aluno_que_atendo`,
   `pode_ver_clinico`, `servico_do_arquivo`, `enxerga_aluno`). Todas `security definer`, senão a
   política da própria tabela entra em recursão. Só elas são executáveis por `authenticated`.
3. Cria uma política de SELECT por tabela, seguindo a matriz.

Conferi as 40 referências de tabela e coluna que ela usa: todas existem no banco. Na revisão de 25/10
(Frente 1), a migration foi aplicada no ensaio dentro de uma transação desfeita no fim e testada por
papel (admin, recepção, professor de cada unidade, professor global, fisio, nutri e responsável): nada
ficou gravado. Falta aplicar de vez, que fecha a 3.3.

## O que falta decidir

| # | Pergunta | Quem decide | O que trava |
|---|---|---|---|
| 5 | Quem vê anamnese e dado clínico, inclusive de criança | Direção, com respaldo jurídico | 4 células da matriz |
| 11 | Dado pessoal no log de auditoria: tirar ou guardar restrito | Frente 3, com a direção | grant e política de `evento_auditoria` |
| 4 | Destino de CPF, e-mail, endereço e telefone da avaliação de fisio | Direção | hoje não são carregados |
| 15 | Papel de professor sem unidade vale para as duas? | Coordenação | 135 vínculos globais |
