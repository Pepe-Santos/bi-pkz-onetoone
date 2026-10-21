-- =============================================================================
-- 10_carga_referencia.sql
-- Domínio: referencia              Dono: Micael (Frente 1)
-- Origem:  origem.app_settings + valores dos enums e das funções do app
--          (student_program, service_type, one_to_one_plan, app_role,
--           plan_weekly_treino, plan_monthly_fisio, plan_monthly_nutri).
--          As regras das funções foram lidas com pg_get_functiondef e estão
--          escritas aqui; o script não chama nada de public.
-- Destino: novo.unidade, servico, configuracao_unidade, plano, plano_beneficio, papel
-- Depende de: migrations 001–010
-- Mapeamento: mapeamento/referencia.csv
-- =============================================================================
\set ON_ERROR_STOP on

begin;

select set_config('novo.modo_carga', 'on', true);

-- Rejeitados não são apagados antes: a chave única (010) + on conflict do nothing
-- evitam duplicar na reexecução.

-- -----------------------------------------------------------------------------
-- unidade (2)
-- -----------------------------------------------------------------------------
insert into novo.unidade (codigo, nome)
values ('pkz',        'PKZ Lab / Playmakerz'),
       ('one_to_one', 'Studio One to One')
on conflict (codigo) do update
  set nome = excluded.nome, atualizado_em = now();

-- -----------------------------------------------------------------------------
-- servico (4)
-- -----------------------------------------------------------------------------
insert into novo.servico (codigo, nome, especializado, ordem)
values ('treino',       'Treino',       false, 1),
       ('fisioterapia', 'Fisioterapia', true,  2),
       ('nutricao',     'Nutrição',     true,  3),
       ('psicologia',   'Psicologia',   true,  4)
on conflict (codigo) do update
  set nome = excluded.nome, especializado = excluded.especializado,
      ordem = excluded.ordem, atualizado_em = now();

-- -----------------------------------------------------------------------------
-- configuracao_unidade: a única linha de app_settings, copiada para as 2 unidades
-- -----------------------------------------------------------------------------
insert into novo.configuracao_unidade as c (
  unidade_id, prazo_cancelamento_horas, capacidade_padrao, limite_credito_baixo,
  creditos_mensais, creditos_fisio_padrao, creditos_nutri_padrao,
  renovacao_dia, renovacao_dia_semana, renovacao_ativa, ultima_renovacao_em,
  espera_aceite_horas, liberacao_automatica, liberacao_intervalo_min,
  contato_endereco, contato_instagram, contato_telefone, contato_site, pendencia)
select u.id, s.cancel_deadline_hours, s.default_capacity, s.low_credit_threshold,
       s.monthly_credits, s.credits_fisio_standard, s.credits_nutri_standard,
       s.renewal_day, s.renewal_weekday % 7,          -- ISO (1=seg … 7=dom) → dow (0=dom)
       s.renewal_enabled, s.last_renewal_at,
       s.waitlist_accept_hours, s.auto_release_enabled, s.auto_release_interval_minutes,
       s.contact_address, s.contact_instagram, s.contact_phone, s.contact_website,
       'configuração única da origem copiada para as duas unidades'
from origem.app_settings s
cross join novo.unidade u
on conflict (unidade_id) do update
  set prazo_cancelamento_horas = excluded.prazo_cancelamento_horas,
      capacidade_padrao        = excluded.capacidade_padrao,
      limite_credito_baixo     = excluded.limite_credito_baixo,
      creditos_mensais         = excluded.creditos_mensais,
      creditos_fisio_padrao    = excluded.creditos_fisio_padrao,
      creditos_nutri_padrao    = excluded.creditos_nutri_padrao,
      renovacao_dia            = excluded.renovacao_dia,
      renovacao_dia_semana     = excluded.renovacao_dia_semana,
      renovacao_ativa          = excluded.renovacao_ativa,
      ultima_renovacao_em      = excluded.ultima_renovacao_em,
      espera_aceite_horas      = excluded.espera_aceite_horas,
      liberacao_automatica     = excluded.liberacao_automatica,
      liberacao_intervalo_min  = excluded.liberacao_intervalo_min,
      contato_endereco         = excluded.contato_endereco,
      contato_instagram        = excluded.contato_instagram,
      contato_telefone         = excluded.contato_telefone,
      contato_site             = excluded.contato_site,
      pendencia                = novo.juntar_pendencia(c.pendencia, excluded.pendencia),
      atualizado_em            = now();

