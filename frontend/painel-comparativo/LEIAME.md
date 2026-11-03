# Painel comparativo — v3

[`painel-comparativo-v3.html`](painel-comparativo-v3.html) é o painel que
compara os alunos de um grupo atributo por atributo, mostra quem está acima ou
abaixo da média, compara dois atletas lado a lado e faz a chamada do dia.

Abre com duplo clique, sem servidor. Funciona no computador e no celular: o
layout troca sozinho abaixo de 1100 px.

## Versões

| Versão | Data | O que é |
|---|---|---|
| v3 | 28/10/2026 | Esta. A versão apresentada ao cliente mais os pedidos que ele fez na apresentação |
| Publicada | 27/10/2026 | A apresentada no dia da entrega |
| Primeira | 29/09/2026 | Copiada à mão do componente do Claude Design |

## O que a v3 acrescenta

1. **Ranking.** Cada aluno mostra a posição no atributo escolhido, com ouro,
   prata e bronze para os três primeiros. Quem empata no valor divide a
   posição. O modo *Ranking*, ao lado do título da lista, mostra a turma inteira
   em linhas: posição, nome, valor e uma barra com a média do grupo.
2. **Resumo do dia.** Sessões de hoje, presentes, faltas e quem ainda aguarda
   chamada. Os números mudam assim que o professor marca a chamada.
3. **Consultas.** No One to One, as consultas de nutrição e fisioterapia de
   hoje aparecem no resumo, e as próximas, no card de cada aluno.
4. **Perfis por área.**

   | Perfil | O que vê |
   |---|---|
   | Admin | Tudo: PKZ e One to One, e troca de área nas abas |
   | Professor PKZ | Só o PKZ. A aba One to One fica bloqueada |
   | Professor One to One | Só o One to One, com o resumo do dia e as consultas. A aba PKZ fica bloqueada |

## Regras que o painel aplica

- **PKZ:** a nota do card é a média das cinco capacidades; a simetria fica fora,
  como alerta. Só compara alunos da mesma modalidade.
- Nível de E a A, e o metal acompanha o nível.
- "Na média" = até 5 pontos de diferença da média do grupo filtrado.

## Dados

**Todos os dados são fictícios.** Os 30 alunos (20 do PKZ e 10 do One to One)
são gerados no próprio arquivo, com semente fixa; não há fotos, só o espaço
reservado. Nada vem do banco.

## O que falta para ligar aos dados reais

| Pendência | Quem |
|---|---|
| Ler os alunos e os atributos pelas views do schema `api` | Desenvolvimento |
| Gravar a chamada (presente e faltou) | Desenvolvimento |
| Agendamentos de nutrição e fisioterapia de cada aluno | Desenvolvimento e Dados |
| Devolver só os alunos da área do professor, a partir do login. O bloqueio de hoje é só da tela | Desenvolvimento |
| Sexo, modalidade, posição e categoria padronizada no cadastro | Dados |
| Fórmula da nota, do nível e do metal | Escola |
