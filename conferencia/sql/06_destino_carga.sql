-- Tarefa 2.3 / Conferencias no destino. Somente leitura.

-- 1) Gabarito: um unico congelamento por execucao, sem misturar snapshots.
WITH ultimo_gabarito AS (
  SELECT rotulo FROM novo.carga_gabarito
  ORDER BY registrado_em DESC, rotulo DESC LIMIT 1
), g AS (
  SELECT tabela, linhas FROM novo.carga_gabarito
  WHERE rotulo=(SELECT rotulo FROM ultimo_gabarito)
), r AS (
  SELECT script, tabela_origem, COUNT(*) FILTER (WHERE motivo NOT LIKE 'chave %') rejeicoes_linha
  FROM novo.carga_rejeitado GROUP BY script,tabela_origem
), p(ordem,script,tabela_origem,destino,linhas_destino,modo) AS (VALUES
  (1,'cadastro','profiles','novo.perfil_usuario',(SELECT COUNT(*) FROM novo.perfil_usuario),'VALIDA'),
  (2,'cadastro','athletes','novo.aluno',(SELECT COUNT(*) FROM novo.aluno),'PARCIAL'),
  (3,'comercial','athletes','novo.matricula',(SELECT COUNT(*) FROM novo.matricula),'PARCIAL'),
  (4,'comercial','credit_transactions','novo.credito_lancamento',(SELECT COUNT(*) FROM novo.credito_lancamento),'VALIDA'),
  (5,'agenda','schedule_blocks','novo.bloqueio_agenda',(SELECT COUNT(*) FROM novo.bloqueio_agenda),'VALIDA'),
  (6,'agenda','bookings','novo.agendamento',(SELECT COUNT(*) FROM novo.agendamento),'VALIDA'),
  (7,'agenda','waitlist','novo.lista_espera',(SELECT COUNT(*) FROM novo.lista_espera),'VALIDA'),
  (8,'agenda','training_feedback','novo.feedback_treino',(SELECT COUNT(*) FROM novo.feedback_treino),'VALIDA'),
  (9,'relatorio','training_report_materials','novo.catalogo_item (material)',(SELECT COUNT(*) FROM novo.catalogo_item WHERE dominio='material' AND id_origem IS NOT NULL),'VALIDA'),
  (10,'relatorio','training_report_technologies','novo.catalogo_item (tecnologia)',(SELECT COUNT(*) FROM novo.catalogo_item WHERE dominio='tecnologia' AND id_origem IS NOT NULL),'VALIDA'),
  (11,'relatorio','training_reports','novo.relatorio_treino',(SELECT COUNT(*) FROM novo.relatorio_treino),'VALIDA'),
  (12,'avaliacao','physical_test_sessions','novo.avaliacao (teste_fisico)',(SELECT COUNT(*) FROM novo.avaliacao WHERE tipo='teste_fisico'),'VALIDA'),
  (13,'avaliacao','weekly_evaluations','novo.avaliacao (semanal)',(SELECT COUNT(*) FROM novo.avaliacao WHERE tipo='semanal'),'VALIDA'),
  (14,'atendimento','physio_assessments','novo.avaliacao (fisioterapia)',(SELECT COUNT(*) FROM novo.avaliacao WHERE tipo='fisioterapia'),'PARCIAL'),
  (15,'atendimento','physio_assessments','novo.anamnese',(SELECT COUNT(*) FROM novo.anamnese),'PARCIAL'),
  (16,'atendimento','physio_evolutions','novo.atendimento (fisio)',(SELECT COUNT(*) FROM novo.atendimento a WHERE EXISTS (SELECT 1 FROM origem.physio_evolutions o WHERE o.id=a.id)),'VALIDA'),
  (17,'atendimento','specialist_evolutions','novo.atendimento (especialista)',(SELECT COUNT(*) FROM novo.atendimento a WHERE EXISTS (SELECT 1 FROM origem.specialist_evolutions o WHERE o.id=a.id)),'VALIDA'),
  (18,'documentos','activity_logs','novo.evento_auditoria (activity_logs)',(SELECT COUNT(*) FROM novo.evento_auditoria WHERE tabela_origem='activity_logs'),'VALIDA'),
  (19,'documentos','booking_audit_logs','novo.evento_auditoria (booking_audit_logs)',(SELECT COUNT(*) FROM novo.evento_auditoria WHERE tabela_origem='booking_audit_logs'),'VALIDA')
)
, gabarito AS (
 SELECT EXISTS (SELECT 1 FROM novo.carga_gabarito) AS existe_gabarito,
        (SELECT rotulo FROM ultimo_gabarito) AS rotulo_gabarito
), origem_destinos AS (
 SELECT tabela_origem,COUNT(*) destinos FROM p GROUP BY tabela_origem
)
SELECT gabarito.rotulo_gabarito,
 p.script,p.tabela_origem,p.destino,p.modo,g.linhas linhas_gabarito,p.linhas_destino,
 COALESCE(r.rejeicoes_linha,0) rejeicoes_linha,od.destinos destinos_da_origem,
 CASE WHEN NOT gabarito.existe_gabarito THEN 'GABARITO_INEXISTENTE'
      WHEN g.tabela IS NULL THEN 'SEM_TABELA_NO_GABARITO'
      WHEN od.destinos>1 OR p.modo='PARCIAL' THEN 'INCONCLUSIVO'
      WHEN g.linhas=p.linhas_destino+COALESCE(r.rejeicoes_linha,0) THEN 'OK'
      ELSE 'DIVERGENCIA' END status,
 CASE WHEN od.destinos>1 OR p.modo='PARCIAL'
      THEN 'Uma origem alimenta mais de um destino; a rejeicao nao e atribuida individualmente sem regra de rateio.'
      WHEN NOT gabarito.existe_gabarito THEN 'Nao existe nenhum snapshot em novo.carga_gabarito.'
      WHEN g.tabela IS NULL THEN 'O snapshot selecionado nao possui esta tabela.'
      END observacao
