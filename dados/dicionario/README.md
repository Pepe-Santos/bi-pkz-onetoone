# Dicionário de dados do schema `novo` (tarefa 3.5)

Para cada tabela e coluna do banco novo: o que é, tipo, se é obrigatória, chave, de onde veio na
origem, como foi transformada, os valores que existem hoje e o nível de sensibilidade.

Gerado por [`gerar_dicionario.py`](gerar_dicionario.py), que junta três fontes: a estrutura lida do
próprio banco, os CSVs de [`../migracoes/mapeamento/`](../migracoes/mapeamento/) (tarefa 1.3) e a
classificação de sensibilidade da Frente 3. Nenhum dado da origem entra aqui: só estrutura, contagem e
lista de valores de coluna categórica.

## Arquivos

| Arquivo | Domínio | Migration |
|---|---|---|
| [00-infra-carga.md](00-infra-carga.md) | Infraestrutura de carga | 001 |
| [01-cadastro.md](01-cadastro.md) | Cadastro e identidade | 002 |
| [02-comercial.md](02-comercial.md) | Comercial e créditos | 003 |
| [03-agenda-treino.md](03-agenda-treino.md) | Agenda e treino | 004 e 005 |
| [04-avaliacao.md](04-avaliacao.md) | Avaliação e testes físicos | 006 |
| [05-atendimento.md](05-atendimento.md) | Atendimento especializado | 007 |
| [06-documentos.md](06-documentos.md) | Documentos, conformidade e comunicação | 008 |

## Cobertura

43 tabelas e 467 colunas, as mesmas do ensaio de 12/10.

| Sensibilidade | Colunas | O que é |
|---|---|---|
| `operacional` | 251 | rotina do negócio: agenda, treino, avaliação, comercial |
| `tecnico` | 149 | controle da carga e colunas padrão (id, datas, pendência) |
| `clinico` | 50 | dado de saúde: anamnese, atendimento, evolução, dor do relatório, confidencialidade |
| `pessoal` | 17 | identifica alguém: nome, cpf, telefone, foto, data de nascimento |

**146 colunas ainda estão como `[revisar]`** na coluna Significado. São as que dependem de quem conhece
a regra de negócio; as colunas de padrão do grupo (id, chaves, datas, pendência) já vêm preenchidas.
A tabela com mais pendência de revisão é a de cadastro (36 colunas).

A classificação de sensibilidade segue o mesmo critério da política de acesso
([`../migracoes/migrations/012_politicas_rls.sql`](../migracoes/migrations/012_politicas_rls.sql)):
`clinico` fecha por padrão, `pessoal` segue o aluno, e as tabelas de controle da carga (`carga_*`)
não são legíveis pela API. A política é por linha; esta classificação é por coluna e serve de guia
para as views do schema `api` (o que não deve aparecer em relatório ou tela).

## Como gerar de novo

Da pasta `dados/migracoes`, como as conferências:

```
# com psql no PATH e a conexão em ENSAIO_URL
python ../dicionario/gerar_dicionario.py

# ou a partir de um JSON exportado antes (formato no fim do script)
python ../dicionario/gerar_dicionario.py --entrada estrutura.json
```

O script só lê. Rodar de novo reescreve os sete arquivos, então a revisão do significado deve ser feita
no próprio texto da coluna Significado — e, quando a frase for definitiva, vale passá-la para o banco
com `comment on column`, que é de onde o gerador lê primeiro.
