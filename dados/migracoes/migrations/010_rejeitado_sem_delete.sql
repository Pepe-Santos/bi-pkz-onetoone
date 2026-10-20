-- =============================================================================
-- 010_rejeitado_sem_delete.sql
-- Dono: Micael (Frente 1). Pré-requisito: 009_ajuste_mapeamento.sql. 15/10/2026.
--
-- Por quê: os scripts de carga começavam com
--     delete from novo.carga_rejeitado where script = '<dominio>';
-- só para não acumular rejeitados repetidos ao rodar de novo. O conector do
-- Supabase usado no ensaio segura comandos com "delete" à espera de uma
-- confirmação que não aparece no app, e o script nunca roda.
--
-- Solução: chave única no registro de rejeitados. Os scripts gravam o rejeitado
-- com "on conflict do nothing": rodar duas vezes não duplica, sem precisar apagar.
-- Rejeitado de uma regra que deixou de existir fica no registro até o ensaio
-- geral (que recria o schema novo do zero).
-- =============================================================================

create unique index carga_rejeitado_chave
  on novo.carga_rejeitado (script, tabela_origem, id_origem, motivo) nulls not distinct;

comment on index novo.carga_rejeitado_chave is
  'Um rejeitado por (script, tabela, id, motivo): os scripts usam on conflict do nothing em vez de apagar antes.';