FROM p LEFT JOIN g ON g.tabela=p.tabela_origem
LEFT JOIN r ON r.script=p.script AND r.tabela_origem=p.tabela_origem
JOIN origem_destinos od ON od.tabela_origem=p.tabela_origem
CROSS JOIN gabarito ORDER BY p.ordem;

-- Arquivos: ORIGEM_DERIVADA; a expectativa e COUNT(DISTINCT caminho), nao o gabarito geral.
WITH caminhos AS (
 SELECT NULLIF(BTRIM(storage_path),'') caminho FROM origem.student_files
 UNION SELECT NULLIF(BTRIM(storage_path),'') FROM origem.nutritionist_files
 UNION SELECT NULLIF(BTRIM(storage_path),'') FROM origem.physio_evolutions
 UNION SELECT NULLIF(BTRIM(file_path),'') FROM origem.specialist_evolutions
 UNION SELECT NULLIF(BTRIM(file_path),'') FROM origem.training_reports
 UNION SELECT NULLIF(BTRIM(pdf_storage_path),'') FROM origem.training_reports
 UNION SELECT NULLIF(BTRIM(file_path),'') FROM origem.physical_test_comparisons
 UNION SELECT NULLIF(BTRIM(file_path),'') FROM origem.physio_assessments
 UNION SELECT NULLIF(BTRIM(file_path),'') FROM origem.student_tests
 UNION SELECT NULLIF(BTRIM(v),'') FROM origem.physio_assessments p
   CROSS JOIN LATERAL jsonb_each_text(p.pkz_data) kv(k,v)
   WHERE k ~ '^img_' OR k IN ('carimbo_path','laudo_path')
)
SELECT 'ORIGEM_DERIVADA' origem_da_expectativa,
 'COUNT(DISTINCT caminho) nas colunas de origem documentadas' base_da_expectativa,
 COUNT(*) caminhos_distintos_origem,(SELECT COUNT(*) FROM novo.arquivo) arquivos_destino,
 (SELECT COUNT(*) FROM novo.carga_rejeitado WHERE tabela_origem='arquivo (caminho)') rejeicoes_registradas,
 CASE WHEN COUNT(*)=(SELECT COUNT(*) FROM novo.arquivo)+
   (SELECT COUNT(*) FROM novo.carga_rejeitado WHERE tabela_origem='arquivo (caminho)')
 THEN 'OK' ELSE 'DIVERGENCIA' END status
FROM caminhos WHERE caminho IS NOT NULL;

-- 2) Rejeicoes por script, tabela e motivo.
SELECT script,tabela_origem,motivo,COUNT(*) quantidade
FROM novo.carga_rejeitado GROUP BY script,tabela_origem,motivo ORDER BY script,tabela_origem,motivo;

