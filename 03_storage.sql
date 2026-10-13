-- Bucket privado para os PDFs dos relatórios.
-- public = false: ninguém lê pela URL direta. O acesso é por URL assinada (temporária)
-- ou pela secret key (gerador de relatórios).
INSERT INTO storage.buckets (id, name, public)
VALUES ('teste', 'teste', false)
ON CONFLICT (id) DO UPDATE SET public = false;  -- garante que continua privado ao rodar de novo

-- Nenhuma policy em storage.objects de propósito: com RLS ligado e sem policy,
-- usuários comuns não acessam nada. A secret key ignora o RLS.
