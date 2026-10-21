-- =============================================================================
-- 20_carga_cadastro.sql
-- Domínio: cadastro                Dono: Micael (Frente 1)
-- Origem:  origem.athletes, origem.profiles, origem.user_roles, e (só para saber
--          quem atua como profissional) bookings, training_reports,
--          physical_test_sessions, physio_assessments, physio_evolutions,
--          specialist_evolutions
-- Destino: novo.pessoa, perfil_usuario, papel_usuario, aluno, aluno_servico,
--          responsavel_aluno, profissional, profissional_servico
-- Depende de: 10_carga_referencia
-- Mapeamento: mapeamento/cadastro.csv
-- =============================================================================
\set ON_ERROR_STOP on

begin;

select set_config('novo.modo_carga', 'on', true);

-- Funções auxiliares só desta sessão (somem no fim da conexão).
-- Nome comparável: minúsculas, sem acento, espaços simples.
create or replace function pg_temp.normaliza(t text) returns text language sql immutable as $$
  select lower(translate(regexp_replace(btrim(t), '\s+', ' ', 'g'),
         'ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇáàâãäéèêëíìîïóòôõöúùûüç',
         'AAAAAEEEEIIIIOOOOOUUUUCaaaaaeeeeiiiiooooouuuuc'));
$$;
-- service_type da origem → codigo de novo.servico
create or replace function pg_temp.servico_codigo(t text) returns text language sql immutable as $$
  select case t when 'treino' then 'treino' when 'fisioterapeuta' then 'fisioterapia'
                when 'nutricionista' then 'nutricao' when 'psicologo' then 'psicologia' end;
$$;

-- Rejeitados não são apagados antes: a chave única (010) + on conflict do nothing
-- evitam duplicar na reexecução.

-- -----------------------------------------------------------------------------
-- b) Rejeitados (não dá para gravar sem quebrar uma FK)
-- -----------------------------------------------------------------------------
insert into novo.carga_rejeitado (script, tabela_origem, id_origem, motivo)
select 'cadastro', 'user_roles', r.id, 'papel de usuário sem perfil em profiles'
from origem.user_roles r
where not exists (select 1 from origem.profiles p where p.id = r.user_id)
on conflict (script, tabela_origem, id_origem, motivo) do nothing;

insert into novo.carga_rejeitado (script, tabela_origem, id_origem, motivo)
select 'cadastro', 'athletes', a.id, 'responsável principal sem perfil em profiles: o aluno entra sem esse vínculo'
from origem.athletes a
where not exists (select 1 from origem.profiles p where p.id = a.responsavel_id)
on conflict (script, tabela_origem, id_origem, motivo) do nothing;

insert into novo.carga_rejeitado (script, tabela_origem, id_origem, motivo)
select 'cadastro', 'athletes', a.id, 'responsável secundário sem perfil em profiles: vínculo não entra'
from origem.athletes a
where a.responsavel_secundario_id is not null
  and not exists (select 1 from origem.profiles p where p.id = a.responsavel_secundario_id)
on conflict (script, tabela_origem, id_origem, motivo) do nothing;

-- -----------------------------------------------------------------------------
-- c) pessoa
-- -----------------------------------------------------------------------------
-- alunos: pessoa.id = athletes.id
insert into novo.pessoa as p (id, nome, data_nascimento, telefone, foto_url, origem_tabela, origem_id, criado_em)
select a.id, btrim(a.name), a.birth_date, nullif(btrim(a.phone), ''), nullif(btrim(a.photo_url), ''),
       'athletes', a.id, a.created_at
from origem.athletes a
on conflict (id) do update
  set nome = excluded.nome, data_nascimento = excluded.data_nascimento,
      telefone = excluded.telefone, foto_url = excluded.foto_url,
      origem_tabela = excluded.origem_tabela, origem_id = excluded.origem_id,
      criado_em = excluded.criado_em, atualizado_em = now();

-- usuários: pessoa.id = profiles.id
insert into novo.pessoa as p (id, nome, telefone, foto_url, origem_tabela, origem_id, pendencia, criado_em)
select pr.id, coalesce(nullif(btrim(pr.full_name), ''), pr.username),
       nullif(btrim(pr.phone), ''), nullif(btrim(pr.avatar_url), ''),
       'profiles', pr.id,
       case when nullif(btrim(pr.full_name), '') is null then 'nome vazio na origem: usado o username' end,
       pr.created_at
