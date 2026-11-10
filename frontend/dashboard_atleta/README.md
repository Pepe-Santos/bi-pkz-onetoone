# Dashboards da PKZ e do One to One

App em Streamlit com três telas, escolhidas nos botões do topo: **Atleta**, **Comparativo** e **Reavaliações**. As três usam o mesmo cartão, o mesmo catálogo de atributos e a mesma nota provisória.

**Tela Atleta**

- a mesma barra de filtros do Comparativo: área (PKZ ou One to One, conforme o login), modalidade, faixa de idade e inativos. O que se escolhe numa tela continua escolhido na outra;
- embaixo, o atleta, com setas para passar de um para o outro;
- no One to One, o aluno aparece com presença e relatórios de treino, e um aviso de que ainda não há avaliação física na API;
- visão geral: avaliações, comparação, presença e reavaliação;
- cartão do atleta, no desenho do painel comparativo, com nota, nível e os seis atributos da modalidade;
- radar dos atributos, contra a média do grupo;
- descrição de como vêm sendo os relatórios: avaliações, saldo da comparação, maior evolução, ponto de atenção, frequência, relatórios de treino e reavaliação;
- onde o atleta se destaca e o que mudou contra a avaliação anterior;
- um gráfico para cada teste, com a forma ligada ao número de avaliações, e um aviso quando falta dado para comparar;
- tabela compacta com todos os valores, fechada por padrão.

**Tela Comparativo** (o painel comparativo, agora no mesmo app)

- área PKZ ou One to One, conforme a unidade do login: o admin vê as duas, cada professor só a sua;
- filtros de modalidade, faixa de idade, inativos e "comparar por" (nota ou um atributo da modalidade escolhida);
- faixa azul com quantos estão acima, na média e abaixo, e a média do grupo filtrado;
- resumo da chamada de hoje, só leitura, e a distribuição da turma por nível;
- cartões ordenados pelo que se está comparando, ou o ranking em barras;
- comparação de dois atletas, atributo por atributo, com a média do grupo marcada.

**Tela Reavaliações**: lista das reavaliações vencidas e a vencer, para a coordenação.

## Como rodar

Nesta pasta (`frontend/dashboard_atleta`), com Python 3.11 ou mais novo:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

No Mac ou no Linux, ative o ambiente com `source .venv/bin/activate`. A tela abre no navegador, em `http://localhost:8501`.

## De onde vêm os dados

**Com o `.env`, da API.** Copie o `.env.example` para `.env` e preencha a URL, a publishable key, o e-mail e a senha do usuário de teste. A senha é passada em particular pelo Miguel. O `.env` não vai para o GitHub.

**Sem o `.env`, dos exemplos.** A tela usa os JSON fictícios de `backend/exemplos/api/` e avisa no topo que são dados de exemplo. Como não existe `reavaliacao.json`, a situação da reavaliação é calculada pela mesma regra da view: 90 dias para vencer e aviso a 30 dias. Se a API falhar, a tela mostra o erro e não troca para os exemplos.

Contrato das views: [`backend/docs/api.md`](../../backend/docs/api.md). O dashboard usa `atleta`, `evolucao`, `comparacao`, `reavaliacao`, `presenca` e `treino`, só com `unidade = PKZ`. Os dados ficam em memória por 5 minutos; o botão *Atualizar* lê tudo de novo.

## Regras que a tela segue

- Melhorou, piorou, estável e vencimento vêm prontos da API; a tela não recalcula nada.
- Teste com regra ainda não confirmada pela PKZ (`confirmado = false`) mostra a classificação com um asterisco e um aviso. Pelo `api.md`, no relatório dos pais esse teste aparece só com os valores.
- Atletas inativos ficam fora, a não ser que se ligue *Incluir atletas inativos*.

## Atributos e nota do cartão (provisória)

A API ainda não entrega nota, nível, metal, modalidade, posição nem foto. O cartão calcula uma nota provisória em `cartao.py` e diz isso na tela. Os atributos de cada modalidade, os testes usados e as regras estão em [`../CATALOGO_ATRIBUTOS.md`](../CATALOGO_ATRIBUTOS.md); a versão lida pelo programa é [`../catalogo_atributos.json`](../catalogo_atributos.json).

O painel comparativo v4 aplica as mesmas regras e dá a mesma nota.

## Filtro de modalidade

O campo *Modalidade* mostra na lista só os atletas daquela modalidade, e começa em *Todas as modalidades*. Cada atleta usa os atributos da própria modalidade. Sem modalidade registrada, usa os atributos gerais e aparece só em *Todas as modalidades*.

A API ainda não informa a modalidade. Até informar, ela vem de uma lista local:

1. Gere a lista: `.venv/Scripts/python gerar_lista_modalidades.py`. Quem já foi preenchido é mantido.
2. Abra `modalidades_atletas.csv` no Excel e preencha a coluna `modalidade`: Futebol de campo, Futsal, Basquete ou Vôlei. Outra modalidade também funciona, com os atributos gerais.
3. Salve como CSV e clique em *Atualizar* no dashboard.

**A lista tem nomes de menores.** Ela fica só nesta máquina, fora do GitHub: não mande em grupo. Quando a API trouxer `modalidade`, o valor da API passa a valer e a lista deixa de ser necessária.

## Como a tela é lida

1. **Como está:** frase principal, números, cartão, radar dos atributos e descrição dos relatórios.
2. **Onde se destaca e o que mudou:** posição entre os colegas e valores de antes e agora.
3. **Como veio evoluindo:** cada dado na forma que comunica melhor. A análise, dado por dado, está em [`../ANALISE_GRAFICOS.md`](../ANALISE_GRAFICOS.md), e os gráficos, em `graficos.py`.

A descrição (`relato.py`) é montada a partir das views da API, sem IA e sem texto inventado. Quando o relatório de treino tem observação do treinador, a última aparece como foi escrita.

## Cuidado com os dados

A tela mostra nome e resultados de menores de idade, e quem abre usa o login do `.env`, sem digitar senha. Por isso ela só atende nesta máquina (`server.address = "localhost"`, em `.streamlit/config.toml`). **Não publique este app em um servidor ou no Streamlit Cloud sem antes colocar um login por usuário.**
