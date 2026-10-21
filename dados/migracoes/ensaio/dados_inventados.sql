-- =============================================================================
-- ensaio/dados_inventados.sql
-- Dados 100% INVENTADOS para testar os scripts de carga num Postgres local.
-- Nada aqui vem da origem real. Ordem: origem_estrutura_local.sql → este arquivo →
-- 001 → congelar_origem.sql → 002…009 → carga/10, 20 (duas vezes: contagens iguais).
-- Cobre: categoria 'sub 10'/só número, adulto = responsável, admin atuando como
-- professor, especialista com 2 papéis, recepção, perfil sem nome, One to One sem plano.
-- Os próximos scripts (30–80) acrescentam casos aqui.
-- =============================================================================
insert into public.app_settings (id, monthly_credits, renewal_weekday, credits_fisio_standard, credits_nutri_standard) values (1, 8, 7, 1, 1);
insert into public.profiles (id, full_name, username, phone, can_schedule) values
 ('10000000-0000-0000-0000-000000000001','Ana Admin','ana.admin',null,true),
 ('10000000-0000-0000-0000-000000000002','Bruno Prof','bruno.prof','2199990000',false),
 ('10000000-0000-0000-0000-000000000003','Carla Fisio','carla.fisio',null,false),
 ('10000000-0000-0000-0000-000000000004','Davi Especialista','davi.esp',null,false),
 ('10000000-0000-0000-0000-000000000005','Eva Recepção','eva.recepcao',null,false),
 ('10000000-0000-0000-0000-000000000006','Fábio Responsável','fabio.resp',null,true),
 ('10000000-0000-0000-0000-000000000007','','gabi.semnome',null,true),
 ('10000000-0000-0000-0000-000000000008','Hugo  Adulto','hugo.adulto',null,true);
insert into public.user_roles (user_id, role) values
 ('10000000-0000-0000-0000-000000000001','admin'),
 ('10000000-0000-0000-0000-000000000002','professor_pkz'),('10000000-0000-0000-0000-000000000002','professor_one_to_one'),
 ('10000000-0000-0000-0000-000000000003','fisioterapeuta'),
 ('10000000-0000-0000-0000-000000000004','nutricionista'),('10000000-0000-0000-0000-000000000004','psicologo'),
 ('10000000-0000-0000-0000-000000000005','recepcao'),
 ('10000000-0000-0000-0000-000000000006','responsavel'),('10000000-0000-0000-0000-000000000007','responsavel'),
 ('10000000-0000-0000-0000-000000000008','responsavel');
insert into public.athletes (id, name, category, responsavel_id, program, plan, allowed_services) values
 ('20000000-0000-0000-0000-000000000001','Iara Criança',' Sub 10 ','10000000-0000-0000-0000-000000000006','pkz',null,'{treino,fisioterapeuta}'),
 ('20000000-0000-0000-0000-000000000002','João Criança','13','10000000-0000-0000-0000-000000000007','pkz',null,'{treino}'),
 ('20000000-0000-0000-0000-000000000003','hugo adulto','Natação','10000000-0000-0000-0000-000000000008','one_to_one','one_move','{treino,nutricionista,psicologo}'),
 ('20000000-0000-0000-0000-000000000004','Karen Sem Plano',null,'10000000-0000-0000-0000-000000000006','one_to_one',null,'{treino}');
insert into public.bookings (athlete_id, service, slot_date, start_time, professor_id) values
 ('20000000-0000-0000-0000-000000000001','treino','2026-09-01','09:00','10000000-0000-0000-0000-000000000001'),
 ('20000000-0000-0000-0000-000000000003','treino','2026-09-01','18:00','10000000-0000-0000-0000-000000000002');
insert into public.physio_evolutions (athlete_id, physio_id, file_name, storage_path) values
 ('20000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000003','x.pdf','fake/x.pdf');

