-- =============================================================================
-- 70_carga_atendimento.sql
-- Domínio: atendimento             Dono: Micael (Frente 1)
-- Origem:  origem.physio_assessments (avaliação de fisioterapia + anamnese),
--          origem.physio_evolutions, origem.specialist_evolutions (atendimentos),
--          origem.bookings (data do atendimento)
-- Destino: novo.avaliacao e novo.avaliacao_medida (tipo 'fisioterapia'),
--          novo.anamnese, novo.atendimento, novo.evolucao;
--          marca pendência em novo.agendamento (especialista presente sem atendimento)
-- Depende de: migrations 001–011; scripts 10–60 (as métricas de fisio vêm do 60)
-- Mapeamento: mapeamento/atendimento.csv
--
-- DADO CLÍNICO (de criança, no PKZ). Nada daqui vai para conferência com texto:
-- só contagens. CPF, e-mail, endereço, telefone, profissão e sexo NÃO migram
-- (pendência 4). Os caminhos de arquivo (file_path, img_*, carimbo, laudo,
-- storage_path das evoluções) entram no script 80.
-- =============================================================================
\set ON_ERROR_STOP on

begin;

select set_config('novo.modo_carga', 'on', true);

-- Chaves de pkz_data que são texto clínico (vão para anamnese.dados_complementares)
create or replace function pg_temp.chave_clinica(k text) returns boolean language sql immutable as $$
  select k ~ '^(rotina_|hpp_d_)'
      or k in ('qualidade_sono', 'entorses_lado', 'cirurgias_sim', 'cirurgias_quais',
               'fraturas_sim', 'fraturas_quais', 'laudo_apresentado', 'hpp_outros_desc');
$$;

-- Chaves de pkz_data que são caminho de arquivo (script 80)
create or replace function pg_temp.chave_arquivo(k text) returns boolean language sql immutable as $$
  select k ~ '^img_' or k in ('carimbo_path', 'laudo_path');
$$;

-- -----------------------------------------------------------------------------
-- b) Rejeitados: avaliação de fisioterapia
-- -----------------------------------------------------------------------------
insert into novo.carga_rejeitado (script, tabela_origem, id_origem, motivo)
select 'atendimento', 'physio_assessments', p.id,
       case when not exists (select 1 from novo.aluno a where a.id = p.athlete_id) then 'aluno inexistente no destino'
            else 'aluno sem matrícula no destino (sem unidade)' end
from origem.physio_assessments p
where not exists (select 1 from novo.aluno a where a.id = p.athlete_id)
   or novo.unidade_atual_do_aluno(p.athlete_id) is null
on conflict (script, tabela_origem, id_origem, motivo) do nothing;

-- -----------------------------------------------------------------------------
-- c1) avaliacao (tipo fisioterapia)
-- -----------------------------------------------------------------------------
insert into novo.avaliacao as av (id, aluno_id, unidade_id, tipo, data, avaliador_id, avaliador_nome, status,
                                  consolidada_em, observacoes, criado_por, pendencia, criado_em)
select p.id, p.athlete_id, un.id, 'fisioterapia', p.assessment_date,
       pr.id,
       case when pr.id is null then nullif(btrim(p.physio_name), '') end,
       case when p.status = 'final' then 'consolidada' else 'rascunho' end,
       case when p.status = 'final' then p.updated_at end,
       null,
       case when exists (select 1 from novo.perfil_usuario u where u.usuario_id = p.created_by) then p.created_by end,
       novo.juntar_pendencia(novo.juntar_pendencia(
         case when p.program is not null and p.program::text <> un.codigo
              then 'programa da avaliação diferente da unidade do aluno' end,
         case when p.physio_id is not null and pr.id is null then 'avaliador não encontrado no destino' end),
         case when p.status not in ('final', 'rascunho') then 'status de origem desconhecido (tratado como rascunho)' end),
       p.created_at
from origem.physio_assessments p
join novo.aluno a on a.id = p.athlete_id
join novo.unidade un on un.id = novo.unidade_atual_do_aluno(p.athlete_id)
left join novo.profissional pr on pr.id = p.physio_id
on conflict (id) do update
  set aluno_id = excluded.aluno_id, unidade_id = excluded.unidade_id, tipo = excluded.tipo, data = excluded.data,
      avaliador_id = excluded.avaliador_id, avaliador_nome = excluded.avaliador_nome, status = excluded.status,
      consolidada_em = excluded.consolidada_em, observacoes = excluded.observacoes, criado_por = excluded.criado_por,
      pendencia = novo.juntar_pendencia(av.pendencia, excluded.pendencia),
      criado_em = excluded.criado_em, atualizado_em = now();