from origem.profiles pr
on conflict (id) do update
  set nome = excluded.nome, telefone = excluded.telefone, foto_url = excluded.foto_url,
      origem_tabela = excluded.origem_tabela, origem_id = excluded.origem_id,
      pendencia = novo.juntar_pendencia(p.pendencia, excluded.pendencia),
      criado_em = excluded.criado_em, atualizado_em = now();

-- responsável secundário só em texto (sem perfil): pessoa nova
insert into novo.pessoa as p (nome, telefone, origem_tabela, origem_id, criado_em)
select btrim(a.responsavel_secundario_nome), nullif(btrim(a.responsavel_secundario_telefone), ''),
       'athletes.responsavel_secundario', a.id, a.created_at
from origem.athletes a
where a.responsavel_secundario_id is null
  and nullif(btrim(a.responsavel_secundario_nome), '') is not null
on conflict (origem_tabela, origem_id) do update
  set nome = excluded.nome, telefone = excluded.telefone, atualizado_em = now();

-- possível pessoa duplicada: adulto do One to One com o mesmo nome do responsável
update novo.pessoa pe
set pendencia = novo.juntar_pendencia(pe.pendencia, 'possível pessoa duplicada (aluno adulto = responsável)')
from origem.athletes a
join origem.profiles pr on pr.id = a.responsavel_id
where pe.id = a.id
  and a.program = 'one_to_one'
  and pg_temp.normaliza(a.name) = pg_temp.normaliza(pr.full_name);

-- -----------------------------------------------------------------------------
-- d) perfil_usuario
-- -----------------------------------------------------------------------------
insert into novo.perfil_usuario as u (usuario_id, pessoa_id, username, status, ativo, trocar_senha,
                                      pode_agendar, pode_treinar, criado_em)
select pr.id, pr.id, pr.username, pr.status, pr.active, pr.must_change_password,
       pr.can_schedule, coalesce(pr.can_train, false), pr.created_at
from origem.profiles pr
on conflict (usuario_id) do update
  set pessoa_id = excluded.pessoa_id, username = excluded.username, status = excluded.status,
      ativo = excluded.ativo, trocar_senha = excluded.trocar_senha,
      pode_agendar = excluded.pode_agendar, pode_treinar = excluded.pode_treinar,
      criado_em = excluded.criado_em, atualizado_em = now();

-- -----------------------------------------------------------------------------
-- e) papel_usuario: 9 papéis → 5; professor_pkz/one_to_one guardam a unidade
-- -----------------------------------------------------------------------------
insert into novo.papel_usuario as pu (usuario_id, papel_id, unidade_id, desde, papel_origem, pendencia, criado_em)
select r.user_id, pa.id, un.id,
       (min(r.created_at) at time zone 'America/Sao_Paulo')::date,
       string_agg(distinct r.role::text, ',' order by r.role::text),
       case when bool_or(r.role::text = 'recepcao') then 'papel recepção sem destino definido na proposta' end,
       min(r.created_at)
from origem.user_roles r
join origem.profiles pr on pr.id = r.user_id
join novo.papel pa on pa.codigo = case r.role::text
       when 'admin'                then 'admin'
       when 'professor'            then 'professor'
       when 'professor_pkz'        then 'professor'
       when 'professor_one_to_one' then 'professor'
       when 'nutricionista'        then 'especialista'
       when 'psicologo'            then 'especialista'
       when 'fisioterapeuta'       then 'especialista'
       when 'responsavel'          then 'responsavel'
       when 'recepcao'             then 'recepcao' end
left join novo.unidade un on un.codigo = case r.role::text
       when 'professor_pkz' then 'pkz' when 'professor_one_to_one' then 'one_to_one' end
group by r.user_id, pa.id, un.id
on conflict (usuario_id, papel_id, unidade_id) do update
  set desde = excluded.desde, papel_origem = excluded.papel_origem,
      pendencia = novo.juntar_pendencia(pu.pendencia, excluded.pendencia),
      criado_em = excluded.criado_em, atualizado_em = now();

