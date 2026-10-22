# Frente 3 · 3.2 — Decisões sobre dado sensível

> Pauta para a direção. Iago · 23/10/2026.
>
> A pendência 5 previa "respaldo jurídico": o grupo dispensou a revisão jurídica em 23/10 (Micael),
> por o ensaio rodar sobre cópia descaracterizada. As quatro decisões abaixo seguem necessárias, e são
> de gestão.
>
> Fecha as pendências 4, 5 e a parte de consentimento da 11. Cada resposta vira ajuste no DDL e na
> carga (Frente 1) e nas políticas de acesso (3.3), e volta registrada em
> [PENDENCIAS.md](../migracoes/PENDENCIAS.md) com quem decidiu e quando.
>
> Números lidos do banco em 23/10/2026, em modo somente leitura. Nenhum dado pessoal neste documento:
> só contagens.

## Por que isto precisa de decisão, e não de escolha técnica

O banco novo está construído e carregado, e as políticas de acesso estão escritas (migration 012). Três
celas dessa política dependem de uma decisão que não é nossa. Enquanto ela não vem, a política entra na
versão mais fechada — inclusive fechada para o responsável, que hoje, no app, consegue ver.

O que está em jogo, em número:

| Fato | Número |
|---|---|
| Alunos no banco | 106 |
| **Alunos menores de 18 anos** | **105** |
| Alunos menores de 13 anos | 65 |
| Anamneses (histórico clínico) | 4, **todas de menores** |
| Avaliações de fisioterapia | 4, com 189 medidas clínicas |
| Atendimentos de fisioterapia e nutrição | 22 |
| Relatórios de treino com campo de dor preenchido | **214** |
| Arquivos de aluno | 523, dos quais 39 marcados como clínicos |
| **Consentimento registrado** | **0** |

Dois pontos que chamam atenção na tabela:

1. **O dado de saúde não está só na fisioterapia.** 214 dos 228 relatórios de treino têm o campo de dor
   preenchido. É dado de saúde de menor registrado pelo professor, na rotina, fora de qualquer
   tratamento clínico.
2. **Não existe registro de consentimento.** A tabela existe no modelo novo e está vazia, porque a
   origem não tem esse dado. Para tratamento de dado de saúde de menor, a LGPD exige consentimento
   específico e destacado do responsável.

## Decisão 1 — Documentos pessoais na avaliação de fisioterapia (pendência 4)

**Situação.** A avaliação de fisioterapia na origem guarda, além das medidas, seis campos de
identificação: CPF, e-mail, endereço, telefone, profissão e sexo. São 4 registros, todos preenchidos. A
carga **não** trouxe esses campos para o banco novo: eles estão parados na origem, esperando esta
decisão.

**Opções.**

| Opção | O que acontece | Efeito |
|---|---|---|
| **A. Descartar** | Os seis campos não entram no banco novo | Menos dado pessoal guardado, que é o princípio da coleta mínima. CPF e endereço não têm uso nos relatórios nem nos indicadores |
| **B. Trazer para o cadastro** | CPF e telefone vão para `pessoa`; o resto é descartado | Unifica o cadastro, mas passa a guardar CPF de 4 pessoas sem finalidade definida |
| **C. Manter na avaliação** | Os seis campos entram junto da avaliação clínica | Repete dado de cadastro dentro de dado clínico; é o arranjo que a origem já tem e que criou o problema |

**Recomendação da Frente 3: opção A.** Nenhum dos seis campos é usado por relatório, dashboard ou
indicador. Se depois aparecer uma finalidade, o dado continua na origem e pode ser trazido.

**Decisão:** ____________________  **Quem:** ____________  **Data:** ____________

## Decisão 2 — Quem pode ver dado clínico (pendência 5)

**Situação.** Dado clínico no banco novo é: `anamnese` (histórico clínico, com doenças, cirurgias,
medicamentos, histórico familiar e hábitos), `avaliacao` do tipo fisioterapia com suas medidas,
`atendimento` de fisioterapia, nutrição e psicologia com as evoluções, e os 39 arquivos marcados como
clínicos. O campo de dor do relatório de treino é um caso à parte, tratado na decisão 4.

**O que a política faz hoje, na versão fechada:** só o `admin` e o especialista que atende aquele aluno.
Recepção, professor e responsável não leem.