-- -----------------------------------------------------------------------------
-- Valores brutos das medidas de fisioterapia: (avaliação, código, lado, texto, tipo)
-- -----------------------------------------------------------------------------
create temporary table tmp_fisio on commit drop as
-- goniometria (colunas numéricas)
select p.id as avaliacao_id, p.created_at, 'fisio_' || g.medida as codigo, g.lado,
       g.valor::text as bruto, 'goniometria'::text as fonte, null::text as chave
from origem.physio_assessments p
join novo.avaliacao av on av.id = p.id
cross join lateral (values
  ('cotovelo_ext',  'dir', p.cotovelo_ext_dir),  ('cotovelo_ext',  'esq', p.cotovelo_ext_esq),
  ('cotovelo_flex', 'dir', p.cotovelo_flex_dir), ('cotovelo_flex', 'esq', p.cotovelo_flex_esq),
  ('joelho_ext',    'dir', p.joelho_ext_dir),    ('joelho_ext',    'esq', p.joelho_ext_esq),
  ('joelho_flex',   'dir', p.joelho_flex_dir),   ('joelho_flex',   'esq', p.joelho_flex_esq),
  ('ombro_abd',     'dir', p.ombro_abd_dir),     ('ombro_abd',     'esq', p.ombro_abd_esq),
  ('ombro_rot_ext', 'dir', p.ombro_rot_ext_dir), ('ombro_rot_ext', 'esq', p.ombro_rot_ext_esq),
  ('quadril',       'dir', p.quadril_dir),       ('quadril',       'esq', p.quadril_esq)) g(medida, lado, valor)
where g.valor is not null
union all
-- Appley (texto: Positivo / Negativo; 'Não avaliado' não gera linha)
select p.id, p.created_at, 'fisio_appley_' || ap.parte, ap.lado, btrim(ap.valor), 'appley', null
from origem.physio_assessments p
join novo.avaliacao av on av.id = p.id
cross join lateral (values
  ('sup', 'dir', p.appley_dir_sup), ('inf', 'dir', p.appley_dir_inf),
  ('sup', 'esq', p.appley_esq_sup), ('inf', 'esq', p.appley_esq_inf)) ap(parte, lado, valor)
where nullif(btrim(ap.valor), '') is not null and btrim(ap.valor) !~* '^n[ãa]o avaliado$'
union all
-- pkz_data: força, relação, mobilidade e postura
select p.id, p.created_at,
       case
         when e.k = 'forca_abdominal'                 then 'fisio_pkz_forca_abdominal'
         when e.k ~ '^(forca|ratio|mob)_.+_(dir|esq)$' then 'fisio_pkz_' || regexp_replace(e.k, '_(dir|esq)$', '')
         when e.k ~ '^post_'                          then pc.codigo
       end,
       case
         when e.k ~ '^(forca|ratio|mob)_.+_(dir|esq)$' then substring(e.k from '_(dir|esq)$')
         when e.k ~ '^post_'                          then pc.lado
       end,
       btrim(e.v),
       case when e.k ~ '^forca_abdominal$' then 'forca_abdominal'
            when e.k ~ '^forca_' then 'forca'
            when e.k ~ '^mob_'   then 'mob'
            when e.k ~ '^ratio_' then 'ratio'
            when e.k ~ '^post_.+_dir$' then 'post_direcao'
            else 'post_valor' end,
       e.k
