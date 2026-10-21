-- =============================================================================
-- 80_carga_documentos.sql
-- Domínio: documentos              Dono: Micael (Frente 1)
-- Origem:  caminhos de arquivo de student_files, nutritionist_files, physio_evolutions,
--          specialist_evolutions, training_reports (file_path e pdf_storage_path),
--          physical_test_comparisons, physio_assessments (file_path e pkz_data),
--          student_tests; auditoria de activity_logs e booking_audit_logs
-- Destino: novo.arquivo, novo.evento_auditoria
--          (consentimento, relatorio_emissao, relatorio_envio, notificacao e
--          acesso_dado_sensivel: só estrutura, sem carga)
-- Depende de: migrations 001–011; scripts 10–70
-- Mapeamento: mapeamento/documentos.csv
--
-- Um caminho = um arquivo. Caminho ligado a alunos diferentes ou a dois "donos"
-- diferentes (relatório, avaliação, atendimento) é rejeitado, nunca escolhido no
-- chute. O id de origem do rejeitado é md5(caminho) — o caminho não é copiado.
-- Da auditoria saem do payload: athlete_name, phone, full_name e username
-- (pendência 11).
-- =============================================================================
\set ON_ERROR_STOP on

begin;

select set_config('novo.modo_carga', 'on', true);

-- -----------------------------------------------------------------------------
-- Todas as referências a caminho, uma linha por (origem, caminho)
--   prioridade: 1 = origem específica (dá o tipo); 2 = pasta genérica do aluno
-- -----------------------------------------------------------------------------
create temporary table tmp_ref on commit drop as
select btrim(r.cam) as caminho, r.fonte, r.prioridade, r.aluno_id, r.nome, r.mime, r.bytes, r.tipo, r.clinico,
       r.relatorio_id, r.avaliacao_id, r.atendimento_id, r.enviado_por, r.pendencia, r.created_at
from (
  select f.storage_path as cam, 'student_files'::text as fonte, 2 as prioridade, f.athlete_id as aluno_id,
         nullif(btrim(f.file_name), '') as nome, f.mime_type as mime, f.size_bytes as bytes,
         case f.folder when '02_Relatorios_de_Treino' then 'relatorio_treino'
                       when '03_Evolucao_e_Comparativos' then 'evolucao_comparativo'
                       when '04_Extrato_Geral_de_Relatorios' then 'extrato'
                       when '05_Fisioterapia' then 'fisioterapia' else 'arquivo_aluno' end as tipo,
         (f.folder = '05_Fisioterapia') as clinico,
         null::uuid as relatorio_id, null::uuid as avaliacao_id, null::uuid as atendimento_id,
         f.uploaded_by as enviado_por,
         case when f.folder not in ('02_Relatorios_de_Treino', '03_Evolucao_e_Comparativos',
                                    '04_Extrato_Geral_de_Relatorios', '05_Fisioterapia')
              then 'pasta de origem desconhecida' end as pendencia,
         f.created_at
  from origem.student_files f
  union all
  select n.storage_path, 'nutritionist_files', 1, n.athlete_id, nullif(btrim(n.file_name), ''), n.mime_type,
         n.size_bytes, 'nutricao', true, null, null, null, n.uploaded_by, null, n.created_at
  from origem.nutritionist_files n
  union all
  select e.storage_path, 'physio_evolutions', 1, e.athlete_id, nullif(btrim(e.file_name), ''), null, null,
         'evolucao', true, null, null, e.id, e.physio_id, null, e.created_at
  from origem.physio_evolutions e
  union all
  select e.file_path, 'specialist_evolutions', 1, e.athlete_id, nullif(btrim(e.file_name), ''), null, null,
         'evolucao', true, null, null, e.id, e.professional_id, null, e.created_at
  from origem.specialist_evolutions e
  union all
  select c.caminho, 'training_reports', 1, t.athlete_id, null, null, null,
         'relatorio_treino', false, t.id, null, null, t.created_by, null, t.created_at
  from origem.training_reports t
  cross join lateral (values (t.file_path), (t.pdf_storage_path)) c(caminho)
  union all
  select c.file_path, 'physical_test_comparisons', 1, c.athlete_id, null, null, null,
         'comparativo_teste_fisico', false, null, null, null, c.created_by,
         format('comparativo entre as avaliações %s e %s', c.session_a_id, c.session_b_id), c.created_at
  from origem.physical_test_comparisons c
  union all
  select p.file_path, 'physio_assessments', 1, p.athlete_id, null, null, null,
         'avaliacao_fisioterapia', true, null, p.id, null, p.created_by, null, p.created_at
  from origem.physio_assessments p
  union all
  select k.v, 'physio_assessments.pkz_data', 1, p.athlete_id, null, null, null,
         case when k.k ~ '^img_mob_' then 'imagem_mobilidade'
              when k.k ~ '^img_'     then 'imagem_postural'
              when k.k = 'carimbo_path' then 'carimbo_profissional'
              when k.k = 'laudo_path'   then 'laudo' end,
         true, null, p.id, null, p.created_by,
         case when k.k = 'carimbo_path' then 'carimbo do profissional, não do aluno' end,
         p.created_at
  from origem.physio_assessments p
  cross join lateral jsonb_each_text(case when jsonb_typeof(p.pkz_data) = 'object' then p.pkz_data else '{}' end) k(k, v)
  where k.k ~ '^img_' or k.k in ('carimbo_path', 'laudo_path')
  union all
  select s.file_path, 'student_tests', 1, s.athlete_id, null, null, null,
         'teste_fisico', false, null, null, null, s.created_by, null, s.created_at
  from origem.student_tests s
) r
where nullif(btrim(r.cam), '') is not null;

