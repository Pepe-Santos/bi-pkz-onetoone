-- =============================================================================
-- 012_politicas_rls.sql
-- Políticas de acesso por papel no schema novo
-- Dono: Iago (Frente 3, tarefas 3.1 e 3.3). Pré-requisito: 011_saldo_nao_cumulativo.sql.
--
-- Cria: grants mínimos no schema, 9 funções de escopo e uma política de select
--       por tabela, seguindo a matriz em ../../seguranca/matriz-papeis.md.
--
-- Por que agora: as 44 tabelas estão com RLS ligado e nenhuma política, e
-- ninguém tem USAGE no schema — nem authenticated, nem service_role. Hoje o
-- banco está carregado e inalcançável, inclusive para o back-end, que ficou de
-- ler o novo direto (combinado de 20/10, PR #4).
--
-- Escolhas:
--   * Só política de SELECT. Quem grava no novo é a carga, que roda com papel
--     privilegiado e passa por cima do RLS. Sem política de escrita,
--     authenticated não grava nada: é proposital.
--   * Funções de escopo são SECURITY DEFINER porque leem papel_usuario e
--     matricula; sem isso a política da própria tabela entraria em recursão.
--     Todas com search_path vazio e nomes qualificados (CONVENCOES §6).
--   * Dado clínico fecha por padrão (CONVENCOES §7): avaliacao com
--     tipo = 'fisioterapia', atendimento por servico_id, anamnese, e arquivo
--     onde confidencialidade <> 'normal'.
--   * Pendência 5 (quem vê dado clínico) e pendência 11 (dado pessoal na
--     auditoria) entram na versão mais fechada, marcadas abaixo.
-- =============================================================================

\set ON_ERROR_STOP on

begin;

-- -----------------------------------------------------------------------------
-- 1. Acesso ao schema
-- -----------------------------------------------------------------------------
grant usage on schema novo to authenticated, service_role;
revoke all on schema novo from anon;

-- service_role (back-end) passa por cima do RLS por desenho; precisa do grant
-- para enxergar as tabelas.
grant select on all tables in schema novo to service_role;

-- authenticated enxerga pelo filtro das políticas; o grant é só o primeiro portão.
grant select on all tables in schema novo to authenticated;

-- Auditoria e controle de carga não são legíveis pela API (pendência 11).
revoke select on novo.carga_execucao, novo.carga_rejeitado, novo.carga_gabarito,
                novo.evento_auditoria, novo.acesso_dado_sensivel
  from authenticated;

-- -----------------------------------------------------------------------------
-- 2. Funções de identidade e escopo
-- -----------------------------------------------------------------------------
create or replace function novo.tem_papel(p_codigo text)
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from novo.papel_usuario pu
    join novo.papel p on p.id = pu.papel_id
    where pu.usuario_id = auth.uid() and p.codigo = p_codigo and p.ativo
  );
$$;

create or replace function novo.e_staff()
returns boolean language sql stable security definer set search_path = '' as $$
  select novo.tem_papel('admin') or novo.tem_papel('recepcao');
$$;

create or replace function novo.pessoa_atual()
returns uuid language sql stable security definer set search_path = '' as $$
  select pu.pessoa_id from novo.perfil_usuario pu where pu.usuario_id = auth.uid();
$$;

-- unidade nula no vínculo vale para todas as unidades (pendência 15)
create or replace function novo.tem_unidade(p_unidade uuid)
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from novo.papel_usuario pu
    where pu.usuario_id = auth.uid()
      and (pu.unidade_id is null or pu.unidade_id = p_unidade)
  );
$$;

create or replace function novo.aluno_sob_responsavel(p_aluno uuid)
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from novo.responsavel_aluno ra
    where ra.aluno_id = p_aluno and ra.pessoa_id = novo.pessoa_atual()
  );
$$;

create or replace function novo.aluno_na_minha_unidade(p_aluno uuid)
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from novo.matricula m
    where m.aluno_id = p_aluno and novo.tem_unidade(m.unidade_id)
  );
$$;

-- aluno que eu atendo: agendamento, atendimento, avaliação ou relatório meu
create or replace function novo.aluno_que_atendo(p_aluno uuid)
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (select 1 from novo.agendamento a
                  where a.aluno_id = p_aluno and a.profissional_id = auth.uid())
      or exists (select 1 from novo.atendimento t
                  where t.aluno_id = p_aluno and t.profissional_id = auth.uid())
      or exists (select 1 from novo.avaliacao v
                  where v.aluno_id = p_aluno and v.avaliador_id = auth.uid())
      or exists (select 1 from novo.relatorio_treino r
                  where r.aluno_id = p_aluno and r.profissional_id = auth.uid());
$$;

-- PENDÊNCIA 5: quem vê dado clínico é decisão da direção, com respaldo
-- jurídico. Até lá: admin, e o especialista que atende aquele aluno.
create or replace function novo.pode_ver_clinico(p_aluno uuid)
returns boolean language sql stable security definer set search_path = '' as $$
  select novo.tem_papel('admin')
      or (novo.tem_papel('especialista') and novo.aluno_que_atendo(p_aluno));