from origem.physio_assessments p
join novo.avaliacao av on av.id = p.id
cross join lateral jsonb_each_text(case when jsonb_typeof(p.pkz_data) = 'object' then p.pkz_data else '{}' end) e(k, v)
-- postura: post_<vista>_<campo>[_dir|_esq]_<valor|dir>. O ÚLTIMO _dir é "direção do desvio".
-- O lado só existe quando a métrica sem o sufixo de lado usa lado (eias_patela, angulo_q, tibia ...).
left join lateral (
  select coalesce(ml.codigo, mn.codigo) as codigo, case when ml.codigo is not null then x.lado end as lado
  from (select m[1] as vista, m[2] as resto, m[3] as sufixo,
               substring(m[2] from '_(dir|esq)$') as lado,
               regexp_replace(m[2], '_(dir|esq)$', '') as campo_sem_lado
        from regexp_match(e.k, '^post_(anterior|lateral_dir|lateral_esq|posterior)_(.+)_(valor|dir)$') m) x
  left join novo.metrica ml
         on x.lado is not null and ml.usa_lado
        and ml.codigo = 'fisio_pkz_post_' || x.vista || '_' || x.campo_sem_lado
                        || case x.sufixo when 'dir' then '_direcao' else '' end
  left join novo.metrica mn
         on mn.codigo = 'fisio_pkz_post_' || x.vista || '_' || x.resto
                        || case x.sufixo when 'dir' then '_direcao' else '' end
) pc on e.k ~ '^post_'
where nullif(btrim(e.v), '') is not null
  and not pg_temp.chave_clinica(e.k)
  and not pg_temp.chave_arquivo(e.k);

-- Chave de pkz_data sem destino (nem medida, nem anamnese, nem arquivo): rejeitada com o nome da chave.
insert into novo.carga_rejeitado (script, tabela_origem, id_origem, motivo)
select distinct 'atendimento', 'physio_assessments', f.avaliacao_id,
       'chave de pkz_data sem métrica: ' || f.chave
from tmp_fisio f
where f.chave is not null
  and (f.codigo is null or not exists (select 1 from novo.metrica m where m.codigo = f.codigo))
on conflict (script, tabela_origem, id_origem, motivo) do nothing;

-- -----------------------------------------------------------------------------
-- c2) avaliacao_medida (fisioterapia)
-- -----------------------------------------------------------------------------
insert into novo.avaliacao_medida as am (avaliacao_id, metrica_id, lado, tentativa, valor_num, valor_texto,
                                         pendencia, criado_em)
select c.avaliacao_id, c.metrica_id, c.lado, 1, c.num,
       case when c.num is null then c.bruto end,
       novo.juntar_pendencia(novo.juntar_pendencia(
         case c.fonte when 'goniometria' then 'unidade a confirmar (graus)'
                      when 'forca'       then 'kg a confirmar'
                      when 'forca_abdominal' then 'unidade a confirmar' end,
         case when c.fonte = 'mob' and c.bruto ~ '[º°]' then 'símbolo de grau removido' end),
         case when c.tipo_dado <> 'texto' and c.num is null then 'formato antigo / não numérico' end),
       c.created_at
from (
  select f.*, m.id as metrica_id, m.tipo_dado,
         case when m.tipo_dado = 'texto' then null
              else novo.texto_para_numero(btrim(translate(f.bruto, 'º°', ''))) end as num
  from tmp_fisio f
  join novo.metrica m on m.codigo = f.codigo
) c
on conflict (avaliacao_id, metrica_id, lado, tentativa) do update
  set valor_num = excluded.valor_num, valor_texto = excluded.valor_texto,
      pendencia = novo.juntar_pendencia(am.pendencia, excluded.pendencia),
      criado_em = excluded.criado_em, atualizado_em = now();

-- -----------------------------------------------------------------------------
-- c3) anamnese (uma por avaliação de fisio; confidencialidade 'restrito')
-- -----------------------------------------------------------------------------
insert into novo.anamnese as an (id, aluno_id, avaliacao_id, profissional_id, data,
  queixa_principal, hda, hpp_doencas, hpp_cirurgias, hpp_fraturas, hpp_entorses,
  hab_freq_treinos, hab_outras_atividades, hab_alcool, hab_tabagista, hab_medicamentos,
  fam_materna, fam_paterna, diagnostico_clinico, diagnostico_funcional, exames_complementares,
  observacao, dados_complementares, confidencialidade, criado_em)
