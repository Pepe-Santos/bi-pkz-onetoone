-- =============================================================================
-- 009_ajuste_mapeamento.sql
-- Ajustes no DDL encontrados no mapeamento (tarefa 1.3, 14/10/2026) e na revisão
-- das tarefas 1.1–1.3 (15/10/2026). Dono: Micael (Frente 1).
-- Pré-requisito: 008_documentos_auditoria.sql. Os scripts de carga 10–80 dependem
-- desta migration.
--
-- Agenda e capacidade
--   1. horario_grade.unidade_id aceita nulo = grade COMPARTILHADA entre as unidades
--      (fisioterapia, nutrição e psicologia: no app a vaga é uma só). Chave única
--      com nulls not distinct.
--   2. horario_grade.intervalo_min: de quanto em quanto tempo começam os horários.
--   3. Capacidade conferida no INTERVALO INTEIRO do agendamento [início, fim):
--      em nenhum momento a sala pode passar da capacidade (decisão de 15/10; o app
--      só olha o horário de início). Serviço especializado sem grade = capacidade 1
--      compartilhada (antes caía na capacidade padrão do treino).
-- Comercial
--   4. configuracao_unidade + creditos_fisio_padrao / creditos_nutri_padrao
--      (colunas novas de app_settings).
--   5. renovacao: a chave passa a incluir a periodicidade (semanal e mensal de
--      treino podem cair na mesma data) e periodicidade vira obrigatória.
--   6. matricula: o plano tem de ser da mesma unidade da matrícula.
--   7. unidade_atual_do_aluno / vw_matricula_vigente: só matrícula já iniciada.
-- Avaliação
--   8. corrige_avaliacao_id só aponta para avaliação consolidada do mesmo aluno e tipo.
--   9. truncate bloqueado em avaliacao / avaliacao_medida (fora do modo de carga).
-- Segurança e robustez
--  10. em_modo_carga() só vale para quem é membro do papel postgres (quem roda a
--      carga). Antes, qualquer sessão podia ligar o modo e editar avaliação consolidada.
--  11. search_path fixo (vazio) em todas as funções de novo (todas usam nomes
--      qualificados). Regra para as próximas: ver CONVENCOES.md §6.
--  12. Funções do 001 mais robustas: espaços/quebras de linha nas pontas,
--      mm:ss com minutos absurdos (antes dava erro em vez de nulo), pendência
--      composta ("a; b") sem duplicar.
--
-- Registro (não muda nada): o comentário "aplica: PROFISSIONAL 0,N" no 006 se refere
-- ao lado do profissional; do lado da avaliação a cardinalidade é (1,1) e foi
-- relaxada para nulo (avaliação semanal não tem avaliador). Ver PENDENCIAS.md.
--
-- Atenção: tem "drop constraint" (troca de chaves únicas). O conector do Supabase
-- pede confirmação para isso.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 12. Funções do 001
-- ---------------------------------------------------------------------------
create or replace function novo.texto_para_numero(p text)
returns numeric
language sql
immutable
as $$
  select case
    when regexp_replace(p, '^\s+|\s+$', '', 'g') ~ '^-?\d+([.,]\d+)?$'
      then replace(regexp_replace(p, '^\s+|\s+$', '', 'g'), ',', '.')::numeric
  end;
$$;
comment on function novo.texto_para_numero(text) is
  'Texto -> numeric. Vírgula ou ponto é sempre DECIMAL (como no app): ''1,234'' = 1.234. Nulo se não for número.';

create or replace function novo.mmss_para_segundos(p text)
returns int
language sql
immutable
as $$
  select case
    when regexp_replace(p, '^\s+|\s+$', '', 'g') ~ '^\d{1,5}:[0-5]\d$'
      then split_part(regexp_replace(p, '^\s+|\s+$', '', 'g'), ':', 1)::int * 60
         + split_part(regexp_replace(p, '^\s+|\s+$', '', 'g'), ':', 2)::int
  end;
$$;

create or replace function novo.juntar_pendencia(p_atual text, p_nova text)
returns text
language plpgsql
immutable
as $$
declare
  v_res   text := nullif(p_atual, '');
  v_parte text;
begin
  if p_nova is null or p_nova = '' then
    return p_atual;
  end if;
  foreach v_parte in array string_to_array(p_nova, '; ') loop
    continue when v_parte = '';
    if v_res is null then
      v_res := v_parte;
    elsif not v_parte = any (string_to_array(v_res, '; ')) then
      v_res := v_res || '; ' || v_parte;
    end if;
  end loop;
  return v_res;
end;
$$;

-- ---------------------------------------------------------------------------
-- 10. Modo de carga só para quem roda a carga
-- ---------------------------------------------------------------------------
create or replace function novo.em_modo_carga()
returns boolean
language sql
stable
as $$
  select coalesce(current_setting('novo.modo_carga', true), '') = 'on'
     and pg_catalog.pg_has_role(current_user, 'postgres', 'member');
$$;
comment on function novo.em_modo_carga() is
  'Verdadeiro só quando a transação ligou novo.modo_carga E o usuário é membro do papel postgres (quem roda os scripts de carga).';

