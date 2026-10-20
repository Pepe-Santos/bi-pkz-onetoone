-- =============================================================================
-- 40_carga_agenda.sql
-- Domínio: agenda                  Dono: Micael (Frente 1)
-- Origem:  regras das funções do app (is_valid_slot, get_service_day,
--          service_capacity — lidas com pg_get_functiondef e escritas aqui),
--          origem.schedule_blocks, origem.bookings, origem.athletes (duração),
--          origem.activity_logs (datas de cancelamento e presença),
--          origem.specialist_evolutions (profissional do especialista),
--          origem.waitlist, origem.training_feedback
-- Destino: novo.horario_grade, bloqueio_agenda, bloqueio_grade, agendamento,
--          sessao_treino, lista_espera, feedback_treino
-- Depende de: migrations 001–010; scripts 10, 20, 30 (unidade vem da matrícula)
-- Mapeamento: mapeamento/agenda.csv
-- =============================================================================
\set ON_ERROR_STOP on

begin;

select set_config('novo.modo_carga', 'on', true);

create or replace function pg_temp.servico_codigo(t text) returns text language sql immutable as $$
  select case t when 'treino' then 'treino' when 'fisioterapeuta' then 'fisioterapia'
                when 'nutricionista' then 'nutricao' when 'psicologo' then 'psicologia' end;
$$;

-- -----------------------------------------------------------------------------
-- c1) horario_grade, reconstruída das regras do app
--   is_valid_slot: seg–sex 06:00–20:00, sábado 08:00–11:00 (inícios)
--   get_service_day: treino PKZ de hora em hora a partir das 08:00; One to One a
--     partir das 06:00, de 30 em 30 antes das 17:00 e de hora em hora depois;
--     fisio de 15 em 15 a partir das 07:00; nutri/psico de 30 em 30 a partir das 08:00
--   service_capacity: treino 6 (sábado 08:00 = 10); especializados 1
--   fisio, nutri e psico não separam por programa → grade compartilhada (unidade nula)
-- -----------------------------------------------------------------------------
insert into novo.horario_grade as g (unidade_id, servico_id, dia_semana, hora_inicio, hora_fim,
                                     capacidade, intervalo_min, vigencia_inicio, pendencia)
select u.id, s.id, d.dia, v.ini::time, v.fim::time, v.cap, v.intervalo,
       coalesce((select min(b.slot_date) from origem.bookings b), current_date),
       'grade reconstruída das regras do app: confirmar com a coordenação'
from (values
  -- unidade,     serviço,        dias,     início,  fim,     cap, intervalo
  ('pkz',        'treino',       'seg-sex', '08:00', '21:00', 6,   60),
  ('pkz',        'treino',       'sab',     '08:00', '09:00', 10,  60),
  ('pkz',        'treino',       'sab',     '09:00', '12:00', 6,   60),
  ('one_to_one', 'treino',       'seg-sex', '06:00', '17:00', 6,   30),
  ('one_to_one', 'treino',       'seg-sex', '17:00', '21:00', 6,   60),
  ('one_to_one', 'treino',       'sab',     '08:00', '08:30', 10,  30),
  ('one_to_one', 'treino',       'sab',     '08:30', '11:30', 6,   30),
  (null,         'fisioterapia', 'seg-sex', '07:00', '20:15', 1,   15),
  (null,         'fisioterapia', 'sab',     '08:00', '11:15', 1,   15),
  (null,         'nutricao',     'seg-sex', '08:00', '20:30', 1,   30),
  (null,         'nutricao',     'sab',     '08:00', '11:30', 1,   30),
  (null,         'psicologia',   'seg-sex', '08:00', '20:30', 1,   30),
  (null,         'psicologia',   'sab',     '08:00', '11:30', 1,   30)
) v(unidade, servico, dias, ini, fim, cap, intervalo)
join novo.servico s on s.codigo = v.servico
left join novo.unidade u on u.codigo = v.unidade
cross join lateral unnest(case v.dias when 'seg-sex' then array[1, 2, 3, 4, 5] else array[6] end) d(dia)
on conflict on constraint horario_grade_chave do update
  set hora_fim = excluded.hora_fim, capacidade = excluded.capacidade,
      intervalo_min = excluded.intervalo_min,
      pendencia = novo.juntar_pendencia(g.pendencia, excluded.pendencia),
      atualizado_em = now();