select p.id, p.athlete_id, p.id,
       case when exists (select 1 from novo.profissional pr where pr.id = p.physio_id) then p.physio_id end,
       p.assessment_date,
       nullif(btrim(p.queixa_principal), ''), nullif(btrim(p.hda), ''),
       nullif(btrim(p.hpp_doencas), ''), nullif(btrim(p.hpp_cirurgias), ''),
       nullif(btrim(p.hpp_fraturas), ''), nullif(btrim(p.hpp_entorses), ''),
       nullif(btrim(p.hab_freq_treinos), ''), nullif(btrim(p.hab_outras_atividades), ''),
       nullif(btrim(p.hab_alcool), ''), nullif(btrim(p.hab_tabagista), ''),
       nullif(btrim(p.hab_medicamentos), ''),
       nullif(btrim(p.fam_materna), ''), nullif(btrim(p.fam_paterna), ''),
       nullif(btrim(p.diagnostico_clinico), ''), nullif(btrim(p.diagnostico_funcional), ''),
       nullif(btrim(p.exames_complementares), ''), nullif(btrim(p.observacao), ''),
       (select jsonb_object_agg(e.k, btrim(e.v))
          from jsonb_each_text(case when jsonb_typeof(p.pkz_data) = 'object' then p.pkz_data else '{}' end) e(k, v)
         where pg_temp.chave_clinica(e.k) and nullif(btrim(e.v), '') is not null),
       'restrito', p.created_at
from origem.physio_assessments p
join novo.avaliacao av on av.id = p.id
on conflict (id) do update
  set aluno_id = excluded.aluno_id, avaliacao_id = excluded.avaliacao_id,
      profissional_id = excluded.profissional_id, data = excluded.data,
      queixa_principal = excluded.queixa_principal, hda = excluded.hda,
      hpp_doencas = excluded.hpp_doencas, hpp_cirurgias = excluded.hpp_cirurgias,
      hpp_fraturas = excluded.hpp_fraturas, hpp_entorses = excluded.hpp_entorses,
      hab_freq_treinos = excluded.hab_freq_treinos, hab_outras_atividades = excluded.hab_outras_atividades,
      hab_alcool = excluded.hab_alcool, hab_tabagista = excluded.hab_tabagista,
      hab_medicamentos = excluded.hab_medicamentos, fam_materna = excluded.fam_materna,
      fam_paterna = excluded.fam_paterna, diagnostico_clinico = excluded.diagnostico_clinico,
      diagnostico_funcional = excluded.diagnostico_funcional,
      exames_complementares = excluded.exames_complementares, observacao = excluded.observacao,
      dados_complementares = excluded.dados_complementares, criado_em = excluded.criado_em,
      atualizado_em = now();

-- -----------------------------------------------------------------------------
-- Atendimentos da origem (as duas tabelas de evolução, já com serviço e data)
-- -----------------------------------------------------------------------------
create temporary table tmp_atend on commit drop as
select e.id, 'physio_evolutions'::text as tabela, e.athlete_id, e.physio_id as profissional_id,
       'fisioterapia'::text as servico, null::uuid as booking_id, null::uuid as agendamento_id,
       (e.created_at at time zone 'America/Sao_Paulo')::date as data,
       'data do atendimento = data do envio do arquivo'::text as pendencia, e.created_at
from origem.physio_evolutions e
union all
select e.id, 'specialist_evolutions', e.athlete_id, e.professional_id,
       case e.service::text when 'treino' then 'treino' when 'fisioterapeuta' then 'fisioterapia'
                            when 'nutricionista' then 'nutricao' when 'psicologo' then 'psicologia' end,
       e.booking_id,
       case when ag.aluno_id = e.athlete_id then ag.id end,
       coalesce(b.slot_date, (e.created_at at time zone 'America/Sao_Paulo')::date),
       novo.juntar_pendencia(
         case when ag.id is not null and ag.aluno_id <> e.athlete_id then 'agendamento de outro aluno: vínculo removido'
              when e.booking_id is not null and ag.id is null then 'agendamento não encontrado no destino: vínculo removido' end,
         case when b.id is null then 'data do atendimento = data do envio do arquivo' end),
       e.created_at
from origem.specialist_evolutions e
left join origem.bookings b on b.id = e.booking_id
left join novo.agendamento ag on ag.id = e.booking_id;

