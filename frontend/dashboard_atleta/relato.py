"""Descrição de como vêm sendo os relatórios do atleta, escrita a partir dos dados.

Não há IA nem texto inventado: cada frase sai das views da API. O que a API não tem não aparece.
"""
from datetime import date
from html import escape


def _data(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%d/%m/%Y")


def _plural(n: int, um: str, varios: str) -> str:
    return f"{n} {um if n == 1 else varios}"


def _nome_do_teste(linha: dict) -> str:
    lados = {"dir": "direita", "esq": "esquerda"}
    lado = lados.get(linha["lado"])
    return f"{linha['teste_nome']}, {lado}" if lado else linha["teste_nome"]


def _num(valor) -> str:
    return f"{float(valor):.2f}".rstrip("0").rstrip(".").replace(".", ",")


def _variacao(linha: dict) -> str:
    """De quanto para quanto, porque só o percentual engana em números pequenos (de 1 para 0 é -100%)."""
    percentual = f"{float(linha['variacao_pct']):+.1f}%".replace(".", ",")
    return (f"de {_num(linha['valor_anterior'])} para {_num(linha['valor_atual'])} "
            f"{escape({'desequilibrios': 'desequilíbrios'}.get(linha['unidade_medida'], linha['unidade_medida'] or ''))} ({percentual})")


def _frase_das_avaliacoes(primeiro: str, evolucao: list[dict]) -> str:
    datas = sorted({l["data_avaliacao"] for l in evolucao})
    if not datas:
        return f"{primeiro} ainda não fez nenhuma avaliação física."
    if len(datas) == 1:
        return f"{primeiro} tem 1 avaliação, em {_data(datas[0])}. Ainda não há outra para comparar."
    return f"{primeiro} tem {len(datas)} avaliações, de {_data(datas[0])} a {_data(datas[-1])}."


def frase_da_comparacao(comparacao: list[dict]) -> str | None:
    contagem = {s: sum(l["situacao"] == s for l in comparacao) for s in ("melhorou", "piorou", "estavel")}
    if not any(contagem.values()):
        return None
    partes = [_plural(contagem["melhorou"], "teste melhorou", "testes melhoraram"),
              _plural(contagem["piorou"], "piorou", "pioraram"),
              _plural(contagem["estavel"], "ficou estável", "ficaram estáveis")]
    frase = f"Na comparação com a avaliação anterior, {partes[0]}, {partes[1]} e {partes[2]}."
    if contagem["melhorou"] > contagem["piorou"]:
        return f"{frase} O saldo é positivo."
    if contagem["piorou"] > contagem["melhorou"]:
        return f"{frase} O saldo é negativo."
    return f"{frase} O saldo fica equilibrado."


def _destaque(comparacao: list[dict], situacao: str) -> dict | None:
    """O teste com a maior variação nessa situação."""
    candidatos = [l for l in comparacao if l["situacao"] == situacao and l["variacao_pct"] is not None]
    return max(candidatos, key=lambda l: abs(float(l["variacao_pct"])), default=None)


def _frase_da_presenca(presenca: list[dict]) -> str:
    presentes = sum(l["status"] == "presente" for l in presenca)
    faltas = sum(l["status"] == "falta" for l in presenca)
    if not presentes and not faltas:
        return "Ainda não há chamada registrada."
    taxa = round(100 * presentes / (presentes + faltas))
    return (f"{_plural(presentes, 'presença', 'presenças')} e {_plural(faltas, 'falta', 'faltas')}, "
            f"ou {taxa}% de presença nas chamadas registradas.")


def _frase_dos_treinos(treinos: list[dict]) -> str:
    if not treinos:
        return "Nenhum relatório de treino registrado."
    return f"{_plural(len(treinos), 'relatório registrado', 'relatórios registrados')}, o último em {_data(treinos[-1]['data'])}."


def html_do_relato(atleta: dict, evolucao: list[dict], comparacao: list[dict], presenca: list[dict],
                   treinos: list[dict], perfil: list[dict] | None = None, reavaliacao: str | None = None) -> str:
    """Bloco da lateral. Tudo o que vem do banco passa pelo escape."""
    primeiro = escape((atleta["nome"] or "Atleta").split()[0])
    nome = f'<span class="cartao-nome">{primeiro}</span>'
    paragrafos = [_frase_das_avaliacoes(nome, evolucao)]
    if frase := frase_da_comparacao(comparacao):
        paragrafos.append(frase)

    itens = []
    if perfil:
        mais_forte, mais_fraco = perfil[0], perfil[-1]
        itens.append(("Mais forte hoje", f"{escape(mais_forte['teste'])}: {mais_forte['posicao']}º de {mais_forte['total']} colegas"))
        if len(perfil) > 1:
            itens.append(("Mais fraco hoje", f"{escape(mais_fraco['teste'])}: {mais_fraco['posicao']}º de {mais_fraco['total']} colegas"))
    if melhor := _destaque(comparacao, "melhorou"):
        itens.append(("Maior evolução", f"{escape(_nome_do_teste(melhor))}: {_variacao(melhor)}"))
    if pior := _destaque(comparacao, "piorou"):
        itens.append(("Maior queda", f"{escape(_nome_do_teste(pior))}: {_variacao(pior)}"))
    itens.append(("Frequência", _frase_da_presenca(presenca)))
    itens.append(("Relatórios de treino", _frase_dos_treinos(treinos)))
    if reavaliacao:
        itens.append(("Próxima reavaliação", escape(reavaliacao)))
    observadas = [t for t in treinos if t.get("observacoes")]
    if observadas:
        itens.append((f"Observação do treinador em {_data(observadas[-1]['data'])}", escape(observadas[-1]["observacoes"])))

    provisorio = any(not l["confirmado"] and l["situacao"] in ("melhorou", "piorou", "estavel") for l in comparacao)
    aviso = ("<p style='margin:12px 0 0;font-size:12px;line-height:1.45;color:#64748b'>Classificações provisórias: "
             "a PKZ ainda não confirmou as regras desses testes.</p>") if provisorio else ""
    corpo = "".join(f"<p style='margin:0 0 10px;font-size:clamp(14.5px,1vw,18px);line-height:1.45;color:#0f172a'>{p}</p>" for p in paragrafos)
    lista = "".join(
        "<div style='display:flex;flex:1;flex-direction:column;justify-content:center;max-height:104px;padding:clamp(8px,.7vw,13px) 0;border-top:1px solid #e8ebf4'>"
        f"<div style='font-size:clamp(10.5px,.75vw,12.5px);font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#4d6b0f'>{rotulo}</div>"
        f"<div style='margin-top:3px;font-size:clamp(14px,.95vw,17px);line-height:1.4;color:#0f172a;overflow-wrap:anywhere'>{texto}</div></div>"
        for rotulo, texto in itens
    )
    return ("<div style='display:flex;flex-direction:column;height:100%;min-width:0;border:1px solid #dbe0f0;border-radius:14px;background:#fff;padding:clamp(15px,1.2vw,22px) clamp(16px,1.3vw,24px)'>"
            "<div style='margin-bottom:9px;font-size:clamp(18px,1.3vw,23px);font-weight:800;letter-spacing:-.01em;color:#12228e'>Como vêm sendo os relatórios</div>"
            f"<div>{corpo}</div><div style='display:flex;flex:1;flex-direction:column'>{lista}</div>{aviso}</div>")