-- O dono só vale se existir no destino; senão o vínculo sai, com pendência.
create temporary table tmp_ref2 on commit drop as
select r.caminho, r.fonte, r.prioridade, r.nome, r.mime, r.bytes, r.tipo, r.clinico, r.created_at,
       r.aluno_id,
       case when exists (select 1 from novo.relatorio_treino x where x.id = r.relatorio_id) then r.relatorio_id end as relatorio_id,
       case when exists (select 1 from novo.avaliacao x where x.id = r.avaliacao_id) then r.avaliacao_id end as avaliacao_id,
       case when exists (select 1 from novo.atendimento x where x.id = r.atendimento_id) then r.atendimento_id end as atendimento_id,
       case when exists (select 1 from novo.perfil_usuario u where u.usuario_id = r.enviado_por) then r.enviado_por end as enviado_por,
       novo.juntar_pendencia(r.pendencia,
         case when (r.relatorio_id is not null and not exists (select 1 from novo.relatorio_treino x where x.id = r.relatorio_id))
                or (r.avaliacao_id is not null and not exists (select 1 from novo.avaliacao x where x.id = r.avaliacao_id))
                or (r.atendimento_id is not null and not exists (select 1 from novo.atendimento x where x.id = r.atendimento_id))
              then 'dono do arquivo não encontrado no destino: vínculo removido' end) as pendencia
from tmp_ref r;

-- Um registro por caminho
create temporary table tmp_arq on commit drop as
select r.caminho,
       count(distinct r.aluno_id) as n_alunos,
       count(distinct coalesce('r' || r.relatorio_id, 'v' || r.avaliacao_id, 'a' || r.atendimento_id)) as n_donos,
       min(r.aluno_id::text)::uuid as aluno_id,
       min(r.relatorio_id::text)::uuid as relatorio_id,
       min(r.avaliacao_id::text)::uuid as avaliacao_id,
       min(r.atendimento_id::text)::uuid as atendimento_id,
       (array_agg(r.nome order by r.prioridade, r.created_at) filter (where r.nome is not null))[1] as nome,
       (array_agg(r.mime order by r.prioridade, r.created_at) filter (where r.mime is not null))[1] as mime,
       max(r.bytes) as bytes,
       (array_agg(r.tipo order by r.prioridade, r.created_at))[1] as tipo,
       bool_or(r.clinico) as clinico,
       (array_agg(r.enviado_por order by r.prioridade, r.created_at) filter (where r.enviado_por is not null))[1] as enviado_por,
       novo.juntar_pendencia(null, string_agg(distinct r.pendencia, '; ' order by r.pendencia)) as pendencia,
       min(r.created_at) as criado_em
from tmp_ref2 r
group by r.caminho;

