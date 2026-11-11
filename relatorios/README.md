# Relatórios: envio por e-mail

- `enviar_email.py` manda um relatório em PDF anexo pelo SMTP do Gmail (`smtp.gmail.com`, porta 465, SSL), com `enviar_email(destinatario, assunto, corpo, caminho_pdf)`.
- `enviar_lote.py` é o envio automático: gera, guarda e envia o relatório de um período para todos os alunos. Roda sozinho pelo GitHub Actions (`.github/workflows/relatorios.yml`).

## Modo teste

A `enviar_email()` só envia para os e-mails de `EMAILS_TESTE` (os do grupo). Qualquer outro destinatário é recusado com um aviso, e nenhum endereço do banco é usado até a PKZ autorizar. Hoje nenhum aluno da cópia tem e-mail cadastrado, então o lote manda todos os relatórios para `EMAIL_LOTE_TESTE`, com `[TESTE]` e o nome do aluno no assunto.

## Configurar

1. Conta Gmail do projeto com verificação em duas etapas ligada e uma **senha de app** (Conta Google → Segurança → Verificação em duas etapas → Senhas de app).
2. No `backend/.env` (modelo em `backend/env.example`), preencha:
   - `EMAIL_USUARIO`: o endereço da conta do projeto
   - `EMAIL_SENHA_APP`: a senha de app (com ou sem espaços)
   - `EMAILS_TESTE`: os e-mails do grupo que podem receber, separados por vírgula
   - para o lote: `EMAIL_LOTE_TESTE` (quem recebe tudo no modo teste; precisa estar em `EMAILS_TESTE`), `SUPABASE_URL` e `SUPABASE_SECRET_KEY`. O lote não usa a senha do banco: tudo passa pela API do Supabase
3. Instale as dependências: `pip install -r relatorios/requirements.txt -r gerador_pkz/requirements.txt`
4. Uma vez por projeto Supabase, rode `backend/sql/07_trat_envio_relatorio.sql` (tabela de envios) e depois `backend/sql/09_api_envio_relatorio.sql` (funções da API que leem e gravam essa tabela, só com a secret key).

O e-mail, a senha de app e as chaves ficam só no `.env` e nos segredos do GitHub, nunca no código.

## Testar o envio de um PDF

Na raiz do repositório, gere um PDF pela API com um `atleta_id` da view `api.atleta`. A referência define a semana (segunda a domingo), o mês ou o ano-calendário:

```bash
python gerador_pkz/gerar_pdf.py <atleta_id> --periodo semanal --referencia 2026-08-20
python gerador_pkz/gerar_pdf.py <atleta_id> --periodo mensal --referencia 2026-08-20
python gerador_pkz/gerar_pdf.py <atleta_id> --periodo anual --referencia 2026-08-20
python gerador_pkz/gerar_pdf.py <atleta_id> --one-to-one --periodo semanal --referencia 2026-08-20
python gerador_pkz/gerar_pdf.py <atleta_id> --one-to-one --periodo mensal --referencia 2026-08-20
python gerador_pkz/gerar_pdf.py <atleta_id> --one-to-one --periodo anual --referencia 2026-08-20
```

O modo One to One consulta as views `atleta`, `presenca` e `treino`. Os relatórios mostram a presença e os dados de treino disponíveis no período: objetivos, tipo, intensidade e desempenho. No anual, a tabela lista até os 10 treinos mais recentes e informa o total do período. Para gerar e enviar um PDF de teste por e-mail, use:

```bash
python relatorios/enviar_email.py
```

Para gerar um relatório PKZ sem consultar a API, informe uma pasta com `atleta.json` e `evolucao.json`; `presenca.json` é opcional. Os arquivos devem conter listas JSON no formato das views correspondentes. O ID do atleta pode ser omitido para usar o primeiro registro PKZ da amostra:

```bash
python gerador_pkz/gerar_pdf.py --json-dir exemplos/api --periodo mensal --referencia 2026-08-20
```

Os exemplos em `exemplos/api/` são fictícios. O repositório não contém a amostra original do Ewerton; use `--json-dir` com a pasta da amostra válida quando ela estiver disponível.

Para mandar outro PDF: `python relatorios/enviar_email.py caminho/do/arquivo.pdf`.

## Relatórios a partir dos modelos HTML (`--renderizador html`)

Além do gerador ReportLab (padrão), o `gerar_pdf.py` gera os relatórios a partir dos seis modelos HTML oficiais em `templates/`: dados da API → indicadores (`gerador_pkz/contexto_relatorio.py`) → template Jinja2 → Chromium (Playwright) → PDF A4.

```bash
pip install -r gerador_pkz/requirements.txt
python -m playwright install chromium     # uma vez por máquina

python gerador_pkz/gerar_pdf.py <atleta_id> --renderizador html --periodo mensal --referencia 2026-08-20
python gerador_pkz/gerar_pdf.py <atleta_id> --one-to-one --renderizador html --periodo anual --referencia 2026-08-20
python gerador_pkz/gerar_pdf.py --json-dir exemplos/api --renderizador html --periodo anual --referencia 2026-08-20
```

