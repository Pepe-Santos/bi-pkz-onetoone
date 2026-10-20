-- =============================================================================
-- 50_carga_relatorio.sql
-- Domínio: relatorio               Dono: Micael (Frente 1)
-- Origem:  origem.training_report_materials, origem.training_report_technologies,
--          origem.training_reports
-- Destino: novo.catalogo_item, novo.relatorio_treino, novo.relatorio_item
-- Depende de: migrations 001–010; scripts 10–40
-- Mapeamento: mapeamento/relatorio.csv
-- Os PDFs dos relatórios (file_path, pdf_storage_path) entram no script 80.
-- =============================================================================
\set ON_ERROR_STOP on

begin;

select set_config('novo.modo_carga', 'on', true);

-- código de catálogo: minúsculas, sem acento, só letras/números e '_'
create or replace function pg_temp.slug(t text) returns text language sql immutable as $$
  select btrim(regexp_replace(lower(translate(btrim(t),
           'ÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇáàâãäéèêëíìîïóòôõöúùûüç',
           'AAAAAEEEEIIIIOOOOOUUUUCaaaaaeeeeiiiiooooouuuuc')), '[^a-z0-9]+', '_', 'g'), '_');
$$;

-- Valores usados nos relatórios, um por (relatório, domínio, texto)
create temporary table tmp_valor on commit drop as
select t.id as relatorio_id, t.created_at, v.dominio, btrim(v.valor) as valor, v.livre
from origem.training_reports t
cross join lateral (
  select 'material', x, false from unnest(t.materials) x
  union all select 'tecnologia', x, false from unnest(t.technologies) x
  union all select 'capacidade_fisica', x, false from unnest(t.capacidades_fisicas) x
  union all select 'capacidade_tecnica', x, false from unnest(t.capacidades_tecnicas) x
  union all select 'capacidade_cognitiva', x, false from unnest(t.capacidades_cognitivas) x
  union all select 'objetivo_sessao', x, false from unnest(t.objetivo_sessao) x
  union all select 'foco', x, false from unnest(t.foco) x
  union all select 'conduta', x, false from unnest(t.conduta) x
  union all select 'material', t.materials_other, true where nullif(btrim(t.materials_other), '') is not null
  union all select 'tecnologia', t.technologies_other, true where nullif(btrim(t.technologies_other), '') is not null
) v(dominio, valor, livre)
where nullif(btrim(v.valor), '') is not null;

-- -----------------------------------------------------------------------------
-- c1) catalogo_item
--   material e tecnologia: das tabelas de catálogo da origem;
--   os outros 6 domínios: valores distintos dos arrays;
--   texto livre (*_other) ou valor fora do catálogo: item próprio, com pendência.
--   Uma linha por (dominio, codigo), senão o on conflict falha.
-- -----------------------------------------------------------------------------
insert into novo.catalogo_item as ci (dominio, codigo, nome, ativo, ordem, id_origem, pendencia, criado_em)
select distinct on (dominio, codigo) dominio, codigo, nome, ativo, ordem, id_origem, pendencia, criado_em
from (
  select 1 as prioridade, 'material' as dominio, pg_temp.slug(m.name) as codigo, btrim(m.name) as nome,
         m.active as ativo, m.sort_order as ordem, m.id as id_origem, null::text as pendencia, m.created_at as criado_em
  from origem.training_report_materials m
  union all
  select 1, 'tecnologia', pg_temp.slug(t.name), btrim(t.name), t.active, t.sort_order, t.id, null, t.created_at
  from origem.training_report_technologies t
  union all
  select 2, v.dominio, pg_temp.slug(v.valor), v.valor, true,
         (dense_rank() over (partition by v.dominio order by v.valor))::int, null, null, now()
  from (select distinct dominio, valor from tmp_valor
         where not livre and dominio not in ('material', 'tecnologia')) v
  union all
  select 3, v.dominio, pg_temp.slug(v.valor), v.valor, true, 900, null,
         'não classificado (valor fora do catálogo)', now()
  from (select distinct dominio, valor from tmp_valor where not livre and dominio in ('material', 'tecnologia')) v
  where not exists (select 1 from origem.training_report_materials m where v.dominio = 'material' and btrim(m.name) = v.valor)
    and not exists (select 1 from origem.training_report_technologies t where v.dominio = 'tecnologia' and btrim(t.name) = v.valor)
  union all
  select 4, v.dominio, 'outro_' || pg_temp.slug(v.valor), v.valor, true, 999, null,
         'não classificado (texto livre de *_other)', now()
  from (select distinct dominio, valor from tmp_valor where livre) v
) x
order by dominio, codigo, prioridade
on conflict (dominio, codigo) do update
  set nome = excluded.nome, ativo = excluded.ativo, ordem = excluded.ordem, id_origem = excluded.id_origem,
      pendencia = novo.juntar_pendencia(ci.pendencia, excluded.pendencia),
      criado_em = excluded.criado_em, atualizado_em = now();

-- -----------------------------------------------------------------------------
-- c2) relatorio_treino
-- -----------------------------------------------------------------------------
insert into novo.carga_rejeitado (script, tabela_origem, id_origem, motivo)
select 'relatorio', 'training_reports', t.id,
       case when not exists (select 1 from novo.aluno a where a.id = t.athlete_id) then 'aluno inexistente no destino'
            else 'aluno sem matrícula no destino (sem unidade)' end
