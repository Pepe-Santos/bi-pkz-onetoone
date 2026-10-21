-- =============================================================================
-- conferencia/02_papel_unidade.sql
-- Papéis globais × papéis por unidade (novo.papel_usuario.unidade_id). SÓ LEITURA.
--
-- Regra da carga (script 20, mapeamento/cadastro.csv):
--   * unidade_id preenchida só quando o PRÓPRIO papel da origem diz a unidade:
--     professor_pkz → pkz; professor_one_to_one → one_to_one.
--   * unidade_id nula = o papel vale para TODAS as unidades: admin, professor
--     (sem sufixo), especialista (fisio, nutri, psico: agenda compartilhada entre
--     as unidades, migration 009), responsavel (a unidade vem da matrícula do
--     aluno) e recepcao (pendência na carga).
-- Explicação completa: mapeamento/README.md, seção "Papéis e unidade".
-- Nenhuma consulta mostra dado pessoal: só papéis e contagens.
-- =============================================================================

-- 1) Distribuição: papel novo × papel da origem × unidade
select p.codigo                         as papel,
       pu.papel_origem,
       coalesce(u.codigo, '(todas)')    as unidade,
       count(*)                         as n
from novo.papel_usuario pu
join novo.papel p on p.id = pu.papel_id
left join novo.unidade u on u.id = pu.unidade_id
group by 1, 2, 3
order by 1, 2, 3;

-- 2) Resumo: com e sem unidade
select count(*)                                   as total,
       count(*) filter (where unidade_id is null)     as globais,
       count(*) filter (where unidade_id is not null) as por_unidade
from novo.papel_usuario;

-- 3) Violações da regra (tem que voltar vazio)
--    a) papel com unidade que não veio de professor_pkz / professor_one_to_one
--    b) professor_pkz / professor_one_to_one sem unidade, ou na unidade errada
select pu.id, p.codigo as papel, pu.papel_origem, u.codigo as unidade,
       case when pu.unidade_id is not null and pu.papel_origem not in ('professor_pkz', 'professor_one_to_one')
            then 'unidade preenchida em papel global'
            else 'professor de unidade sem a unidade certa' end as problema
from novo.papel_usuario pu
join novo.papel p on p.id = pu.papel_id
left join novo.unidade u on u.id = pu.unidade_id
where (pu.unidade_id is not null and pu.papel_origem not in ('professor_pkz', 'professor_one_to_one'))
   or (pu.papel_origem = 'professor_pkz'        and coalesce(u.codigo, '') <> 'pkz')
   or (pu.papel_origem = 'professor_one_to_one' and coalesce(u.codigo, '') <> 'one_to_one');