-- b) Rejeitados: atendimento
insert into novo.carga_rejeitado (script, tabela_origem, id_origem, motivo)
select 'atendimento', t.tabela, t.id, r.motivo
from tmp_atend t
cross join lateral (values
  (case when not exists (select 1 from novo.aluno a where a.id = t.athlete_id) then 'aluno inexistente no destino' end),
  (case when not exists (select 1 from novo.profissional p where p.id = t.profissional_id) then 'profissional inexistente no destino' end),
  (case when t.servico = 'treino' then 'serviço treino: atendimento exige serviço especializado' end),
  (case when t.servico is null then 'serviço desconhecido' end)) r(motivo)
where r.motivo is not null
on conflict (script, tabela_origem, id_origem, motivo) do nothing;

-- -----------------------------------------------------------------------------
-- c4) atendimento
-- -----------------------------------------------------------------------------
insert into novo.atendimento as at (id, aluno_id, profissional_id, servico_id, agendamento_id, unidade_id,
                                    data, observacao, pendencia, criado_em)
select t.id, t.athlete_id, t.profissional_id, s.id, t.agendamento_id,
       novo.unidade_atual_do_aluno(t.athlete_id), t.data, null, t.pendencia, t.created_at
from tmp_atend t
join novo.aluno a on a.id = t.athlete_id
join novo.profissional p on p.id = t.profissional_id
join novo.servico s on s.codigo = t.servico and s.especializado
on conflict (id) do update
  set aluno_id = excluded.aluno_id, profissional_id = excluded.profissional_id, servico_id = excluded.servico_id,
      agendamento_id = excluded.agendamento_id, unidade_id = excluded.unidade_id, data = excluded.data,
      pendencia = novo.juntar_pendencia(at.pendencia, excluded.pendencia),
      criado_em = excluded.criado_em, atualizado_em = now();

-- -----------------------------------------------------------------------------
-- c5) evolucao: uma por atendimento (a observação fica nula: o conteúdo está no
--     arquivo, e o nome do arquivo pode ter o nome do aluno)
-- -----------------------------------------------------------------------------
insert into novo.evolucao as ev (atendimento_id, data, observacao, criado_em)
select at.id, at.data, null, at.criado_em
from novo.atendimento at
join tmp_atend t on t.id = at.id
on conflict (atendimento_id, data) do update
  set criado_em = excluded.criado_em, atualizado_em = now();

-- -----------------------------------------------------------------------------
-- d) agendamento de especialista com presença e sem atendimento
--    Tira a marca de execuções anteriores e marca de novo (só update).
-- -----------------------------------------------------------------------------
update novo.agendamento ag
set pendencia = nullif(array_to_string(array(
      select x from unnest(string_to_array(ag.pendencia, '; ')) x
      where x <> 'realizado sem registro de atendimento'), '; '), '')
where ag.pendencia like '%realizado sem registro de atendimento%';

update novo.agendamento ag
set pendencia = novo.juntar_pendencia(ag.pendencia, 'realizado sem registro de atendimento')
from novo.servico s
where s.id = ag.servico_id and s.especializado
  and ag.status = 'presente'
  and not exists (select 1 from novo.atendimento at where at.agendamento_id = ag.id);

-- -----------------------------------------------------------------------------
-- Registro da execução
-- -----------------------------------------------------------------------------
insert into novo.carga_execucao (script, linhas_carregadas, linhas_rejeitadas, observacao)
select 'atendimento',
       (select count(*) from novo.avaliacao where tipo = 'fisioterapia')
     + (select count(*) from novo.avaliacao_medida am join novo.avaliacao a on a.id = am.avaliacao_id
         where a.tipo = 'fisioterapia')
     + (select count(*) from novo.anamnese) + (select count(*) from novo.atendimento)
     + (select count(*) from novo.evolucao),
       (select count(*) from novo.carga_rejeitado where script = 'atendimento'),
       format('avaliacao fisioterapia %s, medidas %s, anamnese %s, atendimento %s, evolucao %s, '
              || 'agendamento especialista presente sem atendimento %s',
              (select count(*) from novo.avaliacao where tipo = 'fisioterapia'),
              (select count(*) from novo.avaliacao_medida am join novo.avaliacao a on a.id = am.avaliacao_id
                where a.tipo = 'fisioterapia'),
              (select count(*) from novo.anamnese), (select count(*) from novo.atendimento),
              (select count(*) from novo.evolucao),
              (select count(*) from novo.agendamento where pendencia like '%realizado sem registro de atendimento%'));

commit;