-- ---------------------------------------------------------------------------
-- 4. Créditos padrão de fisio e nutri
-- ---------------------------------------------------------------------------
alter table novo.configuracao_unidade
  add column creditos_fisio_padrao int,
  add column creditos_nutri_padrao int;
comment on column novo.configuracao_unidade.creditos_fisio_padrao is 'Origem: app_settings.credits_fisio_standard.';
comment on column novo.configuracao_unidade.creditos_nutri_padrao is 'Origem: app_settings.credits_nutri_standard.';

-- ---------------------------------------------------------------------------
-- 1–2. Grade compartilhada e intervalo
-- ---------------------------------------------------------------------------
alter table novo.horario_grade alter column unidade_id drop not null;
alter table novo.horario_grade
  drop constraint horario_grade_unidade_id_servico_id_dia_semana_hora_inicio__key;
alter table novo.horario_grade
  add constraint horario_grade_chave
  unique nulls not distinct (unidade_id, servico_id, dia_semana, hora_inicio, vigencia_inicio);
alter table novo.horario_grade
  add column intervalo_min smallint not null default 30 check (intervalo_min in (15, 30, 60));
comment on column novo.horario_grade.unidade_id is
  'Nulo = grade compartilhada entre as unidades (a vaga é a mesma para PKZ e One to One). Divergência registrada do conceitual ("oferece" é 1,1).';
comment on column novo.horario_grade.intervalo_min is
  'Minutos entre os inícios de horário: 15 (fisio), 30 (nutri, psico, One to One antes das 17h) ou 60.';

-- ---------------------------------------------------------------------------
-- 3. Capacidade no intervalo inteiro
-- ---------------------------------------------------------------------------
-- Grade que vale para o horário: a da unidade ou, se não houver, a compartilhada.
create or replace function novo.grade_do_horario(p_unidade uuid, p_servico uuid, p_data date, p_hora time)
returns novo.horario_grade
language sql
stable
as $$
  select g.*
  from novo.horario_grade g
  where (g.unidade_id = p_unidade or g.unidade_id is null)
    and g.servico_id = p_servico
    and g.dia_semana = extract(dow from p_data)
    and p_hora >= g.hora_inicio and p_hora < g.hora_fim
    and p_data >= g.vigencia_inicio and (g.vigencia_fim is null or p_data <= g.vigencia_fim)
  order by (g.unidade_id is null), g.vigencia_inicio desc
  limit 1;
$$;

-- Capacidade no horário: a da grade; sem grade, 1 para serviço especializado e a
-- capacidade padrão da unidade para treino.
create or replace function novo.capacidade_do_horario(p_unidade uuid, p_servico uuid, p_data date, p_hora time)
returns int
language sql
stable
as $$
  select coalesce(
    (novo.grade_do_horario(p_unidade, p_servico, p_data, p_hora)).capacidade,
    case when (select s.especializado from novo.servico s where s.id = p_servico) then 1 end,
    (select c.capacidade_padrao from novo.configuracao_unidade c where c.unidade_id = p_unidade)
  );
$$;

create or replace function novo.conferir_capacidade_agendamento()
returns trigger
language plpgsql
as $$
declare
  v_grade       novo.horario_grade;
  v_cap         int;
  v_pico        int;
  v_compartilha boolean;
  v_ini         time := new.hora_inicio;
  v_fim         time := coalesce(new.hora_fim, new.hora_inicio + interval '60 minutes');
begin
  if novo.em_modo_carga() or new.status in ('cancelado', 'falta') then
    return new;
  end if;
  if tg_op = 'UPDATE'
     and old.status not in ('cancelado', 'falta')
     and (old.unidade_id, old.servico_id, old.data, old.hora_inicio, old.hora_fim)
         is not distinct from (new.unidade_id, new.servico_id, new.data, new.hora_inicio, new.hora_fim) then
    return new;
  end if;
  if v_fim <= v_ini then
    v_fim := time '23:59:59.999999';   -- passou da meia-noite
  end if;

  v_grade := novo.grade_do_horario(new.unidade_id, new.servico_id, new.data, new.hora_inicio);
  if v_grade.id is not null then
    v_cap         := v_grade.capacidade;
    v_compartilha := v_grade.unidade_id is null;
  elsif (select s.especializado from novo.servico s where s.id = new.servico_id) then
    v_cap         := 1;
    v_compartilha := true;
  else
    v_cap         := (select c.capacidade_padrao from novo.configuracao_unidade c where c.unidade_id = new.unidade_id);
    v_compartilha := false;
  end if;
  if v_cap is null then
    return new;
  end if;

  perform pg_advisory_xact_lock(hashtextextended(
    case when v_compartilha then '' else new.unidade_id::text end
    || new.servico_id::text || new.data::text, 0));

  -- pico de ocupação dentro de [v_ini, v_fim): a ocupação só sobe no início de
  -- algum agendamento, então basta olhar v_ini e os inícios dentro do intervalo
  with ativos as (
    select a.hora_inicio as ini,
           coalesce(a.hora_fim, a.hora_inicio + interval '60 minutes') as fim
    from novo.agendamento a
    where a.servico_id = new.servico_id
      and a.data = new.data
      and (v_compartilha or a.unidade_id = new.unidade_id)
      and a.status not in ('cancelado', 'falta')
      and a.id <> new.id
      and a.hora_inicio < v_fim
      and coalesce(a.hora_fim, a.hora_inicio + interval '60 minutes') > v_ini
  ),
  pontos as (
    select v_ini as p
    union
    select ini from ativos where ini > v_ini
  )
  select coalesce(max((select count(*) from ativos x where x.ini <= pt.p and pt.p < x.fim)), 0)
  into v_pico
  from pontos pt;

  if v_pico >= v_cap then
    raise exception 'Horário lotado: % de % vagas ocupadas entre % e % (%).', v_pico, v_cap, v_ini, v_fim, new.data
      using errcode = 'check_violation';
  end if;
  return new;
