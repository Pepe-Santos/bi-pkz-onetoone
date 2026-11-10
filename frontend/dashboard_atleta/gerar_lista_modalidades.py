"""Gera modalidades_atletas.csv, para a escola preencher a coluna modalidade no Excel.

O arquivo tem nomes de menores: fica só nesta máquina, fora do GitHub. Quem já está preenchido é mantido.
Quando a API informar a modalidade, esta lista deixa de ser necessária.
"""
import csv

import dados


def main() -> None:
    preenchidos = dados._modalidades_do_arquivo()
    atletas = dados.atletas_pkz()
    with dados.ARQUIVO_MODALIDADES.open("w", encoding="utf-8-sig", newline="") as arquivo:
        saida = csv.writer(arquivo, delimiter=";")
        saida.writerow(["atleta_id", "nome", "categoria", "idade", "modalidade"])
        for a in atletas:
            saida.writerow([a["atleta_id"], a["nome"], a["categoria"] or "", a["idade"] if a["idade"] is not None else "",
                            preenchidos.get(a["atleta_id"]) or a["modalidade"] or ""])
    print(f"{len(atletas)} atletas em {dados.ARQUIVO_MODALIDADES.name}")


if __name__ == "__main__":
    main()