-- Resumo: ocorrencias, ids nulos, ids distintos e chave % excluida da
-- reconciliacao de linhas conforme a conferencia geral da Frente 1.
SELECT script,tabela_origem,COUNT(*) ocorrencias,
 COUNT(*) FILTER (WHERE id_origem IS NULL) id_origem_nulo,
 COUNT(DISTINCT id_origem) ids_origem_distintos,
 COUNT(*) FILTER (WHERE motivo LIKE 'chave %') ocorrencias_chave_excluidas,
 COUNT(*) FILTER (WHERE motivo NOT LIKE 'chave %') ocorrencias_linha
FROM novo.carga_rejeitado GROUP BY script,tabela_origem ORDER BY script,tabela_origem;

-- 3) Pendencias por tabela real com coluna pendencia. query_to_xml executa SELECTs.
SELECT c.table_name tabela,
 (xpath('/row/n/text()',query_to_xml(format('SELECT COUNT(*) n FROM novo.%I',c.table_name),false,true,'')))[1]::text::bigint total,
 (xpath('/row/n/text()',query_to_xml(format('SELECT COUNT(*) n FROM novo.%I WHERE pendencia IS NOT NULL',c.table_name),false,true,'')))[1]::text::bigint com_pendencia
FROM information_schema.columns c JOIN information_schema.tables t
 ON t.table_schema=c.table_schema AND t.table_name=c.table_name
WHERE c.table_schema='novo' AND c.column_name='pendencia' AND t.table_type='BASE TABLE'
ORDER BY c.table_name;

-- 4) As duas ultimas execucoes por script, com datas explicitas.
WITH scripts(script) AS (VALUES
 ('referencia'),('cadastro'),('comercial'),('agenda'),('relatorio'),('avaliacao'),('atendimento'),('documentos')
), e AS (
 SELECT x.*,COUNT(*) OVER (PARTITION BY script) quantidade_execucoes,
 ROW_NUMBER() OVER (PARTITION BY script ORDER BY executado_em DESC,id DESC) posicao
 FROM novo.carga_execucao x
), ultimas AS (
 SELECT script,quantidade_execucoes,
 MAX(executado_em) FILTER (WHERE posicao=1) ultima_executada_em,
 MAX(executado_em) FILTER (WHERE posicao=2) penultima_executada_em,
 MAX(linhas_carregadas) FILTER (WHERE posicao=1) ultima_linhas_carregadas,
 MAX(linhas_carregadas) FILTER (WHERE posicao=2) penultima_linhas_carregadas,
 MAX(linhas_rejeitadas) FILTER (WHERE posicao=1) ultima_linhas_rejeitadas,
 MAX(linhas_rejeitadas) FILTER (WHERE posicao=2) penultima_linhas_rejeitadas
 FROM e GROUP BY script,quantidade_execucoes
), resumo AS (
 SELECT s.script,COALESCE(u.quantidade_execucoes,0) quantidade_execucoes,
  u.ultima_executada_em,u.penultima_executada_em,u.ultima_linhas_carregadas,
  u.penultima_linhas_carregadas,u.ultima_linhas_rejeitadas,u.penultima_linhas_rejeitadas
 FROM scripts s LEFT JOIN ultimas u USING(script)
)
SELECT script,quantidade_execucoes,ultima_executada_em,penultima_executada_em,
 ultima_linhas_carregadas,penultima_linhas_carregadas,
 ultima_linhas_rejeitadas,penultima_linhas_rejeitadas,
 CASE WHEN quantidade_execucoes<2 THEN 'INCONCLUSIVO'
      WHEN ultima_linhas_carregadas IS NOT DISTINCT FROM penultima_linhas_carregadas
       AND ultima_linhas_rejeitadas IS NOT DISTINCT FROM penultima_linhas_rejeitadas THEN 'IGUAL'
      ELSE 'DIVERGENCIA' END status,
 CASE WHEN quantidade_execucoes>=2 THEN 'DUAS_ULTIMAS' ELSE 'SEM_PENULTIMA' END comparacao
FROM resumo ORDER BY script;