$$;

create or replace function novo.enxerga_aluno(p_aluno uuid)
returns boolean language sql stable security definer set search_path = '' as $$
  select novo.e_staff()
      or novo.aluno_sob_responsavel(p_aluno)
      or (novo.tem_papel('professor') and novo.aluno_na_minha_unidade(p_aluno))
      or (novo.tem_papel('especialista') and novo.aluno_que_atendo(p_aluno));
$$;

-- -----------------------------------------------------------------------------
-- 3. Catálogo e referência — sem dado pessoal
-- -----------------------------------------------------------------------------
create policy ref_leitura on novo.unidade              for select to authenticated using (true);
create policy ref_leitura on novo.servico              for select to authenticated using (true);
create policy ref_leitura on novo.plano                for select to authenticated using (true);
create policy ref_leitura on novo.plano_beneficio      for select to authenticated using (true);
create policy ref_leitura on novo.papel                for select to authenticated using (true);
create policy ref_leitura on novo.metrica              for select to authenticated using (true);
create policy ref_leitura on novo.catalogo_item        for select to authenticated using (true);
create policy ref_staff   on novo.configuracao_unidade for select to authenticated using (novo.e_staff());

-- -----------------------------------------------------------------------------
-- 4. Cadastro e identidade
-- -----------------------------------------------------------------------------
create policy pessoa_propria_ou_aluno_visivel on novo.pessoa
  for select to authenticated using (
    id = novo.pessoa_atual()
    or novo.e_staff()
    or exists (select 1 from novo.aluno a where a.pessoa_id = novo.pessoa.id
                and novo.enxerga_aluno(a.id))
  );

create policy perfil_proprio_ou_staff on novo.perfil_usuario
  for select to authenticated using (usuario_id = auth.uid() or novo.e_staff());

create policy papel_proprio_ou_staff on novo.papel_usuario
  for select to authenticated using (usuario_id = auth.uid() or novo.e_staff());

create policy aluno_visivel on novo.aluno
  for select to authenticated using (novo.enxerga_aluno(id));

create policy aluno_servico_pelo_aluno on novo.aluno_servico
  for select to authenticated using (novo.enxerga_aluno(aluno_id));

create policy responsavel_proprio_ou_aluno_visivel on novo.responsavel_aluno
  for select to authenticated using (
    pessoa_id = novo.pessoa_atual() or novo.enxerga_aluno(aluno_id)
  );

create policy profissional_leitura on novo.profissional
  for select to authenticated using (true);

create policy profissional_servico_leitura on novo.profissional_servico
  for select to authenticated using (true);

-- -----------------------------------------------------------------------------
-- 5. Comercial e créditos — staff e responsável
-- -----------------------------------------------------------------------------
create policy matricula_staff_ou_responsavel on novo.matricula
  for select to authenticated using (
    novo.e_staff() or novo.aluno_sob_responsavel(aluno_id)
  );

create policy renovacao_pela_matricula on novo.renovacao
  for select to authenticated using (
    novo.e_staff() or novo.aluno_sob_responsavel(aluno_id)
  );

create policy credito_staff_ou_responsavel on novo.credito_lancamento
  for select to authenticated using (
    novo.e_staff() or novo.aluno_sob_responsavel(aluno_id)
  );

-- -----------------------------------------------------------------------------
-- 6. Agenda e treino
-- Grade e bloqueio são disponibilidade: todo usuário logado precisa deles.
-- -----------------------------------------------------------------------------
create policy grade_leitura    on novo.horario_grade   for select to authenticated using (true);
create policy bloqueio_leitura on novo.bloqueio_agenda for select to authenticated using (true);
create policy bloqueio_grade_leitura on novo.bloqueio_grade for select to authenticated using (true);

create policy agendamento_aluno_visivel_ou_meu on novo.agendamento
  for select to authenticated using (
    novo.enxerga_aluno(aluno_id) or profissional_id = auth.uid()
  );

create policy sessao_pelo_agendamento on novo.sessao_treino
  for select to authenticated using (
    profissional_id = auth.uid()
    or exists (select 1 from novo.agendamento a
                where a.id = novo.sessao_treino.agendamento_id
                  and novo.enxerga_aluno(a.aluno_id))
  );

create policy lista_espera_aluno_visivel on novo.lista_espera
  for select to authenticated using (novo.enxerga_aluno(aluno_id));

create policy feedback_pelo_agendamento on novo.feedback_treino
  for select to authenticated using (
    exists (select 1 from novo.agendamento a
             where a.id = novo.feedback_treino.agendamento_id
               and (novo.enxerga_aluno(a.aluno_id) or a.profissional_id = auth.uid()))
  );