-- ---------------------------------------------------------------------------
-- Casos para os scripts 30–50 (15/10)
-- ---------------------------------------------------------------------------
update public.athletes set credits = 5 where id = '20000000-0000-0000-0000-000000000001';   -- extrato vai dar 4: saldo divergente
update public.athletes set monthly_plan = 8 where id = '20000000-0000-0000-0000-000000000002';
insert into public.credit_transactions (athlete_id, delta, reason, actor_id, created_at) values
 ('20000000-0000-0000-0000-000000000001', 4, 'Renovação mensal PKZ', null, '2026-09-01 03:00+00'),
 ('20000000-0000-0000-0000-000000000003', 3, 'Renovação semanal treino', null, '2026-09-01 03:00+00'),
 ('20000000-0000-0000-0000-000000000003', 1, 'Renovação mensal nutri', null, '2026-09-01 03:00+00'),
 ('20000000-0000-0000-0000-000000000003', 1, 'Renovação mensal nutri', null, '2026-09-01 04:00+00'),   -- 2 na mesma competência
 ('20000000-0000-0000-0000-000000000003', -1, 'Agendamento: treino 01/09 18:00 [treino]', '10000000-0000-0000-0000-000000000008', '2026-09-01 12:00+00'),
 ('20000000-0000-0000-0000-000000000003', -1, 'Solicitação: psicologo 02/09 [treino]', '10000000-0000-0000-0000-000000000008', '2026-09-02 12:00+00'),
 ('20000000-0000-0000-0000-000000000003', 1, 'Cancelamento dentro do prazo [treino]', '10000000-0000-0000-0000-000000000001', '2026-09-02 13:00+00'),
 ('20000000-0000-0000-0000-000000000003', 2, 'Bônus de boas-vindas', '10000000-0000-0000-0000-000000000077', '2026-09-03 13:00+00'); -- origem desconhecida, ator inexistente
insert into public.schedule_blocks (service, block_date, start_time, end_time, reason, is_permanent, weekday) values
 ('treino', '2026-09-07', '08:00', '12:00', 'feriado', false, null),
 (null, '2026-09-01', '12:00', '13:00', 'almoço', true, 3),
 (null, '2026-09-01', '07:00', '07:30', 'abertura', true, null);
insert into public.bookings (id, athlete_id, service, slot_date, start_time, status, professor_id, created_at) values
 ('30000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000003','fisioterapeuta','2026-09-02','10:00','presente',null,'2026-09-01'),
 ('30000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000004','treino','2026-09-02','18:00','cancelado',null,'2026-09-01'),
 ('30000000-0000-0000-0000-000000000003','20000000-0000-0000-0000-000000000004','treino','2026-09-03','18:00','cancelado',null,'2026-09-01'),
 ('30000000-0000-0000-0000-000000000004','20000000-0000-0000-0000-000000000002','treino','2026-09-06','15:00','agendado',null,'2026-09-01'), -- domingo: fora da grade
 ('30000000-0000-0000-0000-000000000005','20000000-0000-0000-0000-000000000001','treino','2026-09-04','09:00','presente','10000000-0000-0000-0000-000000000002','2026-09-01');
insert into public.specialist_evolutions (booking_id, athlete_id, professional_id, service, file_path, file_name) values
 ('30000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000003','10000000-0000-0000-0000-000000000003','fisioterapeuta','fake/e.pdf','e.pdf');
insert into public.activity_logs (actor_id, action, entity, entity_id, payload, created_at) values
 ('10000000-0000-0000-0000-000000000001','cancel_booking','booking','30000000-0000-0000-0000-000000000002','{"refund":true}','2026-09-01 20:00+00'),
 ('10000000-0000-0000-0000-000000000002','mark_attendance','booking','30000000-0000-0000-0000-000000000005','{"status":"presente"}','2026-09-04 13:00+00');
insert into public.training_feedback (booking_id, athlete_id, rating_treino, rating_professor, liked) values
 ('30000000-0000-0000-0000-000000000005','20000000-0000-0000-0000-000000000001',5,4,'{energia}');
insert into public.training_report_materials (name, sort_order) values ('Cones', 1), ('Elástico', 2);
insert into public.training_report_technologies (name, sort_order) values ('Blazepod', 1);
insert into public.training_reports (athlete_id, report_date, professor_id, booking_id, report_kind, status, start_time, end_time,
                                     materials, technologies, capacidades_fisicas, foco, conduta, materials_other) values
 ('20000000-0000-0000-0000-000000000001','2026-09-04','10000000-0000-0000-0000-000000000002','30000000-0000-0000-0000-000000000005','pkz','final','09:00','10:00',
  '{Cones,Elástico}','{Blazepod}','{Força}','{MMII}','{Progredir}', 'Bola suíça'),
 ('20000000-0000-0000-0000-000000000001','2026-09-04','10000000-0000-0000-0000-000000000002','30000000-0000-0000-0000-000000000005','pkz','rascunho','09:00','08:00',
  '{Cones}','{}','{Força,Velocidade}','{}','{}', null),                              -- duplicado + fim antes do início
 ('20000000-0000-0000-0000-000000000003','2026-09-05','10000000-0000-0000-0000-000000000001','30000000-0000-0000-0000-000000000005','pkz','final',null,null,
  '{}','{}','{}','{Core}','{Manter}', null);                                          -- agendamento de outro aluno; tipo pkz em aluno One to One

