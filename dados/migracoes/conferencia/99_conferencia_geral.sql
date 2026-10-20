-- =============================================================================
-- conferencia/99_conferencia_geral.sql
-- Conferência do ensaio geral (tarefa 1.7). SÓ LEITURA: não grava nada.
-- Roda no fim do script mestre e pode rodar sozinha a qualquer momento.
--
-- 1) Origem x destino: para cada tabela da origem que vira uma tabela (ou um
--    tipo) do destino, linhas_origem (do gabarito) = linhas_destino + rejeitados.
--    A coluna `ok` precisa ser true em todas as linhas.
-- 2) Rejeitados por script e motivo (esperado na foto de 12/10: nenhum).
-- 3) Linhas com pendência, por tabela de novo (descoberto pelo catálogo: toda
--    tabela que tem a coluna `pendencia`).
-- 4) Última execução de cada script (novo.v_resumo_carga).
-- Nenhuma consulta mostra dado pessoal: só nomes de tabela, motivos e contagens.
-- =============================================================================

-- 1) Origem x destino
with gab as (
  select tabela, linhas from novo.carga_gabarito
  where rotulo = (select max(rotulo) from novo.carga_gabarito)   -- o gabarito mais recente
),
rej as (   -- só rejeições da linha inteira (as de "chave ... sem métrica" não tiram a linha)
  select script, tabela_origem, count(distinct id_origem) as n
  from novo.carga_rejeitado where motivo not like 'chave %'
  group by script, tabela_origem
),
par (ordem, script, tabela_origem, destino, linhas_destino) as (values
  ( 1, 'cadastro', 'profiles',                  'perfil_usuario',                 (select count(*) from novo.perfil_usuario)),
  ( 2, 'cadastro', 'athletes',                  'aluno',                          (select count(*) from novo.aluno)),
  ( 3, 'comercial', 'athletes',                  'matricula (1 por aluno)',        (select count(*) from novo.matricula)),
  ( 4, 'comercial', 'credit_transactions',       'credito_lancamento',             (select count(*) from novo.credito_lancamento)),
  ( 5, 'agenda', 'schedule_blocks',           'bloqueio_agenda',                (select count(*) from novo.bloqueio_agenda)),
  ( 6, 'agenda', 'bookings',                  'agendamento',                    (select count(*) from novo.agendamento)),
  ( 7, 'agenda', 'waitlist',                  'lista_espera',                   (select count(*) from novo.lista_espera)),
  ( 8, 'agenda', 'training_feedback',         'feedback_treino',                (select count(*) from novo.feedback_treino)),
  ( 9, 'relatorio', 'training_report_materials', 'catalogo_item (material)',       (select count(*) from novo.catalogo_item where dominio = 'material' and id_origem is not null)),
  (10, 'relatorio', 'training_report_technologies', 'catalogo_item (tecnologia)',  (select count(*) from novo.catalogo_item where dominio = 'tecnologia' and id_origem is not null)),
  (11, 'relatorio', 'training_reports',          'relatorio_treino',               (select count(*) from novo.relatorio_treino)),
  (12, 'avaliacao', 'physical_test_sessions',    'avaliacao (teste_fisico)',       (select count(*) from novo.avaliacao where tipo = 'teste_fisico')),
  (13, 'avaliacao', 'weekly_evaluations',        'avaliacao (semanal)',            (select count(*) from novo.avaliacao where tipo = 'semanal')),
  (14, 'atendimento', 'physio_assessments',        'avaliacao (fisioterapia)',       (select count(*) from novo.avaliacao where tipo = 'fisioterapia')),
  (15, 'atendimento', 'physio_assessments',        'anamnese',                       (select count(*) from novo.anamnese)),
  (16, 'atendimento', 'physio_evolutions',         'atendimento (fisio, sem agendamento)',
                                    (select count(*) from novo.atendimento t where exists (select 1 from origem.physio_evolutions e where e.id = t.id))),
  (17, 'atendimento', 'specialist_evolutions',     'atendimento (especialista)',
                                    (select count(*) from novo.atendimento t where exists (select 1 from origem.specialist_evolutions e where e.id = t.id))),
  (18, 'documentos', 'activity_logs',             'evento_auditoria',               (select count(*) from novo.evento_auditoria where tabela_origem = 'activity_logs')),
  (19, 'documentos', 'booking_audit_logs',        'evento_auditoria',               (select count(*) from novo.evento_auditoria where tabela_origem = 'booking_audit_logs'))
)
select p.script, p.tabela_origem, p.destino, g.linhas as linhas_origem, p.linhas_destino,
       coalesce(r.n, 0) as rejeitados,
       g.linhas = p.linhas_destino + coalesce(r.n, 0) as ok
from par p
left join gab g on g.tabela = p.tabela_origem
left join rej r on r.script = p.script and r.tabela_origem = p.tabela_origem
order by p.ordem;

-- 1b) Arquivos: um por caminho distinto não vazio (as 9 colunas de caminho)
select 'arquivo' as destino,
       (select count(*) from novo.arquivo) as linhas_destino,
       (select count(distinct id_origem) from novo.carga_rejeitado where tabela_origem = 'arquivo (caminho)') as rejeitados,
       (select count(*) from (
          select btrim(storage_path) c from origem.student_files union
          select btrim(storage_path) from origem.nutritionist_files union
          select btrim(storage_path) from origem.physio_evolutions union
          select btrim(file_path) from origem.specialist_evolutions union
          select btrim(file_path) from origem.training_reports union
          select btrim(pdf_storage_path) from origem.training_reports union
          select btrim(file_path) from origem.physical_test_comparisons union
          select btrim(file_path) from origem.physio_assessments union
          select btrim(k.v) from origem.physio_assessments p
            cross join lateral jsonb_each_text(p.pkz_data) k(k, v)
            where k.k ~ '^img_' or k.k in ('carimbo_path', 'laudo_path') union
          select btrim(file_path) from origem.student_tests) x
        where nullif(c, '') is not null) as caminhos_origem;

-- 2) Rejeitados por script e motivo
select script, tabela_origem, motivo, count(*) as n
from novo.carga_rejeitado
group by script, tabela_origem, motivo
order by script, tabela_origem, motivo;

-- 3) Linhas com pendência, por tabela (todas as tabelas de novo com a coluna pendencia)
select c.table_name as tabela,
       (xpath('/row/n/text()', query_to_xml(
          format('select count(*) as n from novo.%I', c.table_name), false, true, '')))[1]::text::int as linhas,
       (xpath('/row/n/text()', query_to_xml(
          format('select count(*) as n from novo.%I where pendencia is not null', c.table_name), false, true, '')))[1]::text::int as com_pendencia
from information_schema.columns c
join information_schema.tables t on t.table_schema = c.table_schema and t.table_name = c.table_name
where c.table_schema = 'novo' and c.column_name = 'pendencia' and t.table_type = 'BASE TABLE'
order by c.table_name;

-- 4) Última execução de cada script
select script, linhas_carregadas, linhas_rejeitadas, executado_em, observacao
from novo.v_resumo_carga
order by executado_em;
