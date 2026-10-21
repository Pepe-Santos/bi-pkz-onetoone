-- ESTRUTURA da origem (schema public), gerada de schema/columns.csv + enums.sql do backup de 26/08.
-- Atualizada em 15/10/2026 para ficar igual à foto de 12/10 (365 colunas; tipo e nulo conferidos coluna a coluna):
--   + app_settings.credits_fisio_standard/credits_nutri_standard; schedule_blocks.block_date passou a aceitar nulo;
--   weekday, blocos, dor_intensidade e as notas de training_feedback/weekly_evaluations passaram de smallint para integer.
-- Sem dados. Uso: testar scripts de carga num Postgres local com dados inventados.
-- Não substitui o dump congelado do ensaio. FKs para auth.users foram omitidas.
create extension if not exists pgcrypto;
do $$ begin CREATE TYPE public.app_role AS ENUM ('admin','professor','responsavel','professor_pkz','professor_one_to_one','nutricionista','psicologo','fisioterapeuta','recepcao'); exception when duplicate_object then null; end $$;
do $$ begin CREATE TYPE public.athlete_status AS ENUM ('ativo','inativo','bloqueado'); exception when duplicate_object then null; end $$;
do $$ begin CREATE TYPE public.booking_status AS ENUM ('agendado','presente','falta','cancelado','aguardando_confirmacao'); exception when duplicate_object then null; end $$;
do $$ begin CREATE TYPE public.one_to_one_plan AS ENUM ('express','one_move','one_power','one_power_legacy','be_the_one'); exception when duplicate_object then null; end $$;
do $$ begin CREATE TYPE public.service_type AS ENUM ('treino','nutricionista','psicologo','fisioterapeuta'); exception when duplicate_object then null; end $$;
do $$ begin CREATE TYPE public.student_program AS ENUM ('pkz','one_to_one'); exception when duplicate_object then null; end $$;
create table if not exists public.activity_logs (
  "id" uuid default gen_random_uuid() not null,
  "actor_id" uuid,
  "action" text not null,
  "entity" text,
  "entity_id" uuid,
  "payload" jsonb,
  "created_at" timestamp with time zone default now() not null
);
create table if not exists public.app_settings (
  "id" integer default 1 not null,
  "cancel_deadline_hours" integer default 12 not null,
  "default_capacity" integer default 6 not null,
  "low_credit_threshold" integer default 2 not null,
  "monthly_credits" integer default 8 not null,
  "renewal_day" integer default 1 not null,
  "renewal_enabled" boolean default true not null,
  "last_renewal_at" timestamp with time zone,
  "waitlist_accept_hours" integer default 2 not null,
  "renewal_weekday" integer default 1 not null,
  "auto_release_enabled" boolean default false not null,
  "auto_release_interval_minutes" integer default 60 not null,
  "contact_address" text default 'Endereço da unidade'::text,
  "contact_instagram" text default '@perfil_da_unidade'::text,
  "contact_phone" text default '21 90000-0000'::text,   -- os 3 defaults de contato foram trocados por exemplos (repositório público)
  "contact_website" text,
  "credits_fisio_standard" integer default 1,   -- coluna nova (existe na foto de 12/10, não no backup de 26/08)
  "credits_nutri_standard" integer default 1    -- idem
);
create table if not exists public.athlete_access_links (
  "id" uuid default gen_random_uuid() not null,
  "athlete_id" uuid not null,
  "user_id" uuid not null,
  "kind" text not null,
  "token" text not null,
  "status" text default 'pending'::text not null,
  "expires_at" timestamp with time zone not null,
  "used_at" timestamp with time zone,
  "created_by" uuid,
  "created_at" timestamp with time zone default now() not null,
  "updated_at" timestamp with time zone default now() not null
);
create table if not exists public.athletes (
  "id" uuid default gen_random_uuid() not null,
  "name" text not null,
  "birth_date" date,
  "category" text,
  "phone" text,
  "notes" text,
  "responsavel_id" uuid not null,
  "status" public.athlete_status default 'ativo'::athlete_status not null,
  "credits" integer default 0 not null,
  "auto_renew_enabled" boolean default false not null,
  "auto_renew_amount" integer default 0 not null,
  "auto_renew_day" integer default 1 not null,
  "last_renewed_at" timestamp with time zone,
  "created_at" timestamp with time zone default now() not null,
  "updated_at" timestamp with time zone default now() not null,
  "responsavel_secundario_id" uuid,
  "photo_url" text,
  "program" public.student_program default 'pkz'::student_program not null,
  "allowed_services" public.service_type[] default ARRAY['treino'::service_type, 'nutricionista'::service_type, 'psicologo'::service_type, 'fisioterapeuta'::service_type] not null,
  "training_duration_min" integer default 60 not null,
  "responsavel_secundario_nome" text,
  "responsavel_secundario_telefone" text,
  "monthly_plan" integer default 0 not null,
  "next_renewal_date" date,
  "plan" public.one_to_one_plan,
  "credits_fisio" integer default 0 not null,
  "credits_nutri" integer default 0 not null,
  "next_weekly_renewal" date,
  "is_trial" boolean default false not null
);
create table if not exists public.booking_audit_logs (
  "id" uuid default gen_random_uuid() not null,
  "booking_id" uuid,
  "action" text not null,
  "actor_id" uuid,
  "previous_professor_id" uuid,
  "new_professor_id" uuid,
  "reason" text,
  "created_at" timestamp with time zone default now(),
  "old_value" text,
  "new_value" text,
  "created_by" uuid
);
create table if not exists public.bookings (
  "id" uuid default gen_random_uuid() not null,
  "slot_id" uuid,
  "athlete_id" uuid not null,
  "status" public.booking_status default 'agendado'::booking_status not null,
  "created_by" uuid,
  "created_at" timestamp with time zone default now() not null,
  "updated_at" timestamp with time zone default now() not null,
  "service" public.service_type,
  "slot_date" date,
  "start_time" time without time zone,
  "professor_id" uuid,
  "confirmed_at" timestamp with time zone
);
create table if not exists public.credit_transactions (
  "id" uuid default gen_random_uuid() not null,
  "athlete_id" uuid not null,
  "delta" integer not null,
  "reason" text not null,
  "actor_id" uuid,
  "created_at" timestamp with time zone default now() not null
);
create table if not exists public.notifications (
  "id" uuid default gen_random_uuid() not null,
  "user_id" uuid not null,
  "type" text not null,
  "message" text not null,
  "read" boolean default false not null,
  "created_at" timestamp with time zone default now() not null
);
create table if not exists public.nutritionist_files (
  "id" uuid default gen_random_uuid() not null,
  "athlete_id" uuid not null,
  "file_name" text not null,
  "storage_path" text not null,
  "category" text not null,
  "mime_type" text,
  "size_bytes" bigint not null,
  "uploaded_by" uuid not null,
  "created_at" timestamp with time zone default now()
);
create table if not exists public.physical_test_comparisons (
  "id" uuid default gen_random_uuid() not null,
  "athlete_id" uuid not null,
  "session_a_id" uuid not null,
  "session_b_id" uuid not null,
  "title" text,
  "notes" text,
  "created_by" uuid,
  "created_at" timestamp with time zone default now() not null,
  "updated_at" timestamp with time zone default now() not null,
  "file_path" text
);
create table if not exists public.physical_test_sessions (
  "id" uuid default gen_random_uuid() not null,
  "athlete_id" uuid not null,
  "test_date" date not null,
  "evaluator_id" uuid,
  "evaluator_name" text,
  "altura" numeric,
  "peso" numeric,
  "data" jsonb default '{}'::jsonb not null,
  "observacoes" text,
  "created_by" uuid,
  "created_at" timestamp with time zone default now() not null,
  "updated_at" timestamp with time zone default now() not null
);
create table if not exists public.physio_assessments (
  "id" uuid default gen_random_uuid() not null,
  "athlete_id" uuid not null,
  "physio_id" uuid,
  "physio_name" text,
  "assessment_date" date default CURRENT_DATE not null,
  "cpf" text,
  "endereco" text,
  "profissao" text,
  "sexo" text,
  "email" text,
  "telefone" text,
  "diagnostico_clinico" text,
  "queixa_principal" text,
  "hda" text,
  "hpp_doencas" text,
  "hpp_cirurgias" text,
  "hpp_fraturas" text,
  "hpp_entorses" text,
  "hab_freq_treinos" text,
  "hab_outras_atividades" text,
  "hab_alcool" text,
  "hab_tabagista" text,
  "hab_medicamentos" text,
  "fam_materna" text,
  "fam_paterna" text,
  "exames_complementares" text,
  "ombro_rot_ext_dir" numeric,
  "ombro_rot_ext_esq" numeric,
  "appley_dir_sup" text,
  "appley_dir_inf" text,
  "appley_esq_sup" text,
  "appley_esq_inf" text,
  "quadril_dir" numeric,
  "quadril_esq" numeric,
  "cotovelo_ext_dir" numeric,
  "cotovelo_ext_esq" numeric,
  "cotovelo_flex_dir" numeric,
  "cotovelo_flex_esq" numeric,
  "ombro_abd_dir" numeric,
  "ombro_abd_esq" numeric,
  "joelho_ext_dir" numeric,
  "joelho_ext_esq" numeric,
  "joelho_flex_dir" numeric,
  "joelho_flex_esq" numeric,
  "diagnostico_funcional" text,
  "observacao" text,
  "file_path" text,
  "status" text default 'rascunho'::text not null,
  "created_by" uuid,
  "created_at" timestamp with time zone default now() not null,
  "updated_at" timestamp with time zone default now() not null,
  "program" public.student_program,
  "pkz_data" jsonb default '{}'::jsonb not null
);
create table if not exists public.physio_evolutions (
  "id" uuid default gen_random_uuid() not null,
  "athlete_id" uuid not null,
  "physio_id" uuid not null,
  "file_name" text not null,
  "storage_path" text not null,
  "created_at" timestamp with time zone default now() not null
);
create table if not exists public.profiles (
  "id" uuid not null,
  "full_name" text default ''::text not null,
  "phone" text,
  "active" boolean default true not null,
  "created_at" timestamp with time zone default now() not null,
  "updated_at" timestamp with time zone default now() not null,
  "username" text not null,
  "status" text default 'ativo'::text not null,
  "avatar_url" text,
  "can_schedule" boolean default false not null,
  "must_change_password" boolean default false not null,
  "can_train" boolean default false
);
create table if not exists public.registration_invites (
  "id" uuid default gen_random_uuid() not null,
  "token" text not null,
  "program" public.student_program not null,
  "monthly_plan" integer default 0 not null,
  "plan" public.one_to_one_plan,
  "status" text default 'pending'::text not null,
  "expires_at" timestamp with time zone default (now() + '30 days'::interval) not null,
  "created_by" uuid,
  "used_at" timestamp with time zone,
  "athlete_id" uuid,
  "created_at" timestamp with time zone default now() not null,
  "updated_at" timestamp with time zone default now() not null,
  "athlete_name" text
);
create table if not exists public.schedule_blocks (
  "id" uuid default gen_random_uuid() not null,
  "service" public.service_type,
  "program" public.student_program,
  "block_date" date,
  "start_time" time without time zone not null,
  "end_time" time without time zone not null,
  "reason" text,
  "created_by" uuid,
  "created_at" timestamp with time zone default now() not null,
  "updated_at" timestamp with time zone default now() not null,
  "is_permanent" boolean default false not null,
  "weekday" integer
);
create table if not exists public.specialist_evolutions (
  "id" uuid default gen_random_uuid() not null,
  "booking_id" uuid not null,
  "athlete_id" uuid not null,
  "professional_id" uuid not null,
  "service" public.service_type not null,
  "file_path" text not null,
  "file_name" text not null,
  "created_at" timestamp with time zone default now() not null
);
create table if not exists public.student_files (
  "id" uuid default gen_random_uuid() not null,
  "athlete_id" uuid not null,
  "folder" text default 'arquivos'::text not null,
  "file_name" text not null,
  "storage_path" text not null,
  "mime_type" text,
  "size_bytes" bigint not null,
  "uploaded_by" uuid,
  "created_at" timestamp with time zone default now() not null
);
create table if not exists public.student_tests (
  "id" uuid default gen_random_uuid() not null,
  "athlete_id" uuid not null,
  "test_type" text not null,
  "test_date" date not null,
  "professor_id" uuid,
  "result" numeric,
  "unit" text,
  "notes" text,
  "file_path" text,
  "created_by" uuid,
  "created_at" timestamp with time zone default now() not null,
  "updated_at" timestamp with time zone default now() not null
);
create table if not exists public.student_timeline (
  "id" uuid default gen_random_uuid() not null,
  "athlete_id" uuid not null,
  "event_type" text not null,
  "title" text not null,
  "description" text,
  "actor_id" uuid,
  "ref_type" text,
  "ref_id" uuid,
  "created_at" timestamp with time zone default now() not null
);
create table if not exists public.training_feedback (
  "id" uuid default gen_random_uuid() not null,
  "booking_id" uuid not null,
  "athlete_id" uuid not null,
  "rating_treino" integer,
  "rating_professor" integer,
  "liked" text[] default '{}'::text[] not null,
  "comentario" text,
  "skipped" boolean default false not null,
  "created_by" uuid,
  "created_at" timestamp with time zone default now() not null
);
create table if not exists public.training_report_materials (
  "id" uuid default gen_random_uuid() not null,
  "name" text not null,
  "active" boolean default true not null,
  "sort_order" integer default 0 not null,
  "created_at" timestamp with time zone default now() not null,
  "updated_at" timestamp with time zone default now() not null
);
create table if not exists public.training_report_technologies (
  "id" uuid default gen_random_uuid() not null,
  "name" text not null,
  "active" boolean default true not null,
  "sort_order" integer default 0 not null,
  "created_at" timestamp with time zone default now() not null,
  "updated_at" timestamp with time zone default now() not null
);
create table if not exists public.training_reports (
  "id" uuid default gen_random_uuid() not null,
  "athlete_id" uuid not null,
  "report_date" date not null,
  "category" text,
  "professor_id" uuid,
  "notes" text,
  "file_path" text,
  "created_by" uuid,
  "created_at" timestamp with time zone default now() not null,
  "updated_at" timestamp with time zone default now() not null,
  "title" text,
  "athlete_group" text,
  "local" text,
  "training_type" text,
  "session_number" integer,
  "start_time" time without time zone,
  "end_time" time without time zone,
  "materials" text[] default '{}'::text[] not null,
  "materials_other" text,
  "technologies" text[] default '{}'::text[] not null,
  "technologies_other" text,
  "capacidades_fisicas" text[] default '{}'::text[] not null,
  "capacidades_tecnicas" text[] default '{}'::text[] not null,
  "capacidades_cognitivas" text[] default '{}'::text[] not null,
  "intensidade" text,
  "blocos" integer,
  "objetivos" text,
  "analise_html" text,
  "observacoes" text,
  "evolucao" text,
  "exercicios" jsonb default '[]'::jsonb not null,
  "status" text default 'rascunho'::text not null,
  "pdf_storage_path" text,
  "booking_id" uuid,
  "report_kind" text default 'pkz'::text not null,
  "objetivo_sessao" text[] default '{}'::text[] not null,
  "foco" text[] default '{}'::text[] not null,
  "desempenho" text,
  "dor" text,
  "dor_local" text,
  "dor_intensidade" integer,
  "dor_movimento" text,
  "conduta" text[] default '{}'::text[] not null
);
create table if not exists public.training_slots (
  "id" uuid default gen_random_uuid() not null,
  "slot_date" date not null,
  "start_time" time without time zone not null,
  "end_time" time without time zone not null,
  "capacity" integer default 6 not null,
  "professor_id" uuid,
  "notes" text,
  "created_at" timestamp with time zone default now() not null,
  "updated_at" timestamp with time zone default now() not null
);
create table if not exists public.user_roles (
  "id" uuid default gen_random_uuid() not null,
  "user_id" uuid not null,
  "role" public.app_role not null,
  "created_at" timestamp with time zone default now() not null
);
create table if not exists public.waitlist (
  "id" uuid default gen_random_uuid() not null,
  "service" public.service_type not null,
  "slot_date" date not null,
  "start_time" time without time zone not null,
  "athlete_id" uuid not null,
  "responsavel_id" uuid not null,
  "status" text default 'aguardando'::text not null,
  "notified_at" timestamp with time zone,
  "expires_at" timestamp with time zone,
  "created_at" timestamp with time zone default now() not null
);
create table if not exists public.weekly_evaluations (
  "id" uuid default gen_random_uuid() not null,
  "athlete_id" uuid not null,
  "week_start_date" date not null,
  "rating_quality" integer not null,
  "rating_service" integer not null,
  "rating_environment" integer not null,
  "rating_evolution" integer not null,
  "rating_satisfaction" integer not null,
  "observations" text,
  "unit" public.student_program not null,
  "created_at" timestamp with time zone default now() not null,
  "created_by" uuid
);