-- ---------------------------------------------------------------------------
-- Casos para os scripts 60–80 (16/10). Tudo inventado.
-- ---------------------------------------------------------------------------
-- 60: teste físico completo; legado do blazepod + texto antigo + hop abaixo de 10 + avaliador só por nome;
--     aluno inexistente (rejeitado); chave sem métrica (rejeitada)
insert into public.physical_test_sessions (id, athlete_id, test_date, evaluator_id, evaluator_name, altura, peso, data, created_at) values
 ('40000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','2026-09-10','10000000-0000-0000-0000-000000000002',null,1.42,38.5,
  '{"sprint_10":["2,10","2,05",""],"banco_wells":["22","",""],"single_hop":{"direita":["120","118",""],"esquerda":["115","",""]},
    "cross_hop":{"direita":["300","",""],"esquerda":["290","",""]},"saltos_vert":{"squat_jump":["21,5","",""],"countermovement":["",""," "],"abalakov":["25","",""]},
    "blazepod_vel_reacao":{"hits":["30","",""],"ms":["450","",""]},"teste_vo2":{"vel_max":"12,5","tempo_total":"08:30","distancia_total":"1500","tempo_vel_max":"01:10"}}',
  '2026-09-10 12:00+00'),
 ('40000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000003','2026-09-11',null,'Avaliador Externo',null,70,
  '{"blazepod_vel_reacao":["30","28",""],"estabilidade_aquabag":["2 3 1","",""],"single_hop":{"direita":["1,2","",""],"esquerda":["",""," "]},
    "teste_vo2":{"vel_max":"","tempo_total":"8 min","distancia_total":"1,5","tempo_vel_max":""},"teste_novo":["5","",""]}',
  '2026-09-11 12:00+00'),
 ('40000000-0000-0000-0000-000000000003','20000000-0000-0000-0000-000000000099','2026-09-12',null,null,null,null,'{}','2026-09-12 12:00+00');
-- semanal: unidade diferente da do aluno (aluno 1 é pkz)
insert into public.weekly_evaluations (id, athlete_id, week_start_date, rating_quality, rating_service, rating_environment,
                                       rating_evolution, rating_satisfaction, observations, unit, created_at) values
 ('41000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','2026-09-07',5,4,5,4,5,'ok','one_to_one','2026-09-12 12:00+00');
-- 70: avaliação de fisio PKZ final com pkz_data; One to One rascunho com programa diferente
insert into public.physio_assessments (id, athlete_id, physio_id, physio_name, assessment_date, queixa_principal, hda,
  ombro_rot_ext_dir, ombro_rot_ext_esq, appley_dir_sup, appley_esq_sup, appley_dir_inf, joelho_flex_dir,
  observacao, file_path, status, program, pkz_data, created_at, updated_at) values
 ('42000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000003',null,'2026-09-15',
  'dor inventada','', 90, 85, 'Positivo','Não avaliado','', 140, 'obs inventada','fake/avaliacao1.pdf','final','pkz',
  '{"forca_ext_quadril_dir":"12,5","forca_ext_quadril_esq":"11","forca_abdominal":"20","ratio_flexext_joelho_dir":"60",
    "mob_tornozelo_dir":"33º","mob_tornozelo_esq":"x","post_anterior_tibia_dir_dir":"Interna","post_anterior_tibia_dir_valor":"5",
    "post_anterior_inclinacao_cabeca_dir":"Direita","post_anterior_inclinacao_cabeca_valor":"2",
    "post_lateral_dir_flexao_joelho_dir":"Anterior","post_lateral_dir_flexao_joelho_valor":"3",
    "rotina_escola":"manhã","qualidade_sono":"boa","hpp_d_alergica":"","img_anterior":"fake/img_ant.jpg",
    "img_mob_tornozelo_dir":"fake/img_mob.jpg","carimbo_path":"fake/carimbo.png","chave_estranha":"1"}',
  '2026-09-15 12:00+00','2026-09-15 13:00+00'),
 ('42000000-0000-0000-0000-000000000002','20000000-0000-0000-0000-000000000003',null,'Fisio Externa','2026-09-16',
  null,null,null,null,null,null,null,null,null,null,'rascunho','pkz','{}','2026-09-16 12:00+00','2026-09-16 12:00+00');