-- relatorio_treino tem campo de dor: segue o aluno, não é aberto por unidade.
create policy relatorio_aluno_visivel_ou_meu on novo.relatorio_treino
  for select to authenticated using (
    novo.enxerga_aluno(aluno_id) or profissional_id = auth.uid()
  );

create policy relatorio_item_pelo_relatorio on novo.relatorio_item
  for select to authenticated using (
    exists (select 1 from novo.relatorio_treino r
             where r.id = novo.relatorio_item.relatorio_id
               and (novo.enxerga_aluno(r.aluno_id) or r.profissional_id = auth.uid()))
  );

-- -----------------------------------------------------------------------------
-- 7. Avaliação
-- CONVENCOES §7: a avaliação de fisioterapia não tem coluna de
-- confidencialidade; a política filtra por tipo. São 4 avaliações e 189 medidas
-- clínicas convivendo com 59 testes físicos na mesma tabela.
-- -----------------------------------------------------------------------------
create policy avaliacao_clinica_restrita on novo.avaliacao
  for select to authenticated using (
    case when tipo = 'fisioterapia'
         then novo.pode_ver_clinico(aluno_id)
         else novo.enxerga_aluno(aluno_id) or avaliador_id = auth.uid() end
  );

create policy medida_pela_avaliacao on novo.avaliacao_medida
  for select to authenticated using (
    exists (select 1 from novo.avaliacao v
             where v.id = novo.avaliacao_medida.avaliacao_id
               and case when v.tipo = 'fisioterapia'
                        then novo.pode_ver_clinico(v.aluno_id)
                        else novo.enxerga_aluno(v.aluno_id) or v.avaliador_id = auth.uid() end)
  );

-- -----------------------------------------------------------------------------
-- 8. Atendimento especializado e dado clínico (pendência 5)
-- CONVENCOES §7: atendimento é filtrado por servico_id. Nem recepção, nem
-- professor, nem responsável leem.
-- -----------------------------------------------------------------------------
create policy atendimento_clinico on novo.atendimento
  for select to authenticated using (
    profissional_id = auth.uid()
    or novo.tem_papel('admin')
    or (novo.tem_papel('especialista')
        and novo.aluno_que_atendo(aluno_id)
        and exists (select 1 from novo.profissional_servico ps
                     where ps.profissional_id = auth.uid()
                       and ps.servico_id = novo.atendimento.servico_id))
  );

create policy evolucao_pelo_atendimento on novo.evolucao
  for select to authenticated using (
    exists (select 1 from novo.atendimento t
             where t.id = novo.evolucao.atendimento_id
               and (t.profissional_id = auth.uid() or novo.tem_papel('admin')))
  );

create policy anamnese_clinica_restrita on novo.anamnese
  for select to authenticated using (novo.pode_ver_clinico(aluno_id));

-- -----------------------------------------------------------------------------
-- 9. Documentos e comunicação
-- Os valores reais de arquivo.confidencialidade são 'clinico' e 'normal' (em
-- anamnese, 'restrito'). A regra fecha por padrão: só 'normal' segue o caminho
-- aberto; nulo ou valor novo cai no clínico.
-- -----------------------------------------------------------------------------
create policy arquivo_clinico_restrito on novo.arquivo
  for select to authenticated using (
    case when coalesce(confidencialidade, 'restrito') = 'normal'
         then novo.enxerga_aluno(aluno_id)
         else novo.pode_ver_clinico(aluno_id) end
  );

create policy consentimento_proprio_ou_staff on novo.consentimento
  for select to authenticated using (
    pessoa_id = novo.pessoa_atual() or novo.e_staff()
  );

create policy emissao_pelo_aluno on novo.relatorio_emissao
  for select to authenticated using (novo.enxerga_aluno(aluno_id));

create policy envio_pela_emissao on novo.relatorio_envio
  for select to authenticated using (
    exists (select 1 from novo.relatorio_emissao e
             where e.id = novo.relatorio_envio.emissao_id
               and novo.enxerga_aluno(e.aluno_id))
  );

create policy notificacao_propria on novo.notificacao
  for select to authenticated using (usuario_id = auth.uid());

-- -----------------------------------------------------------------------------
-- 10. Auditoria — sem grant e sem política (pendência 11)
-- evento_auditoria guarda valor_anterior e valor_novo em jsonb, que podem
-- carregar dado pessoal. Leitura só por papel privilegiado até a decisão.
-- -----------------------------------------------------------------------------

commit;

-- =============================================================================
-- Teste por papel, depois de aplicar (segunda metade da 3.3):
--   set local role authenticated;
--   set local request.jwt.claims = '{"sub":"<usuario_id>"}';
--   select count(*) from novo.aluno;                      -- muda conforme o papel
--   select count(*) from novo.anamnese;                   -- 0 fora de admin e do especialista
--   select count(*) from novo.avaliacao where tipo = 'fisioterapia';  -- idem
--   select count(*) from novo.evento_auditoria;           -- erro de permissão
--   reset role;
-- =============================================================================
