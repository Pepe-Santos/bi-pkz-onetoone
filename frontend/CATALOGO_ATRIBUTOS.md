# Atributos de cada modalidade

Registro de qual dado da API alimenta cada atributo do cartão. A versão que os programas leem é [`catalogo_atributos.json`](catalogo_atributos.json), usada pelo dashboard do atleta; o painel comparativo v4 traz uma cópia dela no próprio arquivo.

**Situação dos dados em 05/11/2026:** `api.evolucao` tem 22 combinações de teste e lado, todas de atletas da PKZ. **A API não informa a modalidade do atleta**, nem sexo, posição ou foto.

## De onde vem a modalidade

O campo Modalidade do dashboard é um filtro: mostra só os atletas daquela modalidade. Ele usa, nesta ordem:

1. `api.atleta.modalidade`, quando esse campo existir na API.
2. `dashboard_atleta/modalidades_atletas.csv`, lista local preenchida pela escola. Tem nomes de menores, então fica fora do GitHub.
3. A categoria, nos 2 casos em que ela já traz o esporte: `natacao` e `hipismo`.

Atleta sem modalidade, ou com uma que não está no catálogo, usa os **atributos gerais**: VEL, POT, AGI, RES, MOB e SIM, com os mesmos testes do futebol. O painel comparativo ainda não tem esse filtro: nele, a modalidade só troca os atributos.

## Como ler a tabela

- **Medido:** o teste mede o que o atributo promete.
- **Aproximado:** é o teste mais próximo que existe; ele não mede exatamente o atributo.

**Regra:** todo atleta de uma modalidade tem os mesmos seis atributos, e todos eles vêm de um teste que a bateria mede. Atleta novo, ou que ainda não fez um teste, recebe um aviso no cartão, nunca um número inventado.

Em todas as modalidades da PKZ, **SIM** é a simetria entre as pernas no `single_hop` e fica fora da nota e do radar, como alerta.

**Trocas de 04/11/2026:** os atributos sem teste saíram. Esta escolha é do Front-end e a coordenação técnica ainda precisa validá-la.

| Modalidade | Saiu (sem teste) | Entrou | Por quê |
|---|---|---|---|
| Futebol de campo | FOR, Força | RES, Resistência | O jogo é longo e a bateria mede VO2 |
| Futsal | FOR, Força | REA, Reação | Quadra pequena, decisão rápida |
| Basquete | TRO, Força de tronco | EST, Estabilidade | A Aquabag é o teste mais perto do controle de tronco |
| Vôlei | BLQ, Alcance de bloqueio | BLQ, Salto de bloqueio | Mede a altura do salto parado, não o alcance das mãos |
| Vôlei | OMB, Força de ombro | REA, Reação | Defesa e bloqueio dependem de reagir rápido |

`slalom_wallball` tem dados, mas ficou de fora: a API não define se o valor maior é melhor ou pior.

## PKZ · Futebol de campo

| Sigla | Atributo | Teste (`api.evolucao.teste`) | Melhor | Situação |
|---|---|---|---|---|
| VEL | Velocidade | `sprint_20` | Menor | Medido |
| POT | Salto | `saltos_vert_countermovement` | Maior | Medido |
| AGI | Mudar de direção | `illinois` | Menor | Medido |
| RES | Resistência | `teste_vo2_distancia_total` | Maior | Medido |
| MOB | Flexibilidade | `banco_wells` | Maior | Medido |
| SIM | Equilíbrio das pernas | `single_hop`, direita e esquerda | Mais perto de 100 | Medido |

## PKZ · Futsal

| Sigla | Atributo | Teste | Melhor | Situação |
|---|---|---|---|---|
| DIR | Mudar de direção | `illinois` | Menor | Medido |
| ARR | Arranque curto | `sprint_10` | Menor | Aproximado: o relatório fala em 5 m, a bateria mede 10 m |
| SAL | Salto | `saltos_vert_countermovement` | Maior | Medido |
| REA | Reação | `blazepod_vel_reacao_ms` | Menor | Medido |
| MOB | Flexibilidade | `banco_wells` | Maior | Medido |
| SIM | Equilíbrio das pernas | `single_hop`, direita e esquerda | Mais perto de 100 | Medido |

## PKZ · Basquete

| Sigla | Atributo | Teste | Melhor | Situação |
|---|---|---|---|---|
| ARR | Arranque curto | `sprint_10` | Menor | Aproximado: a bateria mede 10 m |
| SAL | Salto | `saltos_vert_countermovement` | Maior | Medido |
| DIR | Mudar de direção | `illinois` | Menor | Medido |
| EST | Estabilidade | `estabilidade_aquabag` | Menor | Medido |
| MOB | Flexibilidade | `banco_wells` | Maior | Medido |
| SIM | Equilíbrio das pernas | `single_hop`, direita e esquerda | Mais perto de 100 | Medido |

