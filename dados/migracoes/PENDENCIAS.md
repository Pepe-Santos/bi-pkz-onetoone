# Pendências e decisões em aberto

Dúvidas de regra de negócio não são decididas pelo grupo: o registro entra com `pendencia` e a dúvida fica aqui até alguém com autoridade responder. Ao fechar uma, anote quem decidiu e quando.

| # | Pendência | Quem decide | Afeta | Status |
|---|---|---|---|---|
| 1 | Convenção `profissional.id` = `profiles.id` | Micael | 20, 60, 70, 80 | **fechada em 13/10** (ver Decididas) |
| 2 | Unidade e faixa válida de cada teste físico; regra para as alturas ambíguas (metros × centímetros); unidade das medidas posturais e da força abdominal da fisio PKZ | Coordenação técnica esportiva (fisio para as de fisioterapia) | 60, 70 | aberta |
| 3 | Unidade e direção desejada do `slalom_wallball` | Coordenação técnica esportiva | 60 | aberta |
| 4 | Onde ficam CPF, e-mail, endereço, telefone, profissão e sexo da fisio, ou se são descartados | Direção | 70 | aberta |
| 5 | Quem pode ver anamnese e dado clínico | Direção, com respaldo jurídico | 70, 80 (políticas RLS) | aberta |
| 6 | Migrar ou não `notifications` | Grupo, validar com o cliente | 80 | proposta: não migrar |
| 7 | Nome do schema definitivo no projeto separado (`novo` é provisório) e quem cria esse projeto | Grupo + coordenação | todos | aberta |
| 8 | Grade de horários reconstruída das regras do app (horários por serviço e unidade, capacidade 10 no sábado 08:00, fisio/nutri/psico compartilhadas entre as unidades) | Coordenação (via Rafael, 2.5) | 40 | aberta (14/10) |
| 9 | Planos: `plan_monthly_fisio` é mensal, mas o comentário fala em sessões por semana; quantidade de créditos do PKZ (`monthly_credits`); `one_power_legacy` ainda é vendido? | Comercial / direção | 10, 30 | aberta (14/10) |
| 10 | Admins que aparecem como professor/avaliador (46 agendamentos, 62 relatórios, 2 testes, 2 avaliações de fisio): são profissionais de fato ou o registro foi feito em nome de alguém? | Coordenação | 20, 40, 50, 60, 70 | aberta (14/10); entram como `profissional` com pendência |
| 11 | Auditoria: tirar nome, telefone e login (`username`) do `payload` (proposta do mapeamento) ou guardar com acesso restrito | Frente 3 (Iago, 3.2) | 80 | aberta (14/10) |
| 12 | Agendamentos de especialista: 69/69 sem profissional na origem (15 recuperáveis pela evolução) e 11 com presença sem registro de atendimento — é assim mesmo? | Coordenação (via Rafael, 2.5) | 40, 70 | aberta (15/10); os 11 entram marcados 'realizado sem registro de atendimento' (16/10) |
| 13 | Saldo de créditos: 3 alunos com saldo guardado diferente do calculado pelo extrato (2 em fisio, 1 em nutri). A carga não corrige: marca 'ajuste de saldo pendente' na matrícula. Qual vale? (são 3 dos 318 pares aluno × serviço, todos sem renovação identificável pelo texto; comparação com a conferência da 2.1 em `mapeamento/README.md`) | Comercial / coordenação | 30 | aberta (15/10) |
| 14 | 2 agendamentos acima da capacidade do horário (pico no intervalo) e 19 relatórios de treino duplicados para o mesmo agendamento: manter os dois, ou um deles deve ser descartado? | Coordenação (via Rafael, 2.5) | 40, 50 | aberta (15/10); entram com pendência |
| 15 | Papel `professor` sem sufixo (1 usuário na foto): vale para as duas unidades (como está na carga) ou deveria ser de uma só? Os demais papéis globais estão explicados em `mapeamento/README.md` ("Papéis e unidade") | Coordenação (via Rafael, 2.5) | 20 | aberta (21/10); entra com `unidade_id` nula (todas) |

## Decididas

