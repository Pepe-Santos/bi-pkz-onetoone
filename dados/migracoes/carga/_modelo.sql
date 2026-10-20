-- =============================================================================
-- MODELO de script de carga. Copie para carga/NN_carga_<dominio>.sql e preencha.
-- Este arquivo não é executado pelo script mestre (começa com "_").
--
-- NN_carga_<dominio>.sql
-- Domínio: <dominio>              Dono: <nome>
-- Origem:  origem.<tabela_a>, origem.<tabela_b>   (nunca public: ver CONVENCOES.md)
-- Destino: novo.<tabela_x>, novo.<tabela_y>
-- Depende de: 10_carga_referencia, 20_carga_cadastro (fundação carregada)
-- Mapeamento: mapeamento/<dominio>.csv
-- =============================================================================
\set ON_ERROR_STOP on

begin;

-- Liga o modo de carga só nesta transação (ver CONVENCOES.md, "Triggers").
select set_config('novo.modo_carga', 'on', true);

-- -----------------------------------------------------------------------------
-- a) Rejeitados NÃO são apagados antes (migration 010): a chave única
--    (script, tabela_origem, id_origem, motivo) + "on conflict do nothing"
--    evitam duplicar na reexecução. Não use delete: o conector do Supabase
--    trava esperando uma confirmação que não aparece.
-- -----------------------------------------------------------------------------

-- -----------------------------------------------------------------------------
-- b) Registra o que não passa nas regras (um insert por regra, motivo claro).
--    A carga principal (c) filtra pela MESMA condição, ao contrário.
-- -----------------------------------------------------------------------------
insert into novo.carga_rejeitado (script, tabela_origem, id_origem, motivo)
select '<dominio>', '<tabela_a>', a.id, 'aluno inexistente no destino'
from origem.<tabela_a> a
where not exists (select 1 from novo.aluno al where al.id = a.athlete_id)
on conflict (script, tabela_origem, id_origem, motivo) do nothing;

-- -----------------------------------------------------------------------------
-- c) Carrega, na ordem de dependência. Sempre insert ... select ... on conflict.
--    Chave de reexecução: o id de origem (quando a entidade é a mesma) ou uma
--    combinação única declarada no DDL.
-- -----------------------------------------------------------------------------
insert into novo.<tabela_x> (id, aluno_id, ..., pendencia)
select a.id,
       a.athlete_id,
       ...,
       null                                   -- pendências entram em (d)
from origem.<tabela_a> a
where exists (select 1 from novo.aluno al where al.id = a.athlete_id)
on conflict (id) do update
  set aluno_id      = excluded.aluno_id,
      ...,
      atualizado_em = now();

-- -----------------------------------------------------------------------------
-- d) Marca pendências (dúvida de regra de negócio: entra, mas marcado).
--    juntar_pendencia não repete o texto se o script rodar de novo.
-- -----------------------------------------------------------------------------
update novo.<tabela_x>
set pendencia = novo.juntar_pendencia(pendencia, '<descrição curta da dúvida>')
where <condição>;

-- -----------------------------------------------------------------------------
-- e) Registra a execução. linhas_carregadas = TOTAL no destino deste domínio
--    (não o "quanto entrou agora"), para que duas execuções deem o mesmo número.
-- -----------------------------------------------------------------------------
insert into novo.carga_execucao (script, linhas_carregadas, linhas_rejeitadas)
select '<dominio>',
       (select count(*) from novo.<tabela_x>) + (select count(*) from novo.<tabela_y>),
       (select count(*) from novo.carga_rejeitado where script = '<dominio>');

commit;
