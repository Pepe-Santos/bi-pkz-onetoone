"""Cria um usuário da API já confirmado e com a unidade que ele pode ver.

Faz num passo só o que no painel do Supabase exige dois (Add user + UPDATE da unidade).
Usa a API de administração do Supabase, então precisa da SUPABASE_SECRET_KEY no
backend/.env (veja backend/env.example).

    python backend/scripts/criar_usuario.py <email> <senha> <PKZ|ONE_TO_ONE|TODAS>
"""

import os
import sys

from testar_acesso import ENV_PATH, carregar_env, requisicao

UNIDADES = ("PKZ", "ONE_TO_ONE", "TODAS")


def main():
    if len(sys.argv) != 4:
        sys.exit("Uso: python backend/scripts/criar_usuario.py <email> <senha> <PKZ|ONE_TO_ONE|TODAS>")
    email, senha, unidade = sys.argv[1], sys.argv[2], sys.argv[3].upper()
    if unidade not in UNIDADES:
        sys.exit(f"Unidade inválida: {sys.argv[3]}. Use {', '.join(UNIDADES)}.")

    carregar_env(ENV_PATH)
    faltando = [nome for nome in ("SUPABASE_URL", "SUPABASE_SECRET_KEY") if not os.environ.get(nome)]
    if faltando:
        sys.exit(f"Faltam variáveis no backend/.env: {', '.join(faltando)}")

    base = os.environ["SUPABASE_URL"].rstrip("/")
    secret = os.environ["SUPABASE_SECRET_KEY"]
    status, resp = requisicao(
        "POST",
        f"{base}/auth/v1/admin/users",
        {"apikey": secret, "Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
        {
            "email": email,
            "password": senha,
            "email_confirm": True,
            "app_metadata": {"unidade": unidade},
        },
    )

    if status == 200:
        print(f"Usuário {email} criado, confirmado e com unidade {unidade}.")
        return
    if isinstance(resp, dict) and resp.get("error_code") == "email_exists":
        sys.exit(f"Já existe um usuário com o e-mail {email}. Para mudar a unidade dele, use o "
                 "UPDATE da seção \"Criar um usuário\" do backend/docs/api.md.")
    mensagem = resp.get("msg") or resp.get("message") if isinstance(resp, dict) else resp
    sys.exit(f"Não foi possível criar o usuário ({status}): {mensagem}")


if __name__ == "__main__":
    main()
