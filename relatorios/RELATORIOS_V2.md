# Relatórios v2 — PKZ e One to One

Relatório semanal com **até 3 páginas**, mensal com **até 4** e anual com **até 5**, sempre em A4 vertical. Blocos sem dado saem do relatório e as partes que sobram são reagrupadas, então um relatório com pouco dado pode ter menos páginas. O gerador confere o resultado antes de gravar o PDF.

Código: `gerador_pkz/v2/` (contrato, fontes, indicadores, gráficos, páginas, render) e `templates/v2/relatorio.html`.

## Regra principal: só dados reais

- Todo número sai de um **contrato de dados** (JSON) e é calculado em `indicadores.py`. Não há número escrito no código nem nos modelos.
- Sem informação, o relatório diz por quê. Nunca troca a falta de dado por zero.

| Estado | Quando aparece |
|---|---|
| **0** | O resultado real é zero (ex.: nenhuma falta com chamada registrada). |
| **Sem registro** | Não existe informação no sistema para aquele indicador no período. |
| **Regra em validação** | `confirmado = false` na API: a PKZ ainda não validou a regra do teste. O valor e a variação aparecem, mas sem dizer se melhorou ou piorou (contrato da API, `backend/docs/api.md`). |
| **Não se aplica** | O indicador não faz sentido no contexto. |

- Um bloco sem dado vira um painel que explica o que falta. As linhas de texto e esses painéis usam só a altura de que precisam, e o resto da folha vai para os gráficos e as tabelas.
- **Redimensionamento**:
  - cada gráfico tem uma altura mínima (para continuar legível) e uma máxima (para não virar espaço vazio). Uma rosca fica entre 230 e 300 px; barras por teste ganham de 18 a 30 px por item;
  - quando um bloco sai por falta de dado, o que sobra não estica até encher a folha: se a próxima parte não cabe, o gerador traz para cima uma parte da página seguinte que caiba (nunca a conclusão, que fica sempre no fim);
  - tabela que escondia linhas ("+N registros") usa o espaço que sobrar na folha;
  - as quebras entre folhas são escolhidas para deixar o mínimo de espaço em branco (a ordem das partes fica);
  - a **folha de conclusão nunca termina com espaço em branco**:
    - primeiro, ela pode receber uma parte com gráfico de uma folha anterior (nunca da primeira), colocada antes dos pontos positivos e de atenção, quando isso a enche com dados reais;
    - o que ainda sobrar vai para os blocos de texto, lista e tabela dela (nunca para gráficos), e o texto amplia até 30% e se distribui na altura;
  - tabelas contam com todas as linhas (até 60% da folha) na hora de dividir as folhas, para não esconder registros;
  - nenhuma folha repete o título de outra.
- Textos de demonstração gravados na base (ex.: "Dado fictício de demonstração…") são descartados na leitura e contam como *sem registro*.

## Cartão do atleta (página 1)

O mesmo card do dashboard, ao lado do resumo do período. Mostra foto, nota ("over"), nível com metal, nome, idade e os atributos.

- **PKZ**:
  - cada atributo é o percentil (0 a 99) do último resultado, entre o atleta e os colegas da mesma faixa de idade, com pelo menos 5 no grupo;
  - a **nota** é a média dos atributos, sem a simetria, e precisa de 2 ou mais atributos;
  - o nível e o metal seguem a faixa da nota (E e D bronze, C prata, B ouro, A preto);
  - os atributos de cada modalidade vêm de `frontend/catalogo_atributos.json`; sem modalidade, valem os atributos gerais (VEL, POT, AGI, RES, MOB, SIM);
  - a simetria abaixo de 90 aparece em vermelho;
  - a nota é provisória, como no dashboard.
- **One to One**: usa os atributos da modalidade, iguais aos do dashboard (`ONE_TO_ONE` no catálogo):
  - **FIN** força de inferiores (cadeira isométrica), **RES** resistência (VO2, distância total), **POT** potência (salto com contramovimento), **FSU** força de superiores (flexão de braços), **COR** core (prancha ventral) e **MOB** mobilidade (banco de Wells);
  - cada um é o percentil entre o aluno e os colegas do One to One da mesma faixa de idade, com pelo menos 5 no grupo, e a **nota** é a média deles (com 2 ou mais);
  - as avaliações físicas do One to One só alimentam o cartão: o relatório continua precisando de chamada ou treino no período.
