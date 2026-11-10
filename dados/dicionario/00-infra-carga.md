# Infraestrutura de carga

> Dicionário de dados do schema `novo` · migration 001 · gerado por `dicionario/gerar_dicionario.py`.

Sensibilidade: `clinico` (dado de saúde), `pessoal` (identifica alguém), `operacional` (rotina do negócio), `tecnico` (controle da carga).

## `carga_execucao`

Linhas no ensaio de 12/10: **16**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | bigint | sim | PK | — |  |  | tecnico | Chave primária. |
| `script` | text | sim |  | — |  |  | tecnico | Nome do domínio do script de carga que gerou a linha. |
| `linhas_carregadas` | integer | não |  | — |  |  | tecnico | [revisar] |
| `linhas_rejeitadas` | integer | não |  | — |  |  | tecnico | [revisar] |
| `observacao` | text | não |  | — |  |  | tecnico | Texto livre escrito por quem registrou. |
| `executado_em` | timestamp with time zone | sim |  | — | padrão now() |  | tecnico | Data e hora do evento que o nome indica. |

## `carga_rejeitado`

Linhas no ensaio de 12/10: **0**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `id` | bigint | sim | PK | — |  |  | tecnico | Chave primária. |
| `script` | text | sim |  | — |  |  | tecnico | Nome do domínio do script de carga que gerou a linha. |
| `tabela_origem` | text | sim |  | — |  |  | tecnico | Tabela da origem que gerou a linha. |
| `id_origem` | uuid | não |  | — |  |  | tecnico | Id da linha na origem, usado para reexecutar a carga sem duplicar. |
| `motivo` | text | sim |  | — |  |  | tecnico | [revisar] |
| `registrado_em` | timestamp with time zone | sim |  | — | padrão now() |  | tecnico | Data e hora do evento que o nome indica. |

## `carga_gabarito`

Linhas no ensaio de 12/10: **28**

| Coluna | Tipo | Obrig. | Chave | Origem | Transformação | Valores de hoje | Sensib. | Significado |
|---|---|---|---|---|---|---|---|---|
| `rotulo` | text | sim | PK | — |  |  | tecnico | [revisar] |
| `tabela` | text | sim | PK | — |  |  | tecnico | [revisar] |
| `linhas` | bigint | sim |  | — |  |  | tecnico | [revisar] |
| `registrado_em` | timestamp with time zone | sim |  | — | padrão now() |  | tecnico | Data e hora do evento que o nome indica. |