O PDF sai em `gerador_pkz/relatorios/relatorio_html_<unidade>_<atleta>_<periodo>_<data>.pdf`, sem sobrescrever o do ReportLab, para comparar os dois.

- **Templates:** `templates/PKZ_relatorio_{semanal,mensal,anual}.html` e `templates/OneToOne_relatorio_{semanal,mensal,anual}.html` (Jinja2), com cabeçalho e rodapé em `base.html` e componentes em `_macros.html`. Os HTMLs originais aprovados ficam em `templates/referencia/` só para comparação.
- **Offline:** fontes (Inter e Barlow Condensed, em `templates/fonts/`) e logotipos (`templates/assets/`) vão embutidos no HTML; o PDF não depende de internet.
- **Sem dados inventados:** o que o modelo mostrava e a API não tem (nota/nível do atleta, atributos 0–99, PSE, tonelagem, 1RM, composição corporal, mensagem do professor, próximas sessões) não aparece. Blocos sem dado são ocultados; resultados não confirmados aparecem como "Em validação". No One to One não há nenhuma informação de dor.
- **Indicadores:** frequência = presenças ÷ (presenças + faltas); variação = (atual − anterior) ÷ anterior × 100, respeitando `maior_melhor`; só testes medidos dentro do período entram na comparação; no One to One anual, tabela com os 10 treinos mais recentes e total do período.
- **Páginas:** A4, com quebra de página que não corta cartões. Cada modelo é escalado para a largura da folha.

## Testes automatizados do gerador

Instale as dependências de teste e rode a suíte. Os testes usam fixtures sintéticas, mocks da API e PDFs temporários fora do repositório; nenhuma chamada é feita ao Supabase.

```bash
python -m pip install -r requirements-test.txt
python -m pytest
```

## Envio automático (`enviar_lote.py`)

```bash
python relatorios/enviar_lote.py --periodo mensal --referencia 2026-08-26 --simular
python relatorios/enviar_lote.py --periodo mensal --referencia 2026-08-26 --limite 3
```

- `--periodo`: `semanal` (segunda a domingo), `mensal` ou `anual`.
- `--referencia`: qualquer dia do período, `AAAA-MM-DD`. Sem ela, usa ontem (fuso de São Paulo): o agendamento de segunda manda a semana anterior, o do dia 1º o mês anterior e o de 1º de janeiro o ano anterior. O banco tem dados até agosto de 2026, então teste com `2026-08-26`.
- `--simular`: só lista quem receberia, sem guardar, enviar nem registrar.
- `--limite N`: para depois de N envios.

Para cada aluno das duas unidades (`api.atleta`):

1. pula quem já recebeu este período (`trat.envio_relatorio`, pela função `api.relatorios_enviados`);
2. gera o PDF com o `gerador_pkz/gerar_pdf.py`; aluno sem dados no período é pulado;
3. guarda o PDF no bucket privado `relatorios`, em `teste/<unidade>/<periodo>/<inicio>/<aluno_id>.pdf`;
4. envia por e-mail e registra o envio (`api.registrar_envio_relatorio`).

Erro em um aluno não para os outros: o lote mostra o erro, segue e termina com código 1. Quem não foi registrado é tentado de novo na próxima execução. O envio de teste é registrado separado (`teste = true`), então não impede o envio real do mesmo período.

**One to One:** usa o `gerar_relatorio_one_to_one()` do `gerador_pkz/gerar_pdf.py`, chamado pela função `gerar_relatorio()` do `enviar_lote.py`. Aluno sem agendamento nem treino no período é pulado, como na PKZ.

### Agendamento (GitHub Actions)

`.github/workflows/relatorios.yml` roda às 8h de Brasília: semanal toda segunda, mensal todo dia 1º e anual em 1º de janeiro. Também tem disparo manual (*Actions → Relatórios por e-mail → Run workflow*), em que se escolhe o período e a data de referência.

- O GitHub só agenda e mostra o disparo manual com o workflow na branch padrão (`main`).
- Segredos do repositório (*Settings → Secrets and variables → Actions*, quem cadastra é o Pedro): `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `EMAIL_USUARIO`, `EMAIL_SENHA_APP`, `EMAILS_TESTE` e `EMAIL_LOTE_TESTE`.

## Textos dos e-mails

Ficam em `TEXTOS`, no `enviar_email.py`, e `montar_texto(unidade, nome, periodo, rotulo)` devolve o assunto e o corpo prontos (`periodo`: semanal, mensal ou anual; `rotulo`: o período por extenso, como "agosto de 2026", que vai no assunto).

- **PKZ** (para os pais): relatório de evolução nos testes físicos, avisando que resultados em validação não entram nos gráficos.
- **One to One** (para o aluno): relatório de presença e histórico de treinos, com objetivos, tipo, intensidade e desempenho quando registrados.