- **One to One sem testes físicos** (hoje a API não tem nenhum para os 74 alunos): enquanto não houver 2 atributos da modalidade, o cartão usa atributos de acompanhamento, que saem da chamada e dos treinos do período, de 0 a 100. A troca para os atributos da modalidade acontece sozinha quando os testes entrarem na API.
  - **FRQ** frequência = presenças ÷ (presenças + faltas);
  - **CON** constância = semanas com presença ÷ semanas com chamada, só com 2 ou mais semanas com chamada;
  - **REG** treinos registrados = relatórios de treino ÷ presenças, no máximo 100;
  - **INT** intensidade = média da intensidade registrada (leve 33, moderada 66, alta 100);
  - atributo abaixo de 50 aparece em vermelho.
- **Foto**:
  - o `exportar-api` (e o envio em lote, que usa o mesmo caminho) põe a foto sozinho: procura `<atleta_id>.jpg`, `.jpeg`, `.png` ou `.webp` na pasta de fotos;
  - a pasta é a de `--fotos`, ou a da variável `PKZ_FOTOS`, ou `dados-reais/fotos/` do repositório. As três ficam fora do Git: fotos de alunos nunca vão para o GitHub;
  - a foto é embutida no PDF; o arquivo do aluno não precisa estar junto do relatório depois;
  - com `PKZ_FOTOS_ILUSTRATIVAS=1` (por exemplo, fotos geradas por IA para demonstração), o card avisa "Foto ilustrativa";
  - num contrato montado à mão, a foto vai em `aluno.foto` (caminho do arquivo) e `aluno.foto_ilustrativa`;
  - sem foto, aparecem as iniciais.

## Cálculos

- **Frequência** = presenças ÷ (presenças + faltas) × 100. Cancelada não é falta e agendada não é presença. Sem chamada no recorte, a frequência fica *sem registro*, nunca 0%.
- **Variação %** = (atual − anterior) ÷ anterior × 100.
  - Cada teste e cada lado é comparado só com a sua própria medição anterior.
  - Em contagem pequena (anterior inteiro menor que 5, ex.: de 1 para 0 desequilíbrios) não há %: vale o "de X para Y".
- **Situação**: melhorou ou piorou conforme `maior_melhor`. Num teste de tempo, valor menor é melhor. Abaixo de 2% de diferença, o teste é estável.
- **Anual**: compara a primeira e a última medição do ano.
  - Ano com registros em menos de 12 meses ganha um aviso e não é tratado como ano completo.
  - Tendência só aparece com 3 ou mais meses com chamada.
  - A comparação entre trimestres só aparece com 2 ou mais trimestres com chamada.
- **Posição no grupo**: percentil entre colegas da mesma faixa de idade, sem nomes.
  - Só é calculada com 5 ou mais colegas no mesmo teste, e só para testes com a regra validada.
- **Reavaliação**: a situação é a do fim do período do relatório, não a do dia em que ele é gerado.

## Contrato de dados

```json
{
  "versao": 1,
  "modalidade": "PKZ | ONE_TO_ONE",
  "tipo_relatorio": "semanal | mensal | anual",
  "periodo": {"inicio": "AAAA-MM-DD", "fim": "AAAA-MM-DD"},
  "aluno": {"id": null, "nome": "", "data_nascimento": null, "idade": null, "categoria": null,
            "modalidade": null, "clube": null, "turno": null},
  "sessoes": [{"data": "AAAA-MM-DD", "hora_inicio": "HH:MM", "status": "presente | falta | cancelado | agendado"}],
  "avaliacoes": [{"avaliacao_id": "", "data_avaliacao": "", "teste": "", "teste_nome": "", "lado": "dir | esq | null",
                  "unidade_medida": "", "maior_melhor": true, "confirmado": true, "valor": 0}],
  "treinos": [{"data": "", "tipo_treino": null, "intensidade": null, "objetivos": null, "desempenho": null, "observacoes": null}],
  "grupo": {"descricao": "", "avaliacoes": [{"aluno": "colega-1", "teste": "", "lado": null, "data_avaliacao": "", "valor": 0,
                                             "confirmado": true, "maior_melhor": true}]},
  "reavaliacao": {"ultima_avaliacao_em": "", "vence_em": "", "situacao": ""},
  "observacoes": null
}
```

Como os blocos do pedido se encaixam no contrato:

| Bloco do pedido | Campo do contrato |
|---|---|
| Registros de sessões, presenças e faltas | `sessoes` (o `status` de cada uma) |
| Avaliações e resultados | `avaliacoes` |
| Tipos de treinamento, intensidades, objetivos e desempenho | `treinos` |
| Observações | `observacoes` |