-- -----------------------------------------------------------------------------
-- c2) bloqueio_agenda (weekday ISO 1–7 → dow 0–6)
-- -----------------------------------------------------------------------------
insert into novo.carga_rejeitado (script, tabela_origem, id_origem, motivo)
select 'agenda', 'schedule_blocks', b.id,
       case when b.block_date is null then 'bloqueio sem data'
            else 'bloqueio com fim antes do início' end
from origem.schedule_blocks b
where b.block_date is null or b.end_time <= b.start_time
on conflict (script, tabela_origem, id_origem, motivo) do nothing;

insert into novo.bloqueio_agenda as ba (id, unidade_id, servico_id, data, permanente, dia_semana,
                                        hora_inicio, hora_fim, motivo, criado_por, criado_em)
select b.id, u.id, s.id, b.block_date, b.is_permanent, (b.weekday % 7)::smallint,
       b.start_time, b.end_time, b.reason,
       case when exists (select 1 from novo.perfil_usuario p where p.usuario_id = b.created_by) then b.created_by end,
       b.created_at
from origem.schedule_blocks b
left join novo.unidade u on u.codigo = b.program::text
left join novo.servico s on s.codigo = pg_temp.servico_codigo(b.service::text)
where b.block_date is not null and b.end_time > b.start_time
on conflict (id) do update
  set unidade_id = excluded.unidade_id, servico_id = excluded.servico_id, data = excluded.data,
      permanente = excluded.permanente, dia_semana = excluded.dia_semana,
      hora_inicio = excluded.hora_inicio, hora_fim = excluded.hora_fim, motivo = excluded.motivo,
      criado_por = excluded.criado_por, criado_em = excluded.criado_em, atualizado_em = now();

-- c3) bloqueio_grade: quais horários da grade cada bloqueio suspende
insert into novo.bloqueio_grade (bloqueio_id, horario_grade_id)
select b.id, g.id
from novo.bloqueio_agenda b
join novo.horario_grade g
  on (b.servico_id is null or g.servico_id = b.servico_id)
 and (b.unidade_id is null or g.unidade_id is null or g.unidade_id = b.unidade_id)
 and g.hora_inicio < b.hora_fim and b.hora_inicio < g.hora_fim
 and case when b.permanente
          then (b.dia_semana is null or g.dia_semana = b.dia_semana)
               and (g.vigencia_fim is null or g.vigencia_fim >= b.data)
          else g.dia_semana = extract(dow from b.data)
               and g.vigencia_inicio <= b.data and (g.vigencia_fim is null or g.vigencia_fim >= b.data)
     end
on conflict (bloqueio_id, horario_grade_id) do update set atualizado_em = now();

-- -----------------------------------------------------------------------------
-- c4) agendamento
-- -----------------------------------------------------------------------------
insert into novo.carga_rejeitado (script, tabela_origem, id_origem, motivo)
select 'agenda', 'bookings', b.id,
       case when not exists (select 1 from novo.aluno a where a.id = b.athlete_id) then 'aluno inexistente no destino'
            when b.service is null    then 'agendamento sem serviço'
            when b.slot_date is null  then 'agendamento sem data'
            else 'agendamento sem hora de início' end
from origem.bookings b
where not exists (select 1 from novo.aluno a where a.id = b.athlete_id)
   or b.service is null or b.slot_date is null or b.start_time is null
on conflict (script, tabela_origem, id_origem, motivo) do nothing;