from origem.training_reports t
where not exists (select 1 from novo.aluno a where a.id = t.athlete_id)
   or novo.unidade_atual_do_aluno(t.athlete_id) is null
on conflict (script, tabela_origem, id_origem, motivo) do nothing;

insert into novo.relatorio_treino as r (
  id, aluno_id, agendamento_id, profissional_id, unidade_id, tipo, status, data, hora_inicio, hora_fim,
  titulo, categoria, grupo, local, tipo_treino, numero_sessao, intensidade, blocos, objetivos,
  analise_html, observacoes, evolucao, desempenho, notas, dor, dor_local, dor_intensidade,
  dor_movimento, criado_por, pendencia, criado_em)
select t.id, t.athlete_id,
       case when ag.aluno_id = t.athlete_id then ag.id end,
       case when exists (select 1 from novo.profissional p where p.id = t.professor_id) then t.professor_id end,
       un.id, t.report_kind, t.status, t.report_date, t.start_time,
       case when t.end_time is null or t.start_time is null or t.end_time > t.start_time then t.end_time end,
       t.title, t.category, t.athlete_group, t.local, t.training_type, t.session_number, t.intensidade,
       t.blocos, t.objetivos, t.analise_html, t.observacoes, t.evolucao, t.desempenho, t.notes,
       t.dor, t.dor_local, t.dor_intensidade, t.dor_movimento,
       case when exists (select 1 from novo.perfil_usuario u where u.usuario_id = t.created_by) then t.created_by end,
       novo.juntar_pendencia(novo.juntar_pendencia(novo.juntar_pendencia(novo.juntar_pendencia(
         case when t.booking_id is not null and ag.id is null then 'agendamento não encontrado no destino: vínculo removido'
              when ag.id is not null and ag.aluno_id <> t.athlete_id then 'agendamento de outro aluno: vínculo removido' end,
         case when t.booking_id is not null
               and (select count(*) from origem.training_reports t2 where t2.booking_id = t.booking_id) > 1
              then 'relatório duplicado para o mesmo agendamento' end),
         case when t.report_kind <> un.codigo then 'tipo do relatório diferente da unidade do aluno' end),
         case when t.end_time is not null and t.start_time is not null and t.end_time <= t.start_time
              then 'horário de fim inválido' end),
         null),
       t.created_at
from origem.training_reports t
join novo.aluno a on a.id = t.athlete_id
join novo.unidade un on un.id = novo.unidade_atual_do_aluno(t.athlete_id)
left join novo.agendamento ag on ag.id = t.booking_id
on conflict (id) do update
  set aluno_id = excluded.aluno_id, agendamento_id = excluded.agendamento_id,
      profissional_id = excluded.profissional_id, unidade_id = excluded.unidade_id, tipo = excluded.tipo,
      status = excluded.status, data = excluded.data, hora_inicio = excluded.hora_inicio,
      hora_fim = excluded.hora_fim, titulo = excluded.titulo, categoria = excluded.categoria,
      grupo = excluded.grupo, local = excluded.local, tipo_treino = excluded.tipo_treino,
      numero_sessao = excluded.numero_sessao, intensidade = excluded.intensidade, blocos = excluded.blocos,
      objetivos = excluded.objetivos, analise_html = excluded.analise_html,
      observacoes = excluded.observacoes, evolucao = excluded.evolucao, desempenho = excluded.desempenho,
      notas = excluded.notas, dor = excluded.dor, dor_local = excluded.dor_local,
      dor_intensidade = excluded.dor_intensidade, dor_movimento = excluded.dor_movimento,
      criado_por = excluded.criado_por,
      pendencia = novo.juntar_pendencia(r.pendencia, excluded.pendencia),
      criado_em = excluded.criado_em, atualizado_em = now();

-- -----------------------------------------------------------------------------
-- c3) relatorio_item ("classificado por")
-- -----------------------------------------------------------------------------
insert into novo.relatorio_item as ri (relatorio_id, catalogo_item_id, texto_original, criado_em)
select distinct on (v.relatorio_id, ci.id) v.relatorio_id, ci.id, v.valor, v.created_at
from tmp_valor v
join novo.relatorio_treino r on r.id = v.relatorio_id
join novo.catalogo_item ci
  on ci.dominio = v.dominio
 and ci.codigo = case when v.livre then 'outro_' || pg_temp.slug(v.valor) else pg_temp.slug(v.valor) end
order by v.relatorio_id, ci.id, v.valor
on conflict (relatorio_id, catalogo_item_id) do update
  set texto_original = excluded.texto_original, criado_em = excluded.criado_em, atualizado_em = now();

-- -----------------------------------------------------------------------------
-- Registro da execução
-- -----------------------------------------------------------------------------
insert into novo.carga_execucao (script, linhas_carregadas, linhas_rejeitadas, observacao)
select 'relatorio',
       (select count(*) from novo.catalogo_item) + (select count(*) from novo.relatorio_treino)
     + (select count(*) from novo.relatorio_item),
       (select count(*) from novo.carga_rejeitado where script = 'relatorio'),
       format('catalogo_item %s (não classificados %s), relatorio_treino %s (duplicados %s), relatorio_item %s',
              (select count(*) from novo.catalogo_item),
              (select count(*) from novo.catalogo_item where pendencia is not null),
              (select count(*) from novo.relatorio_treino),
              (select count(*) from novo.relatorio_treino where pendencia like '%duplicado%'),
              (select count(*) from novo.relatorio_item));

commit;