-- -----------------------------------------------------------------------------
-- b) Rejeitados: arquivo
-- -----------------------------------------------------------------------------
insert into novo.carga_rejeitado (script, tabela_origem, id_origem, motivo)
select 'documentos', 'arquivo (caminho)', md5(a.caminho)::uuid, x.motivo
from tmp_arq a
cross join lateral (values
  (case when a.n_alunos > 1 then 'caminho ligado a alunos diferentes' end),
  (case when a.n_donos > 1 then 'caminho com dois donos diferentes (relatório, avaliação, atendimento)' end),
  (case when a.n_alunos = 1 and not exists (select 1 from novo.aluno al where al.id = a.aluno_id)
        then 'aluno inexistente no destino' end)) x(motivo)
where x.motivo is not null
on conflict (script, tabela_origem, id_origem, motivo) do nothing;

-- -----------------------------------------------------------------------------
-- c1) arquivo
-- -----------------------------------------------------------------------------
insert into novo.arquivo as f (storage_path, nome, mime, bytes, tipo, confidencialidade, aluno_id, unidade_id,
                               relatorio_id, avaliacao_id, atendimento_id, enviado_por, pendencia, criado_em)
select a.caminho,
       coalesce(a.nome, regexp_replace(a.caminho, '^.*/', '')),
       coalesce(a.mime, case lower(substring(a.caminho from '\.([A-Za-z0-9]+)$'))
                          when 'pdf' then 'application/pdf' when 'png' then 'image/png'
                          when 'jpg' then 'image/jpeg' when 'jpeg' then 'image/jpeg'
                          when 'webp' then 'image/webp' end),
       a.bytes, a.tipo,
       case when a.clinico then 'clinico' else 'normal' end,
       a.aluno_id, novo.unidade_atual_do_aluno(a.aluno_id),
       a.relatorio_id, a.avaliacao_id, a.atendimento_id, a.enviado_por, a.pendencia, a.criado_em
from tmp_arq a
where a.n_alunos = 1 and a.n_donos <= 1
  and exists (select 1 from novo.aluno al where al.id = a.aluno_id)
on conflict (storage_path) do update
  set nome = excluded.nome, mime = excluded.mime, bytes = excluded.bytes, tipo = excluded.tipo,
      confidencialidade = excluded.confidencialidade, aluno_id = excluded.aluno_id,
      unidade_id = excluded.unidade_id, relatorio_id = excluded.relatorio_id,
      avaliacao_id = excluded.avaliacao_id, atendimento_id = excluded.atendimento_id,
      enviado_por = excluded.enviado_por,
      pendencia = novo.juntar_pendencia(f.pendencia, excluded.pendencia),
      criado_em = excluded.criado_em, atualizado_em = now();

-- -----------------------------------------------------------------------------
-- c2) evento_auditoria: activity_logs
-- -----------------------------------------------------------------------------
insert into novo.evento_auditoria as ev (ator_id, acao, acao_original, entidade, entidade_id, valor_anterior,
                                         valor_novo, unidade_id, ip, tabela_origem, id_origem, pendencia, criado_em)
select case when u.usuario_id is not null then l.actor_id end,
       x.acao,
       case when x.acao <> l.action then l.action end,
       x.entidade, l.entity_id, null,
       case when jsonb_typeof(l.payload) = 'object'
            then l.payload - array['athlete_name', 'phone', 'full_name', 'username']
            else l.payload end,
       case x.entidade
         when 'aluno'       then novo.unidade_atual_do_aluno(l.entity_id)
         when 'agendamento' then (select ag.unidade_id from novo.agendamento ag where ag.id = l.entity_id) end,
       null, 'activity_logs', l.id,
       novo.juntar_pendencia(novo.juntar_pendencia(
         case when l.actor_id is not null and u.usuario_id is null then 'ator não encontrado no destino' end,
         case when jsonb_typeof(l.payload) = 'object' and l.payload ?| array['athlete_name', 'phone', 'full_name', 'username']
              then 'dados pessoais removidos do payload' end),
         case when x.acao = 'send_activation_link' and l.entity_id is null
              then 'evento sem referência ao aluno (nome removido)' end),
       l.created_at