Registros de antes do período podem ir junto. Eles servem de histórico: medição anterior, período anterior e evolução.

**A validação bloqueia o PDF** quando encontra:
- período que não é completo (semana de segunda a domingo, mês do dia 1 ao último dia, ano civil);
- data inválida;
- status desconhecido;
- presença ou avaliação numa data futura;
- valor não numérico;
- o mesmo teste com unidades diferentes;
- nenhum registro no período.

**Avisos** (o PDF sai mesmo assim):
- registro repetido, contado uma vez só;
- sessão passada que ficou como agendada;
- período ainda em andamento;
- ano com registros em poucos meses.

## Comandos

Rode na raiz do repositório, com as dependências de `gerador_pkz/requirements.txt` e o Chromium do Playwright (`python -m playwright install chromium`).

```bash
python -m gerador_pkz.v2 alunos --modalidade PKZ --env frontend/dashboard_atleta/.env
python -m gerador_pkz.v2 exportar-api --modalidade PKZ --aluno <atleta_id> --tipo mensal --referencia 2026-08-15 --saida dados-reais/contrato.json --ficha "dados-reais/Ficha Matrícula_PKZ.csv.zip" --env frontend/dashboard_atleta/.env
python -m gerador_pkz.v2 validar dados-reais/contrato.json
python -m gerador_pkz.v2 gerar dados-reais/contrato.json --saida relatorios/saida --previas relatorios/saida/previas
python -m gerador_pkz.v2 modelo --modalidade ONE_TO_ONE --tipo semanal --saida dados-reais/contrato.json
python -m gerador_pkz.v2 importar-csv --pasta dados-reais/csv --modalidade ONE_TO_ONE --tipo semanal --referencia 2026-08-19 --nome "Nome" --saida dados-reais/contrato.json
```

- **`--env`**: aceita o `.env` do backend (`SUPABASE_SECRET_KEY`) ou o do dashboard (login de teste). As credenciais nunca vão para o contrato.
- **`--fotos`**: pasta das fotos dos alunos, com o nome do arquivo igual ao `atleta_id` (padrão: `dados-reais/fotos/`).
- **`--ficha`**: completa nascimento, modalidade, clube e turno quando o nome bate exatamente com o da ficha.
  - Lê só essas colunas. CPF, endereço, telefone, e-mail e responsável são descartados na leitura.
  - Nome repetido na ficha não é usado.
- **`importar-csv`**: lê `sessoes.csv`, `avaliacoes.csv` e `treinos.csv`, com os nomes dos campos do contrato no cabeçalho.
- **Onde guardar**: `dados-reais/` e `relatorios/saida/` estão no `.gitignore`. Contratos e PDFs têm nomes de menores e não vão para o GitHub.

## Conferência automática

Antes de gravar o PDF, o gerador confere:
- que a quantidade de folhas não passa do máximo do tipo;
- que nenhum bloco tem conteúdo maior que o seu espaço, na altura ou na largura;
- que nenhum gráfico sai do bloco e que nenhum texto é cortado sem reticências.

Se algo falhar, o PDF não é gravado e o erro diz a folha e o bloco.

O arquivo `tests/test_relatorios_v2.py` cobre:
- as 18 combinações de unidade, tipo e volume (mínimo, só avaliação ou só treino, cheio);
- a validação;
- os cálculos (frequência, teste de tempo, contagem pequena, regra em validação, mínimo do grupo);
- a leitura segura da ficha.

## O que os dados reais mostram hoje (17/11/2026)

- **One to One**:
  - nenhuma avaliação física na API (o cartão usa os atributos de acompanhamento até os testes entrarem);
  - `tipo_treino` e `objetivos` vazios em todos os treinos;
  - `desempenho` e `observacoes` trazem o texto "Dado fictício de demonstração", que o relatório trata como *sem registro*.
- **PKZ**:
  - a chamada vai só de 29/07 a 27/08/2026;
  - a maioria dos testes está com a regra em validação (`confirmado = false`), então os resultados aparecem sem dizer se melhorou ou piorou.
- **Ficha de matrícula** (36 alunos): nenhum nome bate com os atletas da PKZ na API. A identificação usa só os dados da API até as duas bases terem os mesmos alunos.
- **Relatórios anuais**: com dados de 1 ou 2 meses, várias análises do ano (tendência, trimestres, início e fim do ano) aparecem como painel explicativo. Elas se preenchem sozinhas quando houver mais meses registrados.
