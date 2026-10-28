# Relatórios: envio por e-mail

`enviar_email.py` manda um relatório em PDF anexo pelo SMTP do Gmail (`smtp.gmail.com`, porta 465, SSL). É o primeiro passo do envio automático: a tarefa seguinte chama `enviar_email(destinatario, assunto, corpo, caminho_pdf)` para cada aluno.

## Modo teste

A função só envia para os e-mails de `EMAILS_TESTE` (os do grupo). Qualquer outro destinatário é recusado com um aviso, e nenhum endereço do banco é usado até a PKZ autorizar. Hoje nenhum aluno da cópia tem e-mail cadastrado, então o envio é demonstrado só com e-mails de teste.

## Configurar

1. Conta Gmail do projeto com verificação em duas etapas ligada e uma **senha de app** (Conta Google → Segurança → Verificação em duas etapas → Senhas de app).
2. No `backend/.env` (modelo em `backend/env.example`), preencha:
   - `EMAIL_USUARIO`: o endereço da conta do projeto
   - `EMAIL_SENHA_APP`: a senha de app (com ou sem espaços)
   - `EMAILS_TESTE`: os e-mails do grupo que podem receber, separados por vírgula
3. Instale as dependências: `pip install -r relatorios/requirements.txt`

O e-mail e a senha de app ficam só no `.env`, nunca no código nem no GitHub.

## Testar

Na raiz do repositório, gere o PDF de exemplo (dados fictícios) e mande para todos os e-mails de `EMAILS_TESTE`:

```bash
pip install -r gerador_pkz/requirements.txt
python gerador_pkz/gerar_pdf.py
python relatorios/enviar_email.py
```

Para mandar outro PDF: `python relatorios/enviar_email.py caminho/do/arquivo.pdf`.

## Textos dos e-mails

Ficam em `TEXTOS`, no `enviar_email.py`, e `montar_texto(unidade, nome, periodo)` devolve o assunto e o corpo prontos (`periodo`: semanal, mensal ou anual).

- **PKZ** (para os pais): relatório de evolução nos testes físicos, avisando que resultados em validação não entram nos gráficos.
- **One to One** (para o aluno): relatório de treinos com histórico, cargas e progressão.