-- 5) Duplicidades conforme unicidades relevantes do DDL.
SELECT 'perfil_usuario.username' chave,username,COUNT(*) quantidade FROM novo.perfil_usuario GROUP BY username HAVING COUNT(*)>1;
SELECT 'pessoa.origem' chave,origem_tabela,origem_id,COUNT(*) quantidade FROM novo.pessoa
WHERE origem_tabela IS NOT NULL AND origem_id IS NOT NULL GROUP BY origem_tabela,origem_id HAVING COUNT(*)>1;
SELECT 'papel_usuario' chave,usuario_id,papel_id,unidade_id,COUNT(*) quantidade FROM novo.papel_usuario
GROUP BY usuario_id,papel_id,unidade_id HAVING COUNT(*)>1;
SELECT 'plano.codigo' chave,codigo,COUNT(*) quantidade FROM novo.plano GROUP BY codigo HAVING COUNT(*)>1;
SELECT 'servico.codigo' chave,codigo,COUNT(*) quantidade FROM novo.servico GROUP BY codigo HAVING COUNT(*)>1;
SELECT 'unidade.codigo' chave,codigo,COUNT(*) quantidade FROM novo.unidade GROUP BY codigo HAVING COUNT(*)>1;
SELECT 'renovacao_chave_constraint' chave,aluno_id,servico_id,periodicidade,competencia,COUNT(*) quantidade
FROM novo.renovacao GROUP BY aluno_id,servico_id,periodicidade,competencia HAVING COUNT(*)>1;
-- Regra adicional de neg?cio mais restritiva que a constraint final.
SELECT 'renovacao_regra_negocio_restritiva' chave,aluno_id,servico_id,competencia,COUNT(*) quantidade
FROM novo.renovacao GROUP BY aluno_id,servico_id,competencia HAVING COUNT(*)>1;
SELECT 'arquivo.storage_path' chave,storage_path,COUNT(*) quantidade FROM novo.arquivo GROUP BY storage_path HAVING COUNT(*)>1;
SELECT 'feedback_treino.agendamento_id' chave,agendamento_id,COUNT(*) quantidade FROM novo.feedback_treino GROUP BY agendamento_id HAVING COUNT(*)>1;
SELECT 'sessao_treino.agendamento_id' chave,agendamento_id,COUNT(*) quantidade FROM novo.sessao_treino GROUP BY agendamento_id HAVING COUNT(*)>1;
SELECT 'agendamento.ativo' chave,aluno_id,servico_id,data,hora_inicio,COUNT(*) quantidade FROM novo.agendamento
WHERE status<>'cancelado' GROUP BY aluno_id,servico_id,data,hora_inicio HAVING COUNT(*)>1;
-- A consulta acima cobre a chave operacional usada para agendamentos ativos;
-- outras regras de sobreposicao nao sao inferidas sem constraint/index no DDL.