-- -----------------------------------------------------------------------------
-- plano (7): os 5 do enum one_to_one_plan + pkz_padrao + one_to_one_sem_plano
-- -----------------------------------------------------------------------------
insert into novo.plano as p (unidade_id, codigo, nome, ativo, pendencia)
select u.id, v.codigo, v.nome, v.ativo, v.pendencia
from (values
  ('one_to_one', 'express',              'Express',              true,  null),
  ('one_to_one', 'one_move',             'One Move',             true,  null),
  ('one_to_one', 'one_power',            'One Power',            true,  null),
  ('one_to_one', 'one_power_legacy',     'One Power (legado)',   false, 'plano legado: confirmar se ainda é vendido'),
  ('one_to_one', 'be_the_one',           'Be The One',           true,  null),
  ('pkz',        'pkz_padrao',           'PKZ padrão',           true,  'plano criado na carga: o PKZ não tem plano na origem'),
  ('one_to_one', 'one_to_one_sem_plano', 'One to One sem plano', false, 'aluno One to One sem plano na origem')
) v(unidade, codigo, nome, ativo, pendencia)
join novo.unidade u on u.codigo = v.unidade
on conflict (codigo) do update
  set unidade_id    = excluded.unidade_id,
      nome          = excluded.nome,
      ativo         = excluded.ativo,
      pendencia     = novo.juntar_pendencia(p.pendencia, excluded.pendencia),
      atualizado_em = now();

-- -----------------------------------------------------------------------------
-- plano_beneficio: regras das funções do app (só quantidades > 0) + PKZ
--   plan_weekly_treino : express 5, one_move 3, one_power 6, one_power_legacy 6, be_the_one 6
--   plan_monthly_fisio : one_power_legacy 3, be_the_one 2
--   plan_monthly_nutri : express 1, one_move 1, one_power 2, one_power_legacy 2, be_the_one 2
--   pkz_padrao (treino/mês): app_settings.monthly_credits
-- -----------------------------------------------------------------------------
insert into novo.plano_beneficio as b (plano_id, servico_id, quantidade, periodicidade, pendencia)
select p.id, s.id, v.quantidade, v.periodicidade, v.pendencia
from (values
  ('express',          'treino',       5, 'semana', null),
  ('one_move',         'treino',       3, 'semana', null),
  ('one_power',        'treino',       6, 'semana', null),
  ('one_power_legacy', 'treino',       6, 'semana', null),
  ('be_the_one',       'treino',       6, 'semana', null),
  ('one_power_legacy', 'fisioterapia', 3, 'mes',    'função mensal, mas o comentário diz sessões por semana: confirmar periodicidade'),
  ('be_the_one',       'fisioterapia', 2, 'mes',    'função mensal, mas o comentário diz sessões por semana: confirmar periodicidade'),
  ('express',          'nutricao',     1, 'mes',    null),
  ('one_move',         'nutricao',     1, 'mes',    null),
  ('one_power',        'nutricao',     2, 'mes',    null),
  ('one_power_legacy', 'nutricao',     2, 'mes',    null),
  ('be_the_one',       'nutricao',     2, 'mes',    null)
) v(plano, servico, quantidade, periodicidade, pendencia)
join novo.plano p   on p.codigo = v.plano
join novo.servico s on s.codigo = v.servico
union all
select p.id, s.id, a.monthly_credits, 'mes', 'quantidade do PKZ (monthly_credits) a confirmar'
from origem.app_settings a
join novo.plano p   on p.codigo = 'pkz_padrao'
join novo.servico s on s.codigo = 'treino'
on conflict (plano_id, servico_id, periodicidade) do update
  set quantidade    = excluded.quantidade,
      pendencia     = novo.juntar_pendencia(b.pendencia, excluded.pendencia),
      atualizado_em = now();

-- -----------------------------------------------------------------------------
-- papel (5): app_role (9 valores) → catálogo menor
-- -----------------------------------------------------------------------------
insert into novo.papel (codigo, nome)
values ('admin',        'Administrador'),
       ('professor',    'Professor'),
       ('especialista', 'Especialista'),
       ('responsavel',  'Responsável'),
       ('recepcao',     'Recepção')
on conflict (codigo) do update
  set nome = excluded.nome, atualizado_em = now();

-- -----------------------------------------------------------------------------
-- Registro da execução
-- -----------------------------------------------------------------------------
insert into novo.carga_execucao (script, linhas_carregadas, linhas_rejeitadas, observacao)
select 'referencia',
       (select count(*) from novo.unidade) + (select count(*) from novo.servico)
     + (select count(*) from novo.configuracao_unidade) + (select count(*) from novo.plano)
     + (select count(*) from novo.plano_beneficio) + (select count(*) from novo.papel),
       (select count(*) from novo.carga_rejeitado where script = 'referencia'),
       format('unidade %s, servico %s, configuracao %s, plano %s, beneficio %s, papel %s',
              (select count(*) from novo.unidade), (select count(*) from novo.servico),
              (select count(*) from novo.configuracao_unidade), (select count(*) from novo.plano),
              (select count(*) from novo.plano_beneficio), (select count(*) from novo.papel));

commit;