-- -----------------------------------------------------------------------------
-- f) aluno (categoria normalizada; a original fica guardada)
-- -----------------------------------------------------------------------------
insert into novo.aluno as al (id, pessoa_id, status, data_entrada, categoria, categoria_original,
                              observacao, pendencia, criado_em)
select a.id, a.id, a.status::text,
       (a.created_at at time zone 'America/Sao_Paulo')::date,
       case
         when c.cat is null or c.cat = ''   then null
         when c.cat ~ '^sub ?[0-9]+$'       then 'sub_' || substring(c.cat from '[0-9]+')
         when c.cat ~ '^[0-9]+$'            then 'sub_' || c.cat
         else regexp_replace(c.cat, ' ', '_', 'g')
       end,
       a.category, a.notes,
       novo.juntar_pendencia('data de entrada aproximada (= criação do cadastro)',
                             case when c.cat ~ '^[0-9]+$' then 'categoria só com número: confirmar se é sub-N' end),
       a.created_at
from origem.athletes a
cross join lateral (select pg_temp.normaliza(a.category) as cat) c
on conflict (id) do update
  set pessoa_id = excluded.pessoa_id, status = excluded.status, data_entrada = excluded.data_entrada,
      categoria = excluded.categoria, categoria_original = excluded.categoria_original,
      observacao = excluded.observacao,
      pendencia = novo.juntar_pendencia(al.pendencia, excluded.pendencia),
      criado_em = excluded.criado_em, atualizado_em = now();

-- -----------------------------------------------------------------------------
-- g) aluno_servico (allowed_services)
-- -----------------------------------------------------------------------------
insert into novo.aluno_servico (aluno_id, servico_id, criado_em)
select distinct on (a.id, s.id) a.id, s.id, a.created_at
from origem.athletes a
cross join lateral unnest(a.allowed_services) sv
join novo.servico s on s.codigo = pg_temp.servico_codigo(sv::text)
on conflict (aluno_id, servico_id) do update set atualizado_em = now();

-- -----------------------------------------------------------------------------
-- h) responsavel_aluno
-- -----------------------------------------------------------------------------
-- principal
insert into novo.responsavel_aluno as ra (aluno_id, pessoa_id, tipo_vinculo, principal, pode_agendar, pendencia, criado_em)
select a.id, a.responsavel_id,
       case when d.duplicado then 'proprio' else 'responsavel' end,
       true, true,
       case when d.duplicado then 'possível pessoa duplicada (aluno adulto = responsável)' end,
       a.created_at
from origem.athletes a
join origem.profiles pr on pr.id = a.responsavel_id
cross join lateral (select a.program = 'one_to_one'
                           and pg_temp.normaliza(a.name) = pg_temp.normaliza(pr.full_name) as duplicado) d
on conflict (aluno_id, pessoa_id) do update
  set tipo_vinculo = excluded.tipo_vinculo, principal = excluded.principal,
      pendencia = novo.juntar_pendencia(ra.pendencia, excluded.pendencia),
      criado_em = excluded.criado_em, atualizado_em = now();

-- secundário com perfil (ligação); se o texto também existir e discordar, vale a ligação
insert into novo.responsavel_aluno as ra (aluno_id, pessoa_id, tipo_vinculo, principal, pode_agendar, pendencia, criado_em)
select a.id, a.responsavel_secundario_id, 'responsavel', false, true,
       case when nullif(btrim(a.responsavel_secundario_nome), '') is not null
             and pg_temp.normaliza(a.responsavel_secundario_nome) <> pg_temp.normaliza(pr.full_name)
            then 'responsável secundário: ligação e texto discordam' end,
       a.created_at
from origem.athletes a
join origem.profiles pr on pr.id = a.responsavel_secundario_id
where a.responsavel_secundario_id <> a.responsavel_id
on conflict (aluno_id, pessoa_id) do update
  set pendencia = novo.juntar_pendencia(ra.pendencia, excluded.pendencia), atualizado_em = now();

-- secundário só em texto
insert into novo.responsavel_aluno as ra (aluno_id, pessoa_id, tipo_vinculo, principal, pode_agendar, criado_em)
select a.id, pe.id, 'responsavel', false, true, a.created_at
from origem.athletes a
join novo.pessoa pe on pe.origem_tabela = 'athletes.responsavel_secundario' and pe.origem_id = a.id
on conflict (aluno_id, pessoa_id) do update set atualizado_em = now();