from origem.activity_logs l
left join novo.perfil_usuario u on u.usuario_id = l.actor_id
cross join lateral (select
  case when l.action = 'Link de ativação enviado via WhatsApp' then 'send_activation_link'
       when l.action in ('professor_assigned', 'assign_professor', 'assign_booking_professor') then 'assign_professor'
       else l.action end as acao,
  case l.entity when 'athlete' then 'aluno' when 'booking' then 'agendamento' when 'user' then 'usuario'
                when 'system' then 'sistema' else l.entity end as entidade) x
on conflict (tabela_origem, id_origem) do update
  set ator_id = excluded.ator_id, acao = excluded.acao, acao_original = excluded.acao_original,
      entidade = excluded.entidade, entidade_id = excluded.entidade_id, valor_anterior = excluded.valor_anterior,
      valor_novo = excluded.valor_novo, unidade_id = excluded.unidade_id,
      pendencia = novo.juntar_pendencia(ev.pendencia, excluded.pendencia),
      criado_em = excluded.criado_em, atualizado_em = now();

-- -----------------------------------------------------------------------------
-- c3) evento_auditoria: booking_audit_logs (troca de professor)
-- -----------------------------------------------------------------------------
insert into novo.evento_auditoria as ev (ator_id, acao, acao_original, entidade, entidade_id, valor_anterior,
                                         valor_novo, unidade_id, ip, tabela_origem, id_origem, pendencia, criado_em)
select case when u.usuario_id is not null then coalesce(l.actor_id, l.created_by) end,
       x.acao,
       case when x.acao <> l.action then l.action end,
       'agendamento', l.booking_id,
       nullif(jsonb_strip_nulls(jsonb_build_object('professor_id', l.previous_professor_id, 'valor', l.old_value)), '{}'),
       nullif(jsonb_strip_nulls(jsonb_build_object('professor_id', l.new_professor_id, 'valor', l.new_value,
                                                   'motivo', l.reason)), '{}'),
       (select ag.unidade_id from novo.agendamento ag where ag.id = l.booking_id),
       null, 'booking_audit_logs', l.id,
       novo.juntar_pendencia(
         case when coalesce(l.actor_id, l.created_by) is not null and u.usuario_id is null
              then 'ator não encontrado no destino' end,
         case when l.created_at is null then 'data do evento desconhecida (usada a do agendamento)' end),
       coalesce(l.created_at, b.created_at, now())
from origem.booking_audit_logs l
left join origem.bookings b on b.id = l.booking_id
left join novo.perfil_usuario u on u.usuario_id = coalesce(l.actor_id, l.created_by)
cross join lateral (select
  case when l.action in ('professor_assigned', 'assign_professor', 'assign_booking_professor') then 'assign_professor'
       else l.action end as acao) x
on conflict (tabela_origem, id_origem) do update
  set ator_id = excluded.ator_id, acao = excluded.acao, acao_original = excluded.acao_original,
      entidade = excluded.entidade, entidade_id = excluded.entidade_id, valor_anterior = excluded.valor_anterior,
      valor_novo = excluded.valor_novo, unidade_id = excluded.unidade_id,
      pendencia = novo.juntar_pendencia(ev.pendencia, excluded.pendencia),
      criado_em = excluded.criado_em, atualizado_em = now();

-- -----------------------------------------------------------------------------
-- Registro da execução
-- -----------------------------------------------------------------------------
insert into novo.carga_execucao (script, linhas_carregadas, linhas_rejeitadas, observacao)
select 'documentos',
       (select count(*) from novo.arquivo) + (select count(*) from novo.evento_auditoria),
       (select count(*) from novo.carga_rejeitado where script = 'documentos'),
       format('arquivo %s (clínico %s; ligados a relatório %s, avaliação %s, atendimento %s), '
              || 'evento_auditoria %s (payload com dado pessoal removido %s, ator não encontrado %s)',
              (select count(*) from novo.arquivo),
              (select count(*) from novo.arquivo where confidencialidade = 'clinico'),
              (select count(*) from novo.arquivo where relatorio_id is not null),
              (select count(*) from novo.arquivo where avaliacao_id is not null),
              (select count(*) from novo.arquivo where atendimento_id is not null),
              (select count(*) from novo.evento_auditoria),
              (select count(*) from novo.evento_auditoria where pendencia like '%dados pessoais removidos%'),
              (select count(*) from novo.evento_auditoria where pendencia like '%ator não encontrado%'));

commit;