end;
$$;

create or replace trigger tg_capacidade
before insert or update of status, unidade_id, servico_id, data, hora_inicio, hora_fim on novo.agendamento
for each row execute function novo.conferir_capacidade_agendamento();

-- ---------------------------------------------------------------------------
-- 5. Renovação: chave com periodicidade
-- ---------------------------------------------------------------------------
alter table novo.renovacao alter column periodicidade set not null;
alter table novo.renovacao drop constraint renovacao_aluno_id_servico_id_competencia_key;
alter table novo.renovacao
  add constraint renovacao_chave unique (aluno_id, servico_id, periodicidade, competencia);

-- ---------------------------------------------------------------------------
-- 6. Plano da mesma unidade da matrícula
-- ---------------------------------------------------------------------------
create or replace function novo.conferir_plano_da_unidade()
returns trigger
language plpgsql
as $$
begin
  if not exists (select 1 from novo.plano p where p.id = new.plano_id and p.unidade_id = new.unidade_id) then
    raise exception 'O plano da matrícula é de outra unidade.' using errcode = 'check_violation';
  end if;
  return new;
end;
$$;

create or replace trigger tg_plano_da_unidade
before insert or update of plano_id, unidade_id on novo.matricula
for each row execute function novo.conferir_plano_da_unidade();

-- ---------------------------------------------------------------------------
-- 7. Matrícula vigente = já iniciada e não encerrada
-- ---------------------------------------------------------------------------
create or replace function novo.unidade_atual_do_aluno(p_aluno_id uuid)
returns uuid
language sql
stable
as $$
  select m.unidade_id
  from novo.matricula m
  where m.aluno_id = p_aluno_id
  order by (m.vigencia_inicio <= current_date
            and (m.vigencia_fim is null or m.vigencia_fim >= current_date)) desc,
           m.vigencia_inicio desc
  limit 1;
$$;

create or replace view novo.vw_matricula_vigente
with (security_invoker = true)
as
select m.*
from novo.matricula m
where m.vigencia_inicio <= current_date
  and (m.vigencia_fim is null or m.vigencia_fim >= current_date);

-- ---------------------------------------------------------------------------
-- 8. Correção de avaliação coerente
-- ---------------------------------------------------------------------------
create or replace function novo.conferir_correcao_avaliacao()
returns trigger
language plpgsql
as $$
begin
  if new.corrige_avaliacao_id is not null and not exists (
       select 1 from novo.avaliacao a
       where a.id = new.corrige_avaliacao_id
         and a.aluno_id = new.aluno_id
         and a.tipo = new.tipo
         and a.status = 'consolidada') then
    raise exception 'corrige_avaliacao_id precisa apontar para uma avaliação consolidada do mesmo aluno e tipo.'
      using errcode = 'check_violation';
  end if;
  return new;
end;
$$;

create or replace trigger tg_correcao
before insert or update of corrige_avaliacao_id, aluno_id, tipo on novo.avaliacao
for each row execute function novo.conferir_correcao_avaliacao();

-- ---------------------------------------------------------------------------
-- 9. Truncate bloqueado nas tabelas imutáveis
-- ---------------------------------------------------------------------------
create or replace function novo.bloquear_truncate()
returns trigger
language plpgsql
as $$
begin
  if not novo.em_modo_carga() then
    raise exception 'truncate em % não é permitido (avaliações são imutáveis).', tg_table_name
      using errcode = 'check_violation';
  end if;
  return null;
end;
$$;

create or replace trigger tg_sem_truncate
before truncate on novo.avaliacao
for each statement execute function novo.bloquear_truncate();

create or replace trigger tg_sem_truncate
before truncate on novo.avaliacao_medida
for each statement execute function novo.bloquear_truncate();

-- ---------------------------------------------------------------------------
-- 11. search_path fixo em todas as funções de novo
-- ---------------------------------------------------------------------------
do $$
declare f regprocedure;
begin
  for f in select p.oid::regprocedure from pg_proc p where p.pronamespace = 'novo'::regnamespace loop
    execute format('alter function %s set search_path = %L', f, '');
  end loop;
end;
$$;