-- -----------------------------------------------------------------------------
-- i) profissional e j) profissional_servico
--    Quem tem papel de professor/especialista: serviços pelo papel.
--    Quem não tem (na foto, só admins) mas aparece atuando: serviços de onde aparece.
-- -----------------------------------------------------------------------------
create temporary table tmp_prof_servico on commit drop as
with por_papel as (
  select r.user_id as id,
         case when r.role::text in ('professor', 'professor_pkz', 'professor_one_to_one') then 'treino'
              else pg_temp.servico_codigo(r.role::text) end as servico,
         r.created_at
  from origem.user_roles r
  where r.role::text in ('professor', 'professor_pkz', 'professor_one_to_one',
                         'fisioterapeuta', 'nutricionista', 'psicologo')
),
atuando as (
  select b.professor_id as id, pg_temp.servico_codigo(b.service::text) as servico from origem.bookings b where b.professor_id is not null
  union select t.professor_id, 'treino'       from origem.training_reports t        where t.professor_id is not null
  union select s.evaluator_id, 'treino'       from origem.physical_test_sessions s  where s.evaluator_id is not null
  union select f.physio_id,    'fisioterapia' from origem.physio_assessments f      where f.physio_id is not null
  union select e.physio_id,    'fisioterapia' from origem.physio_evolutions e
  union select e.professional_id, pg_temp.servico_codigo(e.service::text) from origem.specialist_evolutions e
)
select p.id, p.servico, p.created_at, true as tem_papel from por_papel p
union all
select a.id, a.servico, pr.created_at, false
from atuando a
join origem.profiles pr on pr.id = a.id
where a.servico is not null
  and not exists (select 1 from por_papel p where p.id = a.id);

insert into novo.profissional as pf (id, especialidade, ativo, pendencia, criado_em)
select pr.id,
       string_agg(distinct t.servico, ', ' order by t.servico),
       pr.active,
       case when not bool_or(t.tem_papel) then
              case when exists (select 1 from origem.user_roles r where r.user_id = pr.id and r.role::text = 'admin')
                   then 'admin atuando como profissional (sem papel de profissional)'
                   else 'atua como profissional sem papel de profissional' end
       end,
       pr.created_at
from tmp_prof_servico t
join origem.profiles pr on pr.id = t.id
group by pr.id, pr.active, pr.created_at
on conflict (id) do update
  set especialidade = excluded.especialidade, ativo = excluded.ativo,
      pendencia = novo.juntar_pendencia(pf.pendencia, excluded.pendencia),
      criado_em = excluded.criado_em, atualizado_em = now();

insert into novo.profissional_servico (profissional_id, servico_id, criado_em)
select t.id, s.id, min(t.created_at)
from tmp_prof_servico t
join novo.servico s on s.codigo = t.servico
group by t.id, s.id
on conflict (profissional_id, servico_id) do update set atualizado_em = now();

-- -----------------------------------------------------------------------------
-- Registro da execução
-- -----------------------------------------------------------------------------
insert into novo.carga_execucao (script, linhas_carregadas, linhas_rejeitadas, observacao)
select 'cadastro',
       (select count(*) from novo.pessoa) + (select count(*) from novo.perfil_usuario)
     + (select count(*) from novo.papel_usuario) + (select count(*) from novo.aluno)
     + (select count(*) from novo.aluno_servico) + (select count(*) from novo.responsavel_aluno)
     + (select count(*) from novo.profissional) + (select count(*) from novo.profissional_servico),
       (select count(*) from novo.carga_rejeitado where script = 'cadastro'),
       format('pessoa %s, perfil %s, papel_usuario %s, aluno %s, aluno_servico %s, responsavel %s, profissional %s, prof_servico %s',
              (select count(*) from novo.pessoa), (select count(*) from novo.perfil_usuario),
              (select count(*) from novo.papel_usuario), (select count(*) from novo.aluno),
              (select count(*) from novo.aluno_servico), (select count(*) from novo.responsavel_aluno),
              (select count(*) from novo.profissional), (select count(*) from novo.profissional_servico));

commit;
