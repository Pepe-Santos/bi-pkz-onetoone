# Painel comparativo

> **Agora o painel também está no app em Streamlit**, na tela *Comparativo* de [`../dashboard_atleta`](../dashboard_atleta/README.md), com o mesmo modelo do dashboard do atleta. Esta pasta guarda a versão em HTML, que abre sem Python.

**A versão que vale é a [`painel-comparativo-v4.html`](painel-comparativo-v4.html): dados reais, lidos da API, com login.** A `v3`, logo abaixo, fica como registro da versão com dados fictícios.

## v4: como abrir

1. Copie `painel-config.example.js` para `painel-config.js` e preencha a URL e a chave pública. Esse arquivo não vai para o GitHub.
2. Dê dois cliques em `painel-comparativo-v4.html`.
3. Entre com um usuário da API. O perfil vem da unidade do login: `TODAS` é Admin, `PKZ` é Professor PKZ e `ONE_TO_ONE` é Professor One to One. O token fica só na memória: recarregar a página pede o login de novo.

## v4: o que é real e o que mudou

| Na tela | De onde vem |
|---|---|
| Atletas, idade e categoria | `api.atleta`, só os ativos |
| Atributos e nota provisória | `api.evolucao`, pelas regras de [`../CATALOGO_ATRIBUTOS.md`](../CATALOGO_ATRIBUTOS.md). Dá a mesma nota do dashboard do atleta |
| Resumo do dia e presença | `api.presenca` |

**O que saiu, porque a API não tem o dado:** filtros de gênero e de data de entrada, posição, foto e consultas de nutrição e fisioterapia.

**O que está limitado:**

- **Modalidade:** a API não informa a do atleta. Aqui, a escolha na tela só troca os atributos usados, e a lista traz todos os atletas ativos da PKZ. O dashboard do atleta já filtra por modalidade; o painel recebe o mesmo filtro quando o dado existir na API.
- **Dado faltando:** todo atleta da modalidade mostra os mesmos seis atributos. O que falta aparece como "sem dado", com um aviso no cartão, nunca como número inventado.
- **Chamada:** só leitura, porque a API não grava. Os botões Presente e Faltou saíram.
- **One to One:** aparece sem nota, porque não há avaliações físicas na API.

O bloqueio entre unidades é da API, não só da tela. A tela apenas acompanha o que o login pode ver.

## v3

— v3

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
