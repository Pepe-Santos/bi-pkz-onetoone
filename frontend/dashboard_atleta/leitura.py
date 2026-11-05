"""Transforma os resultados do atleta no que o professor quer ler: onde está forte e o que mudou.

Testes de tempo têm "menor é melhor". Aqui tudo é convertido para o mesmo sentido: número maior e
barra para a direita sempre significam resultado melhor.
"""
import cartao

FORTE, MEIO, ATENCAO = "Ponto forte", "No meio do grupo", "Ponto de atenção"
LIMITE_FORTE, LIMITE_ATENCAO = 67, 34
LADOS = {"dir": "direita", "esq": "esquerda"}
MUDANCAS_MOSTRADAS = ("melhorou", "piorou", "estavel")


def _nome(linha: dict) -> str:
    lado = LADOS.get(linha["lado"])
    return f"{linha['teste_nome']} · {lado}" if lado else linha["teste_nome"]


def zona(percentil: int) -> str:
    return FORTE if percentil >= LIMITE_FORTE else ATENCAO if percentil < LIMITE_ATENCAO else MEIO


def perfil_do_atleta(linhas: list[dict], ids_do_grupo: list[str], ultimos: dict, minimo: int = 5) -> list[dict]:
    """Um item por teste com direção definida: a posição do atleta entre os colegas, do melhor para o pior."""
    atual = {}
    for linha in sorted(linhas, key=lambda l: l["data_avaliacao"]):
        atual[(linha["teste"], linha["lado"])] = linha
    perfil = []
    for (teste, lado), linha in atual.items():
        if linha["maior_melhor"] is None:
            continue
        grupo = [ultimos[(i, teste, lado)] for i in ids_do_grupo if (i, teste, lado) in ultimos]
        if len(grupo) < minimo:
            continue
        valor = float(linha["valor"])
        percentil = cartao.percentil(valor, grupo, linha["maior_melhor"])
        melhores = sum((v > valor) if linha["maior_melhor"] else (v < valor) for v in grupo)
        perfil.append({"teste": _nome(linha), "percentil": percentil, "zona": zona(percentil),
                       "valor": valor, "unidade": linha["unidade_medida"] or "", "colegas": len(grupo),
                       "posicao": melhores + 1, "total": len(grupo)})
    return sorted(perfil, key=lambda p: (-p["percentil"], p["teste"]))


def posicao_no_teste(linhas: list[dict], ids_do_grupo: list[str], ultimos: dict, minimo: int = 5) -> tuple[int, int] | None:
    """(posição, total) do atleta num teste sem lado, ou None se não há colegas suficientes para comparar."""
    ultima = max(linhas, key=lambda l: l["data_avaliacao"])
    if ultima["maior_melhor"] is None or ultima["lado"]:
        return None
    grupo = [ultimos[(i, ultima["teste"], None)] for i in ids_do_grupo if (i, ultima["teste"], None) in ultimos]
    if len(grupo) < minimo:
        return None
    valor = float(ultima["valor"])
    return sum((v > valor) if ultima["maior_melhor"] else (v < valor) for v in grupo) + 1, len(grupo)


def media_no_grupo(linhas: list[dict], ids_do_grupo: list[str], ultimos: dict, minimo: int = 5) -> float | None:
    """Média do último resultado dos colegas num teste sem lado, ou None se forem poucos para comparar."""
    ultima = max(linhas, key=lambda l: l["data_avaliacao"])
    grupo = [ultimos[(i, ultima["teste"], None)] for i in ids_do_grupo if (i, ultima["teste"], None) in ultimos]
    return sum(grupo) / len(grupo) if len(grupo) >= minimo else None


def mudancas(comparacao: list[dict]) -> list[dict]:
    """O que mudou contra a avaliação anterior, do que mais melhorou para o que mais piorou."""
    itens = []
    for linha in comparacao:
        if linha["situacao"] not in MUDANCAS_MOSTRADAS or linha["variacao_pct"] is None or linha["maior_melhor"] is None:
            continue
        pct = float(linha["variacao_pct"])
        itens.append({
            "teste": _nome(linha),
            "ganho": pct if linha["maior_melhor"] else -pct,
            "situacao": {"melhorou": "Melhorou", "piorou": "Piorou", "estavel": "Estável"}[linha["situacao"]],
            "anterior": float(linha["valor_anterior"]), "atual": float(linha["valor_atual"]),
            "unidade": linha["unidade_medida"] or "", "confirmado": linha["confirmado"],
        })
    return sorted(itens, key=lambda i: -i["ganho"])


def tendencia(linhas: list[dict]) -> tuple[str, str] | None:
    """(texto, tipo) da primeira para a última avaliação de um teste sem lado. Tipo: melhora, queda ou neutro."""
    if len(linhas) < 2 or any(l["lado"] for l in linhas):
        return None
    ordenadas = sorted(linhas, key=lambda l: l["data_avaliacao"])
    inicial, final = float(ordenadas[0]["valor"]), float(ordenadas[-1]["valor"])
    if not inicial:
        if final == inicial:
            return "Estável desde a primeira", "neutro"
        if ordenadas[0]["maior_melhor"] is None:
            return None
        melhorou = (final > inicial) == ordenadas[0]["maior_melhor"]
        return f"{'Melhorou' if melhorou else 'Piorou'}: de {inicial:g} para {final:g}".replace(".", ","), "melhora" if melhorou else "queda"
    pct = (final - inicial) / abs(inicial) * 100
    maior_melhor = ordenadas[0]["maior_melhor"]
    if abs(pct) < 2:
        return "Estável desde a primeira", "neutro"
    if abs(inicial) < 5 and maior_melhor is not None:
        # Em número pequeno, o percentual engana: de 1 para 0 viraria 100%.
        melhorou = (final > inicial) == maior_melhor
        de_para = f"de {inicial:g} para {final:g}".replace(".", ",")
        return f"{'Melhorou' if melhorou else 'Piorou'}: {de_para}", "melhora" if melhorou else "queda"
    texto = f"{abs(pct):.1f}%".replace(".", ",")
    if maior_melhor is None:
        return f"{'Subiu' if pct > 0 else 'Desceu'} {texto} desde a primeira", "neutro"
    melhorou = (pct > 0) == maior_melhor
    return f"{'Melhorou' if melhorou else 'Piorou'} {texto} desde a primeira", "melhora" if melhorou else "queda"
