# Análise: o melhor gráfico para cada dado

Quem lê é um professor, que quer saber em poucos segundos como o atleta está e o que mudou. A regra usada aqui: **se o gráfico precisa de explicação, ele não é o certo para esse dado.** Em dado que é só um número, um número grande comunica melhor que qualquer gráfico.

**O que os dados reais mostram (04/11/2026):** dos 32 atletas da PKZ, 14 têm uma avaliação só, 9 têm duas e 7 têm três ou mais; 2 ainda não têm nenhuma. Por isso, a quantidade de avaliações também decide a forma.

## A forma de cada dado

| Dado | Forma | Por que essa |
|---|---|---|
| Situação geral | Faixa azul com frase e números | É a conclusão: não precisa de gráfico |
| Atributos do cartão | Radar com o atleta e a média do grupo | Formato comum no esporte. Mostra o desenho do atleta e funciona com poucos atributos. O equilíbrio fica fora, por usar outra escala |
| Melhores e piores resultados | Lista com "2º de 11" | Todo mundo entende posição. "Melhor que 78%" exigia explicação |
| O que mudou | Duas listas, Melhorou e Piorou, com "3,39 → 3,28 s" | O professor compara os valores reais. O percentual engana em números pequenos: de 1 para 0 vira 100% |
| Cada teste, com 3 avaliações ou mais | Linha com o valor em cada ponto | É valor ao longo do tempo. Com o valor escrito, o eixo vertical sai |
| Saltos verticais (3 tipos) | Colunas por salto, uma por avaliação | Mesma unidade e mesma capacidade: juntos, cabem num gráfico só |
| Single hop, Cross hop | Colunas direita e esquerda, mais a diferença (com uma avaliação: duas barras) | O que importa é a comparação entre as pernas, com o limite de 10% escrito |
| VO2, Blazepod, altura e peso | Um cartão por medida, cada um com o seu gráfico | As unidades são diferentes: não cabem no mesmo eixo |
| Todos os valores | Tabela compacta em duas colunas, fechada por padrão | Para consultar. Ocupa cerca de um terço do espaço da tabela antiga |
| Turma por nível (painel) | Colunas por nível, com o total | Mostra o grupo inteiro de uma vez |
| Ranking da turma (painel) | Barras ordenadas | É a forma natural de comparar pessoas em uma medida |

## Conforme a quantidade de avaliações

| Avaliações | Forma |
|---|---|
| 0 no teste | O cartão continua no lugar, com o aviso "Sem dados: o atleta ainda não fez este teste" |
| 1 | Número grande e duas barras: o atleta e a média do grupo. Um aviso explica que ainda não há evolução |
| 2 | Duas colunas: antes e agora. A diferença aparece melhor do que numa linha com dois pontos |
| 3 ou mais | Linha com o valor em cada avaliação |

Todo teste aparece sempre no mesmo lugar, em qualquer atleta. Assim o professor acha cada um sem procurar, e nunca fica sem saber se o dado existe.

## O que saiu, e por quê

| Saiu | Problema |
|---|---|
| Barras de percentil com todos os testes | "Melhor que X% dos colegas" pedia interpretação, e 20 barras não têm foco |
| Barras a partir do centro | Em percentual, destacavam variações pequenas de números pequenos |
| Eixo invertido nos testes de tempo | "Subir é melhorar" contrariava o valor escrito, que estava caindo |
| Pontos cinza dos colegas | Precisavam de legenda para serem entendidos |
| "Contra a média do grupo" abaixo do cartão | Repetia o radar e deixava a coluna mais alta que as outras |
| Número solto em atleta com uma avaliação | Dava a impressão de que os gráficos tinham sumido |

## Cores

Azul é o atleta, verde é a perna esquerda e o selo de melhora, e laranja é a atenção. O selo sempre traz a palavra escrita, então a cor nunca é a única pista.