| Decisão | Quem | Quando |
|---|---|---|
| Destino definitivo é um projeto Supabase separado do app | Micael | 12/10/2026 |
| Ensaio roda na cópia do Dev Lucas (com o ok dele), lendo da foto `origem` e gravando em `novo`; `public` não é tocado | Micael | 12/10/2026 |
| Scripts leem de `origem.`, não de `public.` | Micael | 12/10/2026 |
| `profissional.id` = `profiles.id` (pendência 1); no DDL, `profissional.id` é FK para `perfil_usuario.usuario_id` | Micael | 13/10/2026 |
| Agenda segue o conceitual: profissional, data e hora ficam no `agendamento`; `sessao_treino` é a realização 1:1; capacidade conferida por trigger. Sem tabela `sessao` agrupadora (a proposta tinha) | Micael | 13/10/2026 |
| Arquivo segue o conceitual: `arquivo` com FKs reais (`aluno_id` + no máximo um entre `relatorio_id`, `avaliacao_id`, `atendimento_id`). Sem `arquivo_vinculo` | Micael | 13/10/2026 |
| As 4 tabelas criadas fora das migrations em `novo` (unidade, servico, plano, plano_beneficio, id bigint) foram renomeadas para `avulsa_*` (não apagadas) e recriadas no padrão pelo 002/003; os dados voltam pelo script 10. **Falta apagar as `avulsa_*`** quando o grupo confirmar (desde 16/10 estão dentro de `novo_pre_ensaio_geral`) | Micael | 13/10/2026 |
| Ensaio geral sem apagar nada: o `novo` antigo foi renomeado para `novo_pre_ensaio_geral` e o novo foi recriado do zero pelas migrations. **Falta apagar `novo_pre_ensaio_geral`** pelo SQL Editor quando o grupo confirmar | Micael | 16/10/2026 |

## Escolhas do DDL para a Frente 2 revisar (2.2)

Não são regra de negócio, mas mudam o que a proposta de 16/09 dizia. Cada uma está explicada no cabeçalho da migration.

| Escolha | Onde |
|---|---|
| Aluno sem `unidade_id`: a unidade vem da matrícula (`novo.unidade_atual_do_aluno`) | 002, 003 |
| Papel é catálogo (`papel`) + `papel_usuario` com unidade e `desde` | 002 |
| E-mail fica no `perfil_usuario`; `pessoa.cpf` existe mas não é carregado (pendência 4) | 002 |
| `renovacao` é tabela (conceitual) e os lançamentos apontam para ela | 003 |
| Anamnese é uma por avaliação de fisio (o conceitual previa uma por aluno; há um aluno com duas). A vigente sai de `vw_anamnese_vigente` | 007 |
| `exercicio`/`relatorio_exercicio` não foram criados (fora do conceitual, origem vazia) | 005 |
| `configuracao_unidade` e `aluno_servico` foram criadas (fora do conceitual, necessárias para app_settings e allowed_services) | 002 |
| `notificacao`, `consentimento`, `relatorio_emissao`, `relatorio_envio`, `acesso_dado_sensivel`: só estrutura | 008 |
| Avaliação de fisioterapia é um `tipo` de `avaliacao` (o conceitual só especializa em física e semanal): as medidas de goniometria/força/postura são MEDIDAs | 006 |
| Grade compartilhada: `horario_grade.unidade_id` nulo para fisio, nutri e psico ("oferece" é 1,1 no conceitual; no app a vaga é uma só para as duas unidades) | 009 |
| `lista_espera` existe (fora do conceitual, veio da proposta; origem vazia) | 004 |
| Cardinalidades (1,1) relaxadas para nulo: `avaliacao.avaliador_id` (semanal não tem avaliador), `evento_auditoria.ator_id` (23 eventos de sistema sem ator), `horario_grade.unidade_id` (grade compartilhada) | 006, 008, 009 |
| Capacidade conferida no intervalo inteiro do agendamento (mais rígido que o app, que só olha o início) — decidido por Micael em 15/10 | 009 |
| Dado clínico em `avaliacao`/`atendimento` sem coluna `confidencialidade` (filtro por tipo/serviço) — exceção decidida por Micael em 15/10, ver CONVENCOES §7 | 006, 007 |
| Anamnese e arquivo ligados a uma avaliação consolidada continuam editáveis (só a avaliação e suas medidas são imutáveis) | 006–008 |
| **Créditos não são cumulativos**: a renovação redefine o saldo (no app, `run_daily_renewal` faz `credits = cota` e grava `delta = cota`). `vw_saldo_credito` soma só os lançamentos desde a última renovação do serviço (inclusive). Com isso o saldo bate em 106/106 (treino), 104/106 (fisio) e 105/106 (nutri) | 011 |
| Medidas abaixo de 10 em single/cross hop e na distância do VO2 entram com pendência 'unidade não confirmada' (limiar provisório até a pendência 2) — decidido por Micael em 15/10 | mapeamento 60 |