**O que precisa ser respondido, papel por papel:**

| Papel | Pergunta | Hoje no app |
|---|---|---|
| **Responsável** | Pode ver a anamnese e a evolução clínica do próprio filho? | Sim, vê |
| **Recepção** | Precisa ver algo clínico para operar a agenda? | Vê evolução de fisio e avaliação de fisio |
| **Professor** | Precisa de alguma informação clínica para montar o treino, ou basta a restrição de movimento? | Vê o relatório com o campo de dor |
| **Especialista** | Vê só o próprio serviço, ou fisio, nutri e psico se enxergam? | Vê só o próprio serviço |
| **Admin** | Vê tudo, ou dado clínico fica fora também para o admin? | Vê tudo |

**Por que decidir agora:** 105 dos 106 alunos são menores, e a regra de "quem pode ver" precisa estar
escrita antes de o banco ser aberto para consumo. A política vai junto para o projeto definitivo, onde
o dado é real: escrever a regra agora assumindo dado de ensaio é levá-la assim para a produção.

**Recomendação da Frente 3:** manter fechado para recepção e professor; abrir para o responsável apenas
o que diz respeito ao próprio aluno; manter especialista restrito ao próprio serviço. Com uma condição:
todo acesso a dado clínico fica registrado em `acesso_dado_sensivel`, que já existe no modelo.

**Decisão:** ____________________  **Quem:** ____________  **Data:** ____________

## Decisão 3 — Níveis de confidencialidade e consentimento

**Situação.** O arquivo já tem três níveis previstos (normal, clínico, restrito) e hoje usa dois: 484
normais e 39 clínicos. A anamnese nasce como restrita. A tabela de consentimento existe e está vazia.

**Perguntas:**

1. Os três níveis bastam, ou falta um nível para documento que nem o especialista vê (laudo externo,
   por exemplo)?
2. É preciso registrar consentimento do responsável? Para qual finalidade: tratamento dos dados, envio
   do relatório mensal por e-mail, uso da imagem, ou os três separadamente?
3. O consentimento é coletado onde, e por quem? Hoje não existe tela nem campo para isso em lugar nenhum.
4. Por quanto tempo o dado de um aluno que saiu continua guardado?

**Recomendação da Frente 3:** registrar consentimento por finalidade, separando tratamento de dados e
envio de relatório. O envio automático do relatório por e-mail é o objetivo final do projeto, e ele
manda dado de saúde de menor para fora do sistema: sem consentimento registrado, esse envio não deveria
ser ligado.

**Decisão:** ____________________  **Quem:** ____________  **Data:** ____________

## Decisão 4 — Campo de dor no relatório de treino

**Situação.** Não estava nas pendências, e apareceu ao escrever a política: 214 dos 228 relatórios de
treino têm o campo de dor preenchido (local, intensidade e movimento). É dado de saúde registrado pelo
professor na rotina do treino, e hoje o responsável e o professor leem.

**Perguntas:**

1. O campo de dor continua no relatório de treino, ou vira registro clínico separado?
2. Se continua, o relatório inteiro passa a ser tratado como dado de saúde, com o mesmo acesso restrito?
3. O relatório mensal que vai para o responsável inclui a dor relatada?

**Recomendação da Frente 3:** manter o campo onde está, porque o professor precisa dele para ajustar o
treino, e tratar o relatório de treino como dado de saúde para efeito de acesso: professor da unidade,
especialista que atende e responsável do próprio aluno. É o que a política faz hoje.

**Decisão:** ____________________  **Quem:** ____________  **Data:** ____________

## O que cada resposta destrava

| Decisão | O que muda |
|---|---|
| 1 | Carga do script 70 (Frente 1) e, se for a opção B, o DDL de `pessoa` |
| 2 | Quatro políticas da migration 012: `anamnese`, `avaliacao` de fisio, `atendimento` e `arquivo` clínico |
| 3 | Uso da tabela `consentimento`, hoje vazia, e a liberação do envio automático de relatório |
| 4 | Política de `relatorio_treino` e o conteúdo do relatório mensal |

## Enquanto não há resposta

A política entra na versão mais fechada, e nada é bloqueado para o projeto: o banco carrega igual, as
contagens e os indicadores funcionam. O que fica suspenso é o acesso de recepção, professor e
responsável ao que é clínico, e o envio automático do relatório por e-mail.