create temporary table tmp_ag on commit drop as
select b.id, b.athlete_id, b.status::text as status, b.slot_date as data, b.start_time as hora_inicio,
       b.created_by, b.confirmed_at, b.created_at, b.updated_at,
       s.id as servico_id, s.codigo as servico, s.especializado,
       novo.unidade_atual_do_aluno(b.athlete_id) as unidade_id,
       b.professor_id,
       (select e.professional_id from origem.specialist_evolutions e where e.booking_id = b.id
         order by e.created_at limit 1) as prof_evolucao,
       -- duração pela regra do app (get_service_day)
       case
         when s.codigo = 'treino' and a.program = 'one_to_one' and b.start_time >= time '17:00' then 60
         when s.codigo = 'treino' and a.plan = 'express' then 30
         when s.codigo = 'treino' then coalesce(a.training_duration_min, 60)
         when s.codigo = 'fisioterapia' and a.plan = 'be_the_one' then 60
         when s.codigo = 'fisioterapia' then 15
         else 60
       end as duracao_min,
       (select max(l.created_at) from origem.activity_logs l
         where l.action = 'cancel_booking' and l.entity_id = b.id) as cancelado_em,
       (select max(l.created_at) from origem.activity_logs l
         where l.action = 'mark_attendance' and l.entity_id = b.id) as presenca_em
from origem.bookings b
join origem.athletes a on a.id = b.athlete_id
join novo.aluno al on al.id = b.athlete_id
join novo.servico s on s.codigo = pg_temp.servico_codigo(b.service::text)
where b.slot_date is not null and b.start_time is not null;

insert into novo.carga_rejeitado (script, tabela_origem, id_origem, motivo)
select 'agenda', 'bookings', t.id, 'aluno sem matrícula no destino (sem unidade)'
from tmp_ag t
where t.unidade_id is null
on conflict (script, tabela_origem, id_origem, motivo) do nothing;

insert into novo.agendamento as ag (id, aluno_id, unidade_id, servico_id, horario_grade_id, profissional_id,
                                    data, hora_inicio, hora_fim, status, criado_por, confirmado_em,
                                    cancelado_em, pendencia, criado_em)
select t.id, t.athlete_id, t.unidade_id, t.servico_id,
       (novo.grade_do_horario(t.unidade_id, t.servico_id, t.data, t.hora_inicio)).id,
       p.profissional_id,
       t.data, t.hora_inicio, f.hora_fim, t.status,
       case when exists (select 1 from novo.perfil_usuario u where u.usuario_id = t.created_by) then t.created_by end,
       t.confirmed_at,
       case when t.status = 'cancelado' then t.cancelado_em end,
       novo.juntar_pendencia(novo.juntar_pendencia(novo.juntar_pendencia(novo.juntar_pendencia(
         case when p.da_evolucao then 'profissional deduzido da evolução' end,
         case when (novo.grade_do_horario(t.unidade_id, t.servico_id, t.data, t.hora_inicio)).id is null
              then 'fora da grade reconstruída' end),
         case when f.hora_fim is null then 'fim do horário não calculado' end),
         case when t.status = 'cancelado' and t.cancelado_em is null then 'data de cancelamento desconhecida' end),
         null),
       t.created_at
