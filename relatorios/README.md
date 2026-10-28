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
   - para o lote: `EMAIL_LOTE_TESTE` (quem recebe tudo no modo teste; precisa estar em `EMAILS_TESTE`), `SUPABASE_DB_URL`, `SUPABASE_URL` e `SUPABASE_SECRET_KEY`
3. Instale as dependências: `pip install -r relatorios/requirements.txt -r gerador_pkz/requirements.txt`
4. Uma vez por projeto Supabase, crie a tabela de envios: `backend/sql/07_trat_envio_relatorio.sql`.

O e-mail, a senha de app e as chaves ficam só no `.env` e nos segredos do GitHub, nunca no código.

## Testar o envio de um PDF

Na raiz do repositório, gere o PDF de exemplo (dados fictícios) e mande para todos os e-mails de `EMAILS_TESTE`:

```bash
python gerador_pkz/gerar_pdf.py
python relatorios/enviar_email.py
```

Para mandar outro PDF: `python relatorios/enviar_email.py caminho/do/arquivo.pdf`.

## Envio automático (`enviar_lote.py`)

```bash
python relatorios/enviar_lote.py --periodo mensal --referencia 2026-08-26 --simular
python relatorios/enviar_lote.py --periodo mensal --referencia 2026-08-26 --limite 3
```

- `--periodo`: `semanal` (segunda a domingo), `mensal` ou `anual`.
- `--referencia`: qualquer dia do período, `AAAA-MM-DD`. Sem ela, usa ontem (fuso de São Paulo): o agendamento de segunda manda a semana anterior, o do dia 1º o mês anterior e o de 1º de janeiro o ano anterior. O banco tem dados até agosto de 2026, então teste com `2026-08-26`.
- `--simular`: só lista quem receberia, sem guardar, enviar nem registrar.
- `--limite N`: para depois de N envios.

Para cada aluno das duas unidades (`novo.vw_aluno`):

1. pula quem já recebeu este período (`trat.envio_relatorio`);
2. gera o PDF; aluno sem dados no período é pulado;
3. guarda o PDF no bucket privado `relatorios`, em `teste/<unidade>/<periodo>/<inicio>/<aluno_id>.pdf`;
4. envia por e-mail e registra o envio.

Erro em um aluno não para os outros: o lote mostra o erro, segue e termina com código 1. Quem não foi registrado é tentado de novo na próxima execução. O envio de teste é registrado separado (`teste = true`), então não impede o envio real do mesmo período.

**Gerador provisório:** até o gerador do Henrique aceitar período e unidade (31/10), aluno da PKZ com avaliação no período recebe o PDF de exemplo, e o One to One é pulado (ainda não tem gerador). A troca é só na função `gerar_relatorio()` do `enviar_lote.py`.

### Agendamento (GitHub Actions)

`.github/workflows/relatorios.yml` roda às 8h de Brasília: semanal toda segunda, mensal todo dia 1º e anual em 1º de janeiro. Também tem disparo manual (*Actions → Relatórios por e-mail → Run workflow*), em que se escolhe o período e a data de referência.

- O GitHub só agenda e mostra o disparo manual com o workflow na branch padrão (`main`).
- Segredos do repositório (*Settings → Secrets and variables → Actions*, quem cadastra é o Pedro): `SUPABASE_DB_URL`, `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `EMAIL_USUARIO`, `EMAIL_SENHA_APP`, `EMAILS_TESTE` e `EMAIL_LOTE_TESTE`.
- Em `SUPABASE_DB_URL`, use a string do **Session pooler** (*Connect* no painel do Supabase). A conexão direta (`db.<ref>.supabase.co`) só tem IPv6, que o GitHub Actions não alcança.

## Textos dos e-mails

Ficam em `TEXTOS`, no `enviar_email.py`, e `montar_texto(unidade, nome, periodo, rotulo)` devolve o assunto e o corpo prontos (`periodo`: semanal, mensal ou anual; `rotulo`: o período por extenso, como "agosto de 2026", que vai no assunto).

- **PKZ** (para os pais): relatório de evolução nos testes físicos, avisando que resultados em validação não entram nos gráficos.
- **One to One** (para o aluno): relatório de treinos com histórico, cargas e progressão.
