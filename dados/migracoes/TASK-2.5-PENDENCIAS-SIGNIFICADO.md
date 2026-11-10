# Registro da Task 2.5 - pendencias de significado

Este documento registra a auditoria tecnica e as propostas operacionais provisorias da Task 2.5. Ele e um registro exclusivo desta tarefa e nao substitui o registro oficial da Frente 1 nem encerra qualquer decisao de negocio, tecnica ou de aprovacao.

## Escopo da auditoria

A auditoria revisou as pendencias de significado relacionadas a metricas de avaliacao e ao tratamento de `notifications`, com foco nas pendencias #2, #3 e #6. Foram usadas como evidencia as tabelas de mapeamento e os artefatos SQL ja existentes no repositorio; nenhuma alteracao de migration, carga SQL, catalogo ou codigo e proposta por este registro.

## Pendencia #2 - unidades, faixas e alturas

- Usar o catalogo de metricas existente como referencia inicial para unidades e direcoes ja identificadas.
- Nao inventar unidades nem limites minimo/maximo. Valores fora de faixas plausiveis devem ser encaminhados para revisao.
- Converter alturas somente quando a unidade puder ser identificada com seguranca.
- Preservar o valor original e, quando houver suporte estrutural, registrar separadamente a conversao e a regra aplicada.
- Nao inferir unidade apenas por um limite numerico arbitrario. Valores ambiguos devem permanecer sinalizados para revisao e fora dos indicadores de evolucao ate esclarecimento.
- A validacao tecnica das unidades e faixas oficiais continua pendente.

## Pendencia #3 - `slalom_wallball`

- Nao presumir o significado funcional, a unidade ou a direcao desejada da metrica.
- Manter a metrica identificada no catalogo, mas fora dos indicadores de evolucao enquanto esses parametros estiverem indefinidos.
- Para liberar o uso, ainda sao necessarias descricao funcional, metodo de calculo, unidade, direcao desejada e faixa plausivel, quando aplicavel.
- A definicao esportiva continua pendente.

## Pendencia #6 - `notifications`

- A proposta operacional e manter as notificacoes fora da carga analitica inicial.
- Nao excluir dados da origem nem executar operacao destrutiva por causa dessa proposta.
- Ficar fora da carga inicial nao autoriza descartar o historico.
- A decisao de preservar ou migrar as notificacoes continua pendente de aprovacao de negocio do grupo ou do cliente.

## Resultado da comparacao e da auditoria

- A comparacao entre `mapeamento/avaliacao_metricas.csv` e o catalogo SQL encontrou equivalencia nos 109 pares ordem/codigo.
- Nao foram identificadas divergencias nem ordens duplicadas nessa comparacao.
- A carga preserva alturas sem conversao automatica e sinaliza a ambiguidade de unidade.
- `slalom_wallball` permanece identificada sem unidade ou direcao inventadas.
- `notifications` permanece fora da carga analitica inicial, sem operacao destrutiva sobre a origem.
- Nao foram identificadas alteracoes de codigo necessarias sem definicoes tecnicas adicionais.

## Limitacoes e pendencias remanescentes

- As propostas sao provisorias e nao encerram as pendencias #2, #3 ou #6.
- A validacao das unidades, faixas e regras esportivas depende das definicoes tecnicas e de negocio ainda nao fornecidas.
- A decisao final sobre preservar ou migrar `notifications` depende do grupo ou do cliente.
- Valores ambiguos continuam exigindo revisao antes de serem usados em indicadores de evolucao.
- A homologacao do modelo no marco M2 continua pendente conforme a documentacao existente.
