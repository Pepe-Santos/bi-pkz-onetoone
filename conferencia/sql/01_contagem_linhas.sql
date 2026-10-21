-- Tarefa 2.1 / Conferência 1: quantidade de registros por tabela de origem.
-- Fonte exclusiva: schema origem.
-- Não inclui tabelas de destino nem realiza qualquer escrita.

SELECT 'origem.activity_logs' AS tabela, COUNT(*) AS quantidade FROM origem.activity_logs
UNION ALL SELECT 'origem.app_settings', COUNT(*) FROM origem.app_settings
UNION ALL SELECT 'origem.athlete_access_links', COUNT(*) FROM origem.athlete_access_links
UNION ALL SELECT 'origem.athletes', COUNT(*) FROM origem.athletes
UNION ALL SELECT 'origem.booking_audit_logs', COUNT(*) FROM origem.booking_audit_logs
UNION ALL SELECT 'origem.bookings', COUNT(*) FROM origem.bookings
UNION ALL SELECT 'origem.credit_transactions', COUNT(*) FROM origem.credit_transactions
UNION ALL SELECT 'origem.notifications', COUNT(*) FROM origem.notifications
UNION ALL SELECT 'origem.nutritionist_files', COUNT(*) FROM origem.nutritionist_files
UNION ALL SELECT 'origem.physical_test_comparisons', COUNT(*) FROM origem.physical_test_comparisons
UNION ALL SELECT 'origem.physical_test_sessions', COUNT(*) FROM origem.physical_test_sessions
UNION ALL SELECT 'origem.physio_assessments', COUNT(*) FROM origem.physio_assessments
UNION ALL SELECT 'origem.physio_evolutions', COUNT(*) FROM origem.physio_evolutions
UNION ALL SELECT 'origem.profiles', COUNT(*) FROM origem.profiles
UNION ALL SELECT 'origem.registration_invites', COUNT(*) FROM origem.registration_invites
UNION ALL SELECT 'origem.schedule_blocks', COUNT(*) FROM origem.schedule_blocks
UNION ALL SELECT 'origem.specialist_evolutions', COUNT(*) FROM origem.specialist_evolutions
UNION ALL SELECT 'origem.student_files', COUNT(*) FROM origem.student_files
UNION ALL SELECT 'origem.student_tests', COUNT(*) FROM origem.student_tests
UNION ALL SELECT 'origem.student_timeline', COUNT(*) FROM origem.student_timeline
UNION ALL SELECT 'origem.training_feedback', COUNT(*) FROM origem.training_feedback
UNION ALL SELECT 'origem.training_report_materials', COUNT(*) FROM origem.training_report_materials
UNION ALL SELECT 'origem.training_report_technologies', COUNT(*) FROM origem.training_report_technologies
UNION ALL SELECT 'origem.training_reports', COUNT(*) FROM origem.training_reports
UNION ALL SELECT 'origem.training_slots', COUNT(*) FROM origem.training_slots
UNION ALL SELECT 'origem.user_roles', COUNT(*) FROM origem.user_roles
UNION ALL SELECT 'origem.waitlist', COUNT(*) FROM origem.waitlist
UNION ALL SELECT 'origem.weekly_evaluations', COUNT(*) FROM origem.weekly_evaluations
ORDER BY tabela;
