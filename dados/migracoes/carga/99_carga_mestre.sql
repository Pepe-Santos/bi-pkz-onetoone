-- =============================================================================
-- 99_carga_mestre.sql
-- Script mestre (tarefa 1.7)       Dono: Micael (Frente 1)
-- Roda as cargas 10 a 80 na ordem de dependência e, no fim, a conferência geral.
--
-- Uso (psql, de dentro de dados/migracoes, porque os \i são relativos):
--   psql $env:ENSAIO_URL -f carga/99_carga_mestre.sql
--
-- Pré-requisitos: migrations 001–011 aplicadas e o gabarito registrado
--   (select novo.registrar_gabarito('congelamento-2026-10-12');).
-- Cada script é uma transação própria: se um falhar, o psql para ali
-- (ON_ERROR_STOP) e os anteriores ficam gravados. Corrija e rode o mestre de
-- novo: todos os scripts podem rodar quantas vezes for preciso, sem duplicar.
--
-- Ensaio geral: rodar o mestre DUAS vezes. As contagens da conferência
-- (e de novo.v_resumo_carga) não podem mudar entre a primeira e a segunda.
-- =============================================================================
\set ON_ERROR_STOP on
\timing on

\echo '== 10 referência'
\i carga/10_carga_referencia.sql
\echo '== 20 cadastro'
\i carga/20_carga_cadastro.sql
\echo '== 30 comercial'
\i carga/30_carga_comercial.sql
\echo '== 40 agenda'
\i carga/40_carga_agenda.sql
\echo '== 50 relatório'
\i carga/50_carga_relatorio.sql
\echo '== 60 avaliação'
\i carga/60_carga_avaliacao.sql
\echo '== 70 atendimento'
\i carga/70_carga_atendimento.sql
\echo '== 80 documentos'
\i carga/80_carga_documentos.sql

\timing off
\echo '== conferência geral (só leitura)'
\i conferencia/99_conferencia_geral.sql