## PKZ · Vôlei

| Sigla | Atributo | Teste | Melhor | Situação |
|---|---|---|---|---|
| BLQ | Salto de bloqueio | `saltos_vert_countermovement` | Maior | Aproximado: salto parado, sem medir o alcance das mãos |
| ATQ | Salto de ataque | `saltos_vert_abalakov` | Maior | Aproximado: salto parado, sem a passada do ataque |
| DES | Deslocamento | `illinois` | Menor | Aproximado: mede mudança de direção |
| REA | Reação | `blazepod_vel_reacao_ms` | Menor | Medido |
| MOB | Flexibilidade | `banco_wells` | Maior | Medido |
| SIM | Equilíbrio das pernas | `single_hop`, direita e esquerda | Mais perto de 100 | Medido |

## One to One

Atributos da ficha do relatório One to One da AP1. Testes escolhidos pelo Front-end em 10/11/2026 e aprovados pela gerência para a apresentação; a coordenação técnica ainda pode trocá-los.

| Sigla | Atributo | Teste (`api.evolucao.teste`) | Melhor |
|---|---|---|---|
| FIN | Força de inferiores | `cadeira_isometrica` (segundos) | Maior |
| RES | Resistência | `teste_vo2_distancia_total` | Maior |
| POT | Potência | `saltos_vert_countermovement` | Maior |
| FSU | Força de superiores | `flexao_bracos` (repetições em 1 min) | Maior |
| COR | Core | `prancha_ventral` (segundos) | Maior |
| MOB | Mobilidade | `banco_wells` | Maior |

Na API real, os alunos do One to One ainda não têm avaliações: o cartão mostra o aviso de aluno sem avaliação. `cadeira_isometrica`, `flexao_bracos` e `prancha_ventral` ainda não existem na bateria da API; existem nos dados fictícios da apresentação.

## Testes fora dos atributos

Estes testes têm dados e aparecem nos gráficos do dashboard, mas não entram na nota de nenhuma modalidade: `slalom_wallball`, `saltos_vert_squat_jump`, `cross_hop`, `teste_vo2_vel_max`, `teste_vo2_tempo_total`, `teste_vo2_tempo_vel_max`, `blazepod_vel_reacao_hits`, `blazepod_foco`, `antropometria_altura` e `antropometria_peso`.

## Como a nota é calculada (provisória)

1. **Último resultado:** usa o valor mais recente de cada teste.
2. **Percentil:** de 0 a 99, entre os atletas da mesma faixa de idade: até 10 anos, 11 e 12, 13 a 17, 18 ou mais (18 ou mais separado em 10/11/2026, por causa dos adultos do One to One). Faixa com menos de 5 resultados no teste fica sem valor, com aviso.
3. **Simetria:** menor lado ÷ maior lado × 100. Abaixo de 90 fica em alerta.
4. **Nota:** média dos atributos preenchidos, sem a simetria. Precisa de pelo menos 3.
5. **Nível e metal:** E até 20 e D até 40 (bronze), C até 60 (prata), B até 80 (ouro), A acima (preto). É a regra provisória do README do projeto.

A fórmula definitiva é da escola. Quando ela existir, o ideal é a API entregar a nota pronta.

## O que falta para fechar

| Falta | Quem resolve | O que muda |
|---|---|---|
| `modalidade` em `api.atleta` | Dados e Desenvolvimento | O filtro funciona para todos, sem lista local, e o painel pode ganhar o mesmo filtro. A comparação continua por faixa de idade até o grupo decidir |
| `sexo` em `api.atleta` | Dados e Desenvolvimento | Comparar por idade e sexo, como pede o relatório |
| `posicao` e foto | Dados e Desenvolvimento | Completam o cartão |
| Validar as trocas de atributo | Coordenação técnica | Confirma ou ajusta os atributos escolhidos pelo Front-end |
| Sentido do `slalom_wallball` | Dados e PKZ | Permite usar o teste como atributo de controle de bola |
| Testes de força, ombro, alcance de bloqueio e arranque de 5 m | Coordenação técnica | Medem os atributos originais, se a escola quiser voltar a eles |
| Avaliações do One to One | Escola | Permitem nota para esses alunos |
| Consultas de nutrição e fisioterapia na API | Desenvolvimento | Hoje `api.presenca` traz só treinos |
| Gravar a chamada pela API | Desenvolvimento | Hoje a API só lê; o painel só mostra a chamada registrada |
