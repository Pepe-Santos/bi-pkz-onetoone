# Dashboard do atleta (PKZ)

Tela em Streamlit em que se escolhe um atleta da PKZ e se vê como ele evolui nos testes físicos.

**Aba Atleta**

- nome, categoria e data da última avaliação;
- situação da reavaliação: em dia, vence em breve ou vencida;
- comparação com a avaliação anterior: melhorou, piorou ou estável;
- evolução de cada teste em gráfico de linha, com direita e esquerda separadas nos testes feitos com cada perna.

**Aba Reavaliações**: lista das reavaliações vencidas e a vencer, para a coordenação.

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

Contrato das views: [`backend/docs/api.md`](../../backend/docs/api.md). O dashboard usa `atleta`, `evolucao`, `comparacao` e `reavaliacao`, só com `unidade = PKZ`. Os dados ficam em memória por 5 minutos; o botão *Atualizar dados* lê tudo de novo.

## Regras que a tela segue

- Melhorou, piorou, estável e vencimento vêm prontos da API; a tela não recalcula nada.
- Teste com regra ainda não confirmada pela PKZ (`confirmado = false`) mostra a classificação com um asterisco e um aviso. Pelo `api.md`, no relatório dos pais esse teste aparece só com os valores.
- Atletas inativos ficam fora, a não ser que se ligue *Incluir atletas inativos*.

## Cuidado com os dados

A tela mostra nome e resultados de menores de idade, e quem abre usa o login do `.env`, sem digitar senha. Por isso ela só atende nesta máquina (`server.address = "localhost"`, em `.streamlit/config.toml`). **Não publique este app em um servidor ou no Streamlit Cloud sem antes colocar um login por usuário.**