from tmp_ag t
cross join lateral (
  select case when (t.hora_inicio + make_interval(mins => t.duracao_min)) > t.hora_inicio
              then t.hora_inicio + make_interval(mins => t.duracao_min) end as hora_fim
) f
cross join lateral (
  select case
           when t.professor_id is not null
                and exists (select 1 from novo.profissional pf where pf.id = t.professor_id) then t.professor_id
           when t.professor_id is null and t.especializado
                and exists (select 1 from novo.profissional pf where pf.id = t.prof_evolucao) then t.prof_evolucao
         end as profissional_id,
         (t.professor_id is null and t.especializado
          and exists (select 1 from novo.profissional pf where pf.id = t.prof_evolucao)) as da_evolucao
) p
where t.unidade_id is not null
on conflict (id) do update
  set aluno_id = excluded.aluno_id, unidade_id = excluded.unidade_id, servico_id = excluded.servico_id,
      horario_grade_id = excluded.horario_grade_id, profissional_id = excluded.profissional_id,
      data = excluded.data, hora_inicio = excluded.hora_inicio, hora_fim = excluded.hora_fim,
      status = excluded.status, criado_por = excluded.criado_por, confirmado_em = excluded.confirmado_em,
      cancelado_em = excluded.cancelado_em,
      pendencia = novo.juntar_pendencia(ag.pendencia, excluded.pendencia),
      criado_em = excluded.criado_em, atualizado_em = now();

-- Acima da capacidade: pico de ocupação dentro do intervalo de cada agendamento
-- (mesma regra do trigger do 009, que não confere durante a carga).
update novo.agendamento ag
set pendencia = novo.juntar_pendencia(ag.pendencia,
      format('horário acima da capacidade (%s de %s)', x.pico, x.cap))
from (
  select a.id, c.cap,
         (select max((select count(*) from novo.agendamento o
                       where o.servico_id = a.servico_id and o.data = a.data
                         and (c.compartilha or o.unidade_id = a.unidade_id)
                         and o.status not in ('cancelado', 'falta')
                         and o.hora_inicio <= pt.p
                         and pt.p < coalesce(o.hora_fim, o.hora_inicio + interval '60 minutes')))
            from (select a.hora_inicio as p
                  union
                  select o2.hora_inicio from novo.agendamento o2
                   where o2.servico_id = a.servico_id and o2.data = a.data
                     and (c.compartilha or o2.unidade_id = a.unidade_id)
                     and o2.status not in ('cancelado', 'falta')
                     and o2.hora_inicio > a.hora_inicio
                     and o2.hora_inicio < coalesce(a.hora_fim, a.hora_inicio + interval '60 minutes')) pt) as pico
  from novo.agendamento a
  cross join lateral (
    select coalesce(g.capacidade, case when s.especializado then 1 end,
                    (select cu.capacidade_padrao from novo.configuracao_unidade cu where cu.unidade_id = a.unidade_id)) as cap,
           coalesce(g.id is not null and g.unidade_id is null, s.especializado) as compartilha
    from novo.servico s
    left join novo.horario_grade g on g.id = a.horario_grade_id
    where s.id = a.servico_id
  ) c
  where a.status not in ('cancelado', 'falta')
) x
where ag.id = x.id and x.pico > x.cap;

-- -----------------------------------------------------------------------------
-- c5) sessao_treino: realização (treino com presença)
-- -----------------------------------------------------------------------------
insert into novo.sessao_treino as st (agendamento_id, profissional_id, data, hora_inicio, hora_fim, criado_em)
select ag.id, ag.profissional_id, ag.data, ag.hora_inicio, ag.hora_fim,
       coalesce(t.presenca_em, ag.criado_em)
from novo.agendamento ag
join tmp_ag t on t.id = ag.id
where ag.status = 'presente' and t.servico = 'treino'
on conflict (agendamento_id) do update
  set profissional_id = excluded.profissional_id, data = excluded.data,
      hora_inicio = excluded.hora_inicio, hora_fim = excluded.hora_fim,
      criado_em = excluded.criado_em, atualizado_em = now();

-- -----------------------------------------------------------------------------
-- c6) lista_espera (origem vazia na foto: só a regra)
-- -----------------------------------------------------------------------------
insert into novo.carga_rejeitado (script, tabela_origem, id_origem, motivo)
select 'agenda', 'waitlist', w.id, 'aluno inexistente no destino'
from origem.waitlist w
where not exists (select 1 from novo.aluno a where a.id = w.athlete_id)
on conflict (script, tabela_origem, id_origem, motivo) do nothing;