-- 6) FKs cobertas. Nulos permitidos/obrigatorios e orfaos sao separados.
SELECT 'aluno.pessoa_id' relacao,COUNT(*) FILTER(WHERE x.pessoa_id IS NULL) nulos_obrigatorios,COUNT(*) FILTER(WHERE x.pessoa_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.aluno x LEFT JOIN novo.pessoa y ON y.id=x.pessoa_id;
SELECT 'aluno_servico.aluno_id' relacao,COUNT(*) FILTER(WHERE x.aluno_id IS NULL) nulos_obrigatorios,COUNT(*) FILTER(WHERE x.aluno_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.aluno_servico x LEFT JOIN novo.aluno y ON y.id=x.aluno_id;
SELECT 'aluno_servico.servico_id' relacao,COUNT(*) FILTER(WHERE x.servico_id IS NULL) nulos_obrigatorios,COUNT(*) FILTER(WHERE x.servico_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.aluno_servico x LEFT JOIN novo.servico y ON y.id=x.servico_id;
SELECT 'papel_usuario.usuario_id' relacao,COUNT(*) FILTER(WHERE x.usuario_id IS NULL) nulos_obrigatorios,COUNT(*) FILTER(WHERE x.usuario_id IS NOT NULL AND y.usuario_id IS NULL) orfaos FROM novo.papel_usuario x LEFT JOIN novo.perfil_usuario y ON y.usuario_id=x.usuario_id;
SELECT 'papel_usuario.papel_id' relacao,COUNT(*) FILTER(WHERE x.papel_id IS NULL) nulos_obrigatorios,COUNT(*) FILTER(WHERE x.papel_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.papel_usuario x LEFT JOIN novo.papel y ON y.id=x.papel_id;
SELECT 'papel_usuario.unidade_id' relacao,COUNT(*) FILTER(WHERE x.unidade_id IS NULL) nulos_permitidos,COUNT(*) FILTER(WHERE x.unidade_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.papel_usuario x LEFT JOIN novo.unidade y ON y.id=x.unidade_id;
SELECT 'profissional.perfil_usuario' relacao,COUNT(*) FILTER(WHERE x.id IS NULL) nulos_obrigatorios,COUNT(*) FILTER(WHERE x.id IS NOT NULL AND y.usuario_id IS NULL) orfaos FROM novo.profissional x LEFT JOIN novo.perfil_usuario y ON y.usuario_id=x.id;
SELECT 'profissional_servico.profissional_id' relacao,COUNT(*) FILTER(WHERE x.profissional_id IS NULL) nulos_obrigatorios,COUNT(*) FILTER(WHERE x.profissional_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.profissional_servico x LEFT JOIN novo.profissional y ON y.id=x.profissional_id;
SELECT 'profissional_servico.servico_id' relacao,COUNT(*) FILTER(WHERE x.servico_id IS NULL) nulos_obrigatorios,COUNT(*) FILTER(WHERE x.servico_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.profissional_servico x LEFT JOIN novo.servico y ON y.id=x.servico_id;
SELECT 'matricula.aluno_id' relacao,COUNT(*) FILTER(WHERE x.aluno_id IS NULL) nulos_obrigatorios,COUNT(*) FILTER(WHERE x.aluno_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.matricula x LEFT JOIN novo.aluno y ON y.id=x.aluno_id;
SELECT 'matricula.plano_id' relacao,COUNT(*) FILTER(WHERE x.plano_id IS NULL) nulos_obrigatorios,COUNT(*) FILTER(WHERE x.plano_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.matricula x LEFT JOIN novo.plano y ON y.id=x.plano_id;
SELECT 'matricula.unidade_id' relacao,COUNT(*) FILTER(WHERE x.unidade_id IS NULL) nulos_obrigatorios,COUNT(*) FILTER(WHERE x.unidade_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.matricula x LEFT JOIN novo.unidade y ON y.id=x.unidade_id;
SELECT 'renovacao.aluno_id' relacao,COUNT(*) FILTER(WHERE x.aluno_id IS NULL) nulos_obrigatorios,COUNT(*) FILTER(WHERE x.aluno_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.renovacao x LEFT JOIN novo.aluno y ON y.id=x.aluno_id;
SELECT 'renovacao.servico_id' relacao,COUNT(*) FILTER(WHERE x.servico_id IS NULL) nulos_obrigatorios,COUNT(*) FILTER(WHERE x.servico_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.renovacao x LEFT JOIN novo.servico y ON y.id=x.servico_id;
SELECT 'renovacao.matricula_id' relacao,COUNT(*) FILTER(WHERE x.matricula_id IS NULL) nulos_permitidos,COUNT(*) FILTER(WHERE x.matricula_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.renovacao x LEFT JOIN novo.matricula y ON y.id=x.matricula_id;
SELECT 'credito_lancamento.aluno_id' relacao,COUNT(*) FILTER(WHERE x.aluno_id IS NULL) nulos_obrigatorios,COUNT(*) FILTER(WHERE x.aluno_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.credito_lancamento x LEFT JOIN novo.aluno y ON y.id=x.aluno_id;
SELECT 'credito_lancamento.servico_id' relacao,COUNT(*) FILTER(WHERE x.servico_id IS NULL) nulos_obrigatorios,COUNT(*) FILTER(WHERE x.servico_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.credito_lancamento x LEFT JOIN novo.servico y ON y.id=x.servico_id;
SELECT 'credito_lancamento.renovacao_id' relacao,COUNT(*) FILTER(WHERE x.renovacao_id IS NULL) nulos_permitidos,COUNT(*) FILTER(WHERE x.renovacao_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.credito_lancamento x LEFT JOIN novo.renovacao y ON y.id=x.renovacao_id;
SELECT 'credito_lancamento.ator_id' relacao,COUNT(*) FILTER(WHERE x.ator_id IS NULL) nulos_permitidos,COUNT(*) FILTER(WHERE x.ator_id IS NOT NULL AND y.usuario_id IS NULL) orfaos FROM novo.credito_lancamento x LEFT JOIN novo.perfil_usuario y ON y.usuario_id=x.ator_id;
SELECT 'agendamento.aluno_id' relacao,COUNT(*) FILTER(WHERE x.aluno_id IS NULL) nulos_obrigatorios,COUNT(*) FILTER(WHERE x.aluno_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.agendamento x LEFT JOIN novo.aluno y ON y.id=x.aluno_id;
SELECT 'agendamento.unidade_id' relacao,COUNT(*) FILTER(WHERE x.unidade_id IS NULL) nulos_obrigatorios,COUNT(*) FILTER(WHERE x.unidade_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.agendamento x LEFT JOIN novo.unidade y ON y.id=x.unidade_id;
SELECT 'agendamento.servico_id' relacao,COUNT(*) FILTER(WHERE x.servico_id IS NULL) nulos_obrigatorios,COUNT(*) FILTER(WHERE x.servico_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.agendamento x LEFT JOIN novo.servico y ON y.id=x.servico_id;
SELECT 'agendamento.horario_grade_id' relacao,COUNT(*) FILTER(WHERE x.horario_grade_id IS NULL) nulos_permitidos,COUNT(*) FILTER(WHERE x.horario_grade_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.agendamento x LEFT JOIN novo.horario_grade y ON y.id=x.horario_grade_id;
SELECT 'agendamento.profissional_id' relacao,COUNT(*) FILTER(WHERE x.profissional_id IS NULL) nulos_permitidos,COUNT(*) FILTER(WHERE x.profissional_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.agendamento x LEFT JOIN novo.profissional y ON y.id=x.profissional_id;
SELECT 'agendamento.criado_por' relacao,COUNT(*) FILTER(WHERE x.criado_por IS NULL) nulos_permitidos,COUNT(*) FILTER(WHERE x.criado_por IS NOT NULL AND y.usuario_id IS NULL) orfaos FROM novo.agendamento x LEFT JOIN novo.perfil_usuario y ON y.usuario_id=x.criado_por;
SELECT 'atendimento.aluno_id' relacao,COUNT(*) FILTER(WHERE x.aluno_id IS NULL) nulos_obrigatorios,COUNT(*) FILTER(WHERE x.aluno_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.atendimento x LEFT JOIN novo.aluno y ON y.id=x.aluno_id;
SELECT 'atendimento.profissional_id' relacao,COUNT(*) FILTER(WHERE x.profissional_id IS NULL) nulos_obrigatorios,COUNT(*) FILTER(WHERE x.profissional_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.atendimento x LEFT JOIN novo.profissional y ON y.id=x.profissional_id;
SELECT 'atendimento.servico_id' relacao,COUNT(*) FILTER(WHERE x.servico_id IS NULL) nulos_obrigatorios,COUNT(*) FILTER(WHERE x.servico_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.atendimento x LEFT JOIN novo.servico y ON y.id=x.servico_id;
SELECT 'atendimento.agendamento_id' relacao,COUNT(*) FILTER(WHERE x.agendamento_id IS NULL) nulos_permitidos,COUNT(*) FILTER(WHERE x.agendamento_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.atendimento x LEFT JOIN novo.agendamento y ON y.id=x.agendamento_id;
SELECT 'atendimento.unidade_id' relacao,COUNT(*) FILTER(WHERE x.unidade_id IS NULL) nulos_permitidos,COUNT(*) FILTER(WHERE x.unidade_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.atendimento x LEFT JOIN novo.unidade y ON y.id=x.unidade_id;
SELECT 'anamnese.aluno_id' relacao,COUNT(*) FILTER(WHERE x.aluno_id IS NULL) nulos_obrigatorios,COUNT(*) FILTER(WHERE x.aluno_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.anamnese x LEFT JOIN novo.aluno y ON y.id=x.aluno_id;
SELECT 'anamnese.avaliacao_id' relacao,COUNT(*) FILTER(WHERE x.avaliacao_id IS NULL) nulos_permitidos,COUNT(*) FILTER(WHERE x.avaliacao_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.anamnese x LEFT JOIN novo.avaliacao y ON y.id=x.avaliacao_id;
SELECT 'anamnese.profissional_id' relacao,COUNT(*) FILTER(WHERE x.profissional_id IS NULL) nulos_permitidos,COUNT(*) FILTER(WHERE x.profissional_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.anamnese x LEFT JOIN novo.profissional y ON y.id=x.profissional_id;
SELECT 'arquivo.relatorio_id' relacao,COUNT(*) FILTER(WHERE x.relatorio_id IS NULL) nulos_permitidos,COUNT(*) FILTER(WHERE x.relatorio_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.arquivo x LEFT JOIN novo.relatorio_treino y ON y.id=x.relatorio_id;
SELECT 'arquivo.aluno_id' relacao,COUNT(*) FILTER(WHERE x.aluno_id IS NULL) nulos_permitidos,COUNT(*) FILTER(WHERE x.aluno_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.arquivo x LEFT JOIN novo.aluno y ON y.id=x.aluno_id;
SELECT 'arquivo.unidade_id' relacao,COUNT(*) FILTER(WHERE x.unidade_id IS NULL) nulos_permitidos,COUNT(*) FILTER(WHERE x.unidade_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.arquivo x LEFT JOIN novo.unidade y ON y.id=x.unidade_id;
SELECT 'arquivo.avaliacao_id' relacao,COUNT(*) FILTER(WHERE x.avaliacao_id IS NULL) nulos_permitidos,COUNT(*) FILTER(WHERE x.avaliacao_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.arquivo x LEFT JOIN novo.avaliacao y ON y.id=x.avaliacao_id;
SELECT 'arquivo.atendimento_id' relacao,COUNT(*) FILTER(WHERE x.atendimento_id IS NULL) nulos_permitidos,COUNT(*) FILTER(WHERE x.atendimento_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.arquivo x LEFT JOIN novo.atendimento y ON y.id=x.atendimento_id;
SELECT 'arquivo.enviado_por' relacao,COUNT(*) FILTER(WHERE x.enviado_por IS NULL) nulos_permitidos,COUNT(*) FILTER(WHERE x.enviado_por IS NOT NULL AND y.usuario_id IS NULL) orfaos FROM novo.arquivo x LEFT JOIN novo.perfil_usuario y ON y.usuario_id=x.enviado_por;
SELECT 'evento_auditoria.ator_id' relacao,COUNT(*) FILTER(WHERE x.ator_id IS NULL) nulos_permitidos,COUNT(*) FILTER(WHERE x.ator_id IS NOT NULL AND y.usuario_id IS NULL) orfaos FROM novo.evento_auditoria x LEFT JOIN novo.perfil_usuario y ON y.usuario_id=x.ator_id;
SELECT 'evento_auditoria.unidade_id' relacao,COUNT(*) FILTER(WHERE x.unidade_id IS NULL) nulos_permitidos,COUNT(*) FILTER(WHERE x.unidade_id IS NOT NULL AND y.id IS NULL) orfaos FROM novo.evento_auditoria x LEFT JOIN novo.unidade y ON y.id=x.unidade_id;

-- 7) Creditos: renovacao reinicia pelo delta; sem reset fixo de 10.
SELECT origem_tipo,COUNT(*) lancamentos FROM novo.credito_lancamento GROUP BY origem_tipo ORDER BY origem_tipo;
SELECT r.id,r.aluno_id,r.servico_id,r.matricula_id,r.competencia,r.periodicidade,r.pendencia
FROM novo.renovacao r WHERE NOT EXISTS(SELECT 1 FROM novo.credito_lancamento l WHERE l.renovacao_id=r.id);
SELECT l.id,l.aluno_id,l.servico_id,l.delta,l.motivo,l.criado_em
FROM novo.credito_lancamento l WHERE l.origem_tipo='renovacao' AND l.renovacao_id IS NULL;
WITH u AS (
 SELECT DISTINCT ON(aluno_id,servico_id) aluno_id,servico_id,id renovacao_id,criado_em renovacao_em,delta delta_renovacao
 FROM novo.credito_lancamento WHERE origem_tipo='renovacao'
 ORDER BY aluno_id,servico_id,criado_em DESC,id DESC
), s AS (
 SELECT l.aluno_id,l.servico_id,u.renovacao_id,u.renovacao_em,u.delta_renovacao,
 COUNT(*) lancamentos_considerados,SUM(l.delta)::int saldo_reconstruido
 FROM novo.credito_lancamento l LEFT JOIN u ON u.aluno_id=l.aluno_id AND u.servico_id=l.servico_id
 WHERE u.renovacao_id IS NULL OR (l.criado_em,l.id)>=(u.renovacao_em,u.renovacao_id)
 GROUP BY l.aluno_id,l.servico_id,u.renovacao_id,u.renovacao_em,u.delta_renovacao
), empates AS (
 SELECT u.aluno_id,u.servico_id,u.renovacao_id,u.renovacao_em,
  COUNT(l.id) FILTER (WHERE l.id<>u.renovacao_id) lancamentos_mesmo_timestamp,
  COUNT(l.id) FILTER (WHERE l.id<>u.renovacao_id AND l.id<u.renovacao_id) empates_anteriores_por_id
 FROM u LEFT JOIN novo.credito_lancamento l
  ON l.aluno_id=u.aluno_id AND l.servico_id=u.servico_id AND l.criado_em=u.renovacao_em
 GROUP BY u.aluno_id,u.servico_id,u.renovacao_id,u.renovacao_em
), comparacoes AS (
 SELECT COALESCE(s.aluno_id,v.aluno_id) aluno_id,COALESCE(s.servico_id,v.servico_id) servico_id,
 s.renovacao_id,s.renovacao_em,s.delta_renovacao,s.lancamentos_considerados,
 COALESCE(e.lancamentos_mesmo_timestamp,0) lancamentos_mesmo_timestamp,
 COALESCE(e.empates_anteriores_por_id,0) empates_anteriores_por_id,
 s.saldo_reconstruido,v.saldo saldo_view,
 CASE WHEN s.aluno_id IS NULL THEN 'SOMENTE_NA_VIEW'
      WHEN v.aluno_id IS NULL THEN 'SOMENTE_NA_RECONSTRUCAO'
      WHEN s.saldo_reconstruido IS NOT DISTINCT FROM v.saldo THEN 'OK'
      ELSE 'DIVERGENCIA' END status
 FROM s FULL JOIN novo.vw_saldo_credito v USING(aluno_id,servico_id)
 LEFT JOIN empates e ON e.aluno_id=COALESCE(s.aluno_id,v.aluno_id)
  AND e.servico_id=COALESCE(s.servico_id,v.servico_id)
)
SELECT *,CASE WHEN lancamentos_mesmo_timestamp>0 THEN true ELSE false END tem_empate_no_timestamp,
 CASE WHEN status='DIVERGENCIA' AND lancamentos_mesmo_timestamp>0
      THEN 'DIVERGENCIA_POTENCIALMENTE_EXPLICADA_POR_EMPATE'
      WHEN status='DIVERGENCIA' THEN 'DIVERGENCIA_A_INVESTIGAR'
      ELSE status END interpretacao
FROM comparacoes ORDER BY aluno_id,servico_id;
-- Resumo: mesma reconstrucao da consulta anterior (reinicio na renovacao mais recente).
WITH u AS (
 SELECT DISTINCT ON(aluno_id,servico_id) aluno_id,servico_id,id renovacao_id,criado_em renovacao_em
 FROM novo.credito_lancamento WHERE origem_tipo='renovacao'
 ORDER BY aluno_id,servico_id,criado_em DESC,id DESC
), s AS (
 SELECT l.aluno_id,l.servico_id,SUM(l.delta)::int saldo_reconstruido
 FROM novo.credito_lancamento l LEFT JOIN u ON u.aluno_id=l.aluno_id AND u.servico_id=l.servico_id
 WHERE u.renovacao_id IS NULL OR (l.criado_em,l.id)>=(u.renovacao_em,u.renovacao_id)
 GROUP BY l.aluno_id,l.servico_id
), comparacoes AS (
 SELECT COALESCE(s.aluno_id,v.aluno_id) aluno_id,COALESCE(s.servico_id,v.servico_id) servico_id,
 CASE WHEN s.aluno_id IS NULL THEN 'SOMENTE_NA_VIEW'
      WHEN v.aluno_id IS NULL THEN 'SOMENTE_NA_RECONSTRUCAO'
      WHEN s.saldo_reconstruido IS NOT DISTINCT FROM v.saldo THEN 'OK' ELSE 'DIVERGENCIA' END status
 FROM s FULL JOIN novo.vw_saldo_credito v USING(aluno_id,servico_id)
)
SELECT status,COUNT(*) quantidade FROM comparacoes GROUP BY status ORDER BY status;