-- 70: atendimento de serviço treino (rejeitado), agendamento de outro aluno, especialista presente sem atendimento
insert into public.bookings (id, athlete_id, service, slot_date, start_time, status, professor_id, created_at) values
 ('30000000-0000-0000-0000-000000000006','20000000-0000-0000-0000-000000000003','nutricionista','2026-09-08','10:00','presente','10000000-0000-0000-0000-000000000004','2026-09-01');
insert into public.specialist_evolutions (booking_id, athlete_id, professional_id, service, file_path, file_name) values
 ('30000000-0000-0000-0000-000000000005','20000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000002','treino','fake/t.pdf','t.pdf'),
 ('30000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001','10000000-0000-0000-0000-000000000003','fisioterapeuta','fake/o.pdf','o.pdf');
-- 80: arquivos (pasta 02 igual ao PDF do relatório; pasta 05; caminho de dois alunos; comparativo)
update public.training_reports set file_path = 'fake/rel1.pdf', pdf_storage_path = 'fake/rel1.pdf'
 where athlete_id = '20000000-0000-0000-0000-000000000001' and status = 'final';
insert into public.student_files (athlete_id, folder, file_name, storage_path, mime_type, size_bytes, uploaded_by) values
 ('20000000-0000-0000-0000-000000000001','02_Relatorios_de_Treino','rel1.pdf','fake/rel1.pdf','application/pdf',1000,'10000000-0000-0000-0000-000000000002'),
 ('20000000-0000-0000-0000-000000000001','05_Fisioterapia','f.pdf','fake/f.pdf',null,500,null),
 ('20000000-0000-0000-0000-000000000001','03_Evolucao_e_Comparativos','dois.pdf','fake/dois.pdf',null,1,null),
 ('20000000-0000-0000-0000-000000000002','03_Evolucao_e_Comparativos','dois.pdf','fake/dois.pdf',null,1,null);
insert into public.physical_test_comparisons (athlete_id, session_a_id, session_b_id, file_path, created_by) values
 ('20000000-0000-0000-0000-000000000001','40000000-0000-0000-0000-000000000001','40000000-0000-0000-0000-000000000001','fake/comp.pdf','10000000-0000-0000-0000-000000000002');
insert into public.student_tests (athlete_id, test_type, test_date, file_path) values ('20000000-0000-0000-0000-000000000001','x','2026-09-01','');
-- 80: auditoria (dado pessoal no payload, ator inexistente, ação padronizada, troca de professor sem data)
insert into public.activity_logs (actor_id, action, entity, entity_id, payload, created_at) values
 ('10000000-0000-0000-0000-000000000001','Link de ativação enviado via WhatsApp',null,null,'{"athlete_name":"Nome Inventado","phone":"21900000000"}','2026-09-02 10:00+00'),
 ('10000000-0000-0000-0000-000000000001','admin_create_user','user','10000000-0000-0000-0000-000000000005','{"username":"eva.recepcao","role":"recepcao"}','2026-09-02 11:00+00'),
 ('10000000-0000-0000-0000-000000000077','assign_booking_professor','booking','30000000-0000-0000-0000-000000000005','{"professor_id":"10000000-0000-0000-0000-000000000002"}','2026-09-02 12:00+00'),
 ('10000000-0000-0000-0000-000000000001','adjust_credits','athlete','20000000-0000-0000-0000-000000000001','{"delta":1}','2026-09-02 13:00+00');
insert into public.booking_audit_logs (booking_id, action, actor_id, previous_professor_id, new_professor_id, reason, created_at, created_by) values
 ('30000000-0000-0000-0000-000000000005','professor_assigned',null,null,'10000000-0000-0000-0000-000000000002','troca',null,'10000000-0000-0000-0000-000000000001');