insert into novo.lista_espera as le (id, aluno_id, unidade_id, servico_id, data, hora_inicio, solicitante_id,
                                     status, notificado_em, expira_em, criado_em)
select w.id, w.athlete_id, novo.unidade_atual_do_aluno(w.athlete_id), s.id, w.slot_date, w.start_time,
       case when exists (select 1 from novo.perfil_usuario u where u.usuario_id = w.responsavel_id) then w.responsavel_id end,
       w.status, w.notified_at, w.expires_at, w.created_at
from origem.waitlist w
join novo.aluno a on a.id = w.athlete_id
join novo.servico s on s.codigo = pg_temp.servico_codigo(w.service::text)
on conflict (id) do update
  set status = excluded.status, notificado_em = excluded.notificado_em, expira_em = excluded.expira_em,
      atualizado_em = now();

-- -----------------------------------------------------------------------------
-- c7) feedback_treino (legado)
-- -----------------------------------------------------------------------------
insert into novo.carga_rejeitado (script, tabela_origem, id_origem, motivo)
select 'agenda', 'training_feedback', f.id, 'agendamento inexistente no destino'
from origem.training_feedback f
where not exists (select 1 from novo.agendamento a where a.id = f.booking_id)
on conflict (script, tabela_origem, id_origem, motivo) do nothing;

insert into novo.feedback_treino as fb (id, agendamento_id, nota_treino, nota_professor, gostou, comentario,
                                        pulado, criado_por, pendencia, criado_em)
select f.id, f.booking_id,
       case when f.rating_treino between 1 and 5 then f.rating_treino end,
       case when f.rating_professor between 1 and 5 then f.rating_professor end,
       f.liked, f.comentario, f.skipped,
       case when exists (select 1 from novo.perfil_usuario u where u.usuario_id = f.created_by) then f.created_by end,
       case when f.rating_treino not between 1 and 5 or f.rating_professor not between 1 and 5
            then 'nota fora da escala 1–5 (descartada)' end,
       f.created_at
from origem.training_feedback f
join novo.agendamento a on a.id = f.booking_id
on conflict (id) do update
  set nota_treino = excluded.nota_treino, nota_professor = excluded.nota_professor,
      gostou = excluded.gostou, comentario = excluded.comentario, pulado = excluded.pulado,
      criado_por = excluded.criado_por,
      pendencia = novo.juntar_pendencia(fb.pendencia, excluded.pendencia),
      criado_em = excluded.criado_em, atualizado_em = now();

-- -----------------------------------------------------------------------------
-- Registro da execução
-- -----------------------------------------------------------------------------
insert into novo.carga_execucao (script, linhas_carregadas, linhas_rejeitadas, observacao)
select 'agenda',
       (select count(*) from novo.horario_grade) + (select count(*) from novo.bloqueio_agenda)
     + (select count(*) from novo.bloqueio_grade) + (select count(*) from novo.agendamento)
     + (select count(*) from novo.sessao_treino) + (select count(*) from novo.lista_espera)
     + (select count(*) from novo.feedback_treino),
       (select count(*) from novo.carga_rejeitado where script = 'agenda'),
       format('grade %s, bloqueio %s, bloqueio_grade %s, agendamento %s (fora da grade %s, acima da capacidade %s), sessao %s, espera %s, feedback %s',
              (select count(*) from novo.horario_grade), (select count(*) from novo.bloqueio_agenda),
              (select count(*) from novo.bloqueio_grade), (select count(*) from novo.agendamento),
              (select count(*) from novo.agendamento where pendencia like '%fora da grade%'),
              (select count(*) from novo.agendamento where pendencia like '%acima da capacidade%'),
              (select count(*) from novo.sessao_treino), (select count(*) from novo.lista_espera),
              (select count(*) from novo.feedback_treino));

commit;
