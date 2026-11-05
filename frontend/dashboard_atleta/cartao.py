"""Cartão do atleta, no mesmo desenho do painel comparativo.

A API ainda não entrega nota, nível nem metal. A nota aqui é PROVISÓRIA e os atributos de cada
modalidade vêm de ../catalogo_atributos.json, explicado em ../CATALOGO_ATRIBUTOS.md.

Cada atleta usa os atributos da própria modalidade; sem modalidade no catálogo, usa os atributos
gerais. A comparação é sempre com os atletas da mesma faixa de idade. Todo atleta da modalidade
mostra os mesmos atributos: quem não tem dado num deles recebe um aviso, nunca um número inventado.
"""
import json
import math
import unicodedata
from html import escape
from pathlib import Path

CATALOGO = json.loads((Path(__file__).resolve().parent.parent / "catalogo_atributos.json").read_text(encoding="utf-8"))
REGRAS = CATALOGO["regras"]
MODALIDADES_PKZ = list(CATALOGO["modalidades"]["PKZ"])
GRUPOS_DE_TESTES = CATALOGO["grupos_de_testes"]

ESTILO_NIVEL = {
    "A": ("linear-gradient(145deg,#2c2f38,#0b0c10)", "#e8c96a"),
    "B": ("linear-gradient(145deg,#e8c96a,#bd9426)", "#3d2f05"),
    "C": ("linear-gradient(145deg,#c8ced6,#8d97a3)", "#2b3138"),
    "D": ("linear-gradient(145deg,#d8a97c,#a06a3a)", "#3a1f0b"),
    "E": ("linear-gradient(145deg,#d8a97c,#a06a3a)", "#3a1f0b"),
}
MEDALHAS = {
    1: ("linear-gradient(145deg,#e8c96a,#bd9426)", "#3d2f05"),
    2: ("linear-gradient(145deg,#c8ced6,#8d97a3)", "#2b3138"),
    3: ("linear-gradient(145deg,#d8a97c,#a06a3a)", "#3a1f0b"),
}
ESTILO_MEDIA = {
    "acima": ("#dcf3e2", "#0d5132", "acima da média do grupo"),
    "média": ("#f1f4f9", "#475569", "na média do grupo"),
    "abaixo": ("#fdeccb", "#7a4708", "abaixo da média do grupo"),
}
SEM_TESTE, POUCOS_COLEGAS = "sem_teste", "poucos_colegas"


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn").strip().lower()


_NOMES_DE_MODALIDADE = {_sem_acento(m): m for m in MODALIDADES_PKZ} | {"futebol": "Futebol de campo"}


def nome_da_modalidade(texto: str | None) -> str | None:
    """Junta quem escreveu "volei" ou "VÔLEI" na mesma modalidade do catálogo."""
    if not texto or not texto.strip():
        return None
    return _NOMES_DE_MODALIDADE.get(_sem_acento(texto), texto.strip().capitalize())


def _arredondar(valor: float) -> int:
    """Meio para cima, como o Math.round do painel. O round do Python daria outra nota em 50,5."""
    return math.floor(valor + 0.5)


def faixa_de_idade(idade: int | None) -> str:
    if idade is None:
        return "Todas as idades"
    for faixa in CATALOGO["faixas_de_idade"]:
        if faixa["ate"] is None or idade <= faixa["ate"]:
            return faixa["nome"]
    return "Todas as idades"


def nivel_da_nota(nota: int) -> tuple[str, str]:
    for regra in REGRAS["niveis"]:
        if nota <= regra["ate"]:
            return regra["nivel"], regra["metal"]
    return "A", "Preto"


def ultimos_valores(medidas: list[dict]) -> dict:
    """{(atleta, teste, lado): último valor}."""
    return {(l["atleta_id"], l["teste"], l["lado"]): float(l["valor"])
            for l in sorted(medidas, key=lambda l: l["data_avaliacao"])}


def percentil(valor: float, grupo: list[float], maior_melhor: bool) -> int:
    abaixo = sum((v < valor) if maior_melhor else (v > valor) for v in grupo)
    iguais = sum(v == valor for v in grupo)
    return _arredondar(99 * (abaixo + 0.5 * iguais) / len(grupo))


def _simetria(ultimos: dict, atleta_id: str, teste: str) -> int | None:
    direita = ultimos.get((atleta_id, teste, "dir"))
    esquerda = ultimos.get((atleta_id, teste, "esq"))
    if not direita or not esquerda:
        return None
    return _arredondar(100 * min(direita, esquerda) / max(direita, esquerda))


def _motivo_da_falta(d: dict, atleta_id: str, ultimos: dict) -> str:
    """Por que o atributo está vazio: o atleta não fez o teste, ou há poucos colegas para comparar."""
    fez = d["tipo"] == "percentil" and (atleta_id, d["teste"], None) in ultimos
    return POUCOS_COLEGAS if fez else SEM_TESTE


def calcular_cartoes(atletas: list[dict], medidas: list[dict], modalidade: str | None) -> dict[str, dict]:
    """{atleta_id: cartão} de todos os atletas, nos atributos da modalidade (ou nos gerais, se ela não está no catálogo)."""
    definicoes = CATALOGO["modalidades"]["PKZ"].get(modalidade) or CATALOGO["modalidades"]["GERAL"]
    rotulo = modalidade if modalidade in MODALIDADES_PKZ else f"{modalidade or 'Modalidade não informada'} · atributos gerais"
    ultimos = ultimos_valores(medidas)
    grupos: dict[str, list[str]] = {}
    for atleta in atletas:
        grupos.setdefault(faixa_de_idade(atleta["idade"]), []).append(atleta["atleta_id"])

    cartoes = {}
    for nome_do_grupo, ids in grupos.items():
        valores_por_sigla = {}
        for d in definicoes:
            if d["tipo"] == "percentil":
                valores = {i: ultimos[(i, d["teste"], None)] for i in ids if (i, d["teste"], None) in ultimos}
                lista = list(valores.values())
                valores_por_sigla[d["sigla"]] = (
                    {i: percentil(v, lista, d["maior_melhor"]) for i, v in valores.items()}
                    if len(lista) >= REGRAS["minimo_no_grupo"] else {}
                )
            elif d["tipo"] == "simetria":
                valores_por_sigla[d["sigla"]] = {i: s for i in ids if (s := _simetria(ultimos, i, d["teste"])) is not None}
            else:
                valores_por_sigla[d["sigla"]] = {}

        do_grupo = {}
        for atleta_id in ids:
            atributos = {d["sigla"]: valores_por_sigla[d["sigla"]].get(atleta_id) for d in definicoes}
            capacidades = [atributos[d["sigla"]] for d in definicoes
                           if d["tipo"] != "simetria" and atributos[d["sigla"]] is not None]
            nota = (_arredondar(sum(capacidades) / len(capacidades))
                    if len(capacidades) >= REGRAS["minimo_de_atributos_para_nota"] else None)
            nivel, metal = nivel_da_nota(nota) if nota is not None else (None, None)
            faltas = [{"nome": d["nome"], "motivo": _motivo_da_falta(d, atleta_id, ultimos)}
                      for d in definicoes if atributos[d["sigla"]] is None]
            do_grupo[atleta_id] = {"grupo": nome_do_grupo, "modalidade": rotulo, "definicoes": definicoes,
                                   "atributos": atributos, "nota": nota, "nivel": nivel, "metal": metal, "faltas": faltas}

        medias = {}
        for d in definicoes:
            valores = [c["atributos"][d["sigla"]] for c in do_grupo.values() if c["atributos"][d["sigla"]] is not None]
            medias[d["sigla"]] = sum(valores) / len(valores) if valores else None
        notas = [c["nota"] for c in do_grupo.values() if c["nota"] is not None]
        for cartao in do_grupo.values():
            cartao["medias"] = medias
            cartao["media_das_notas"] = sum(notas) / len(notas) if notas else None
            cartao["no_grupo"] = len(notas)
            # Quem empata na nota divide a posição, igual ao painel.
            cartao["posicao"] = 1 + sum(n > cartao["nota"] for n in notas) if cartao["nota"] is not None else None
        cartoes.update(do_grupo)
    return cartoes


def _em_relacao(valor, media) -> str | None:
    if valor is None or media is None:
        return None
    if valor > media + REGRAS["faixa_da_media"]:
        return "acima"
    return "abaixo" if valor < media - REGRAS["faixa_da_media"] else "média"


def _lista(nomes: list[str]) -> str:
    return nomes[0] if len(nomes) == 1 else f"{', '.join(nomes[:-1])} e {nomes[-1]}"


def aviso_de_dados(atleta: dict, cartao: dict) -> str:
    """O que falta no cartão, em palavras. Vazio quando está tudo preenchido."""
    if not atleta["total_avaliacoes"]:
        return "Atleta novo: os atributos e a nota aparecem depois da primeira avaliação."
    frases = []
    sem_teste = [f["nome"] for f in cartao["faltas"] if f["motivo"] == SEM_TESTE]
    poucos = [f["nome"] for f in cartao["faltas"] if f["motivo"] == POUCOS_COLEGAS]
    if sem_teste:
        frases.append(f"Sem dados em {_lista(sem_teste)}: o atleta ainda não fez esse teste." if len(sem_teste) == 1
                      else f"Sem dados em {_lista(sem_teste)}: o atleta ainda não fez esses testes.")
    if poucos:
        frases.append(f"{_lista(poucos)}: poucos colegas com esse teste para comparar.")
    if cartao["nota"] is None:
        frases.append(f"A nota aparece com pelo menos {REGRAS['minimo_de_atributos_para_nota']} atributos preenchidos.")
    return " ".join(frases)


def _atributo(d: dict, valor) -> str:
    alerta = d["tipo"] == "simetria" and valor is not None and valor < REGRAS["simetria_minima"]
    dica = escape(d["nome"] + (" (aproximado: " + d["falta"] + ")" if d.get("aproximado") else ""))
    marca = '<span style="color:#4d6b0f">*</span>' if d.get("aproximado") else ""
    numero = ('<div style="display:grid;place-items:center;height:clamp(32px,11cqi,58px);font-size:clamp(12px,3.2cqi,15px);font-weight:600;color:#7a4708">sem dado</div>'
              if valor is None else
              f'<div style="font-size:clamp(30px,10.5cqi,56px);font-weight:800;line-height:1.1;color:{"#be123c" if alerta else "#12228e"}">{valor}</div>')
    fundo = "background:#fdf6e6;border:1px dashed #e6c98a" if valor is None else "background:#f7f8fd;border:1px solid transparent"
    return (f'<div title="{dica}" style="display:flex;flex-direction:column;justify-content:center;min-width:0;padding:clamp(7px,2cqi,12px) 4px;border-radius:12px;text-align:center;{fundo}">'
            f'<div style="font-size:clamp(12px,3.3cqi,16px);font-weight:700;letter-spacing:.03em;color:#475569">{d["sigla"]}{marca}</div>'
            f"{numero}"
            f'<div style="font-size:clamp(11px,2.9cqi,14px);line-height:1.2;color:#64748b">{escape(d["nome"])}</div></div>')


def html_do_cartao(atleta: dict, cartao: dict) -> str:
    """O tamanho de tudo acompanha a largura do próprio cartão. O que vem do banco passa pelo escape."""
    nota, nivel = cartao["nota"], cartao["nivel"]
    numero = "—" if nota is None else nota
    fundo_nivel, tinta_nivel = ESTILO_NIVEL.get(nivel, ("rgba(255,255,255,.14)", "#ffffff"))
    categoria = (atleta["categoria"] or "Sem categoria").replace("_", " ").capitalize()
    idade = f" · {atleta['idade']} anos" if atleta["idade"] is not None else ""

    posicao = cartao["posicao"]
    fundo_pos, tinta_pos = MEDALHAS.get(posicao, ("#f3f5fd", "#12228e"))
    pilula = (f'<span title="Posição entre {escape(cartao["grupo"].lower())}" style="display:inline-grid;place-items:center;flex-shrink:0;'
              f"min-width:34px;height:28px;padding:0 7px;border-radius:8px;background:{fundo_pos};color:{tinta_pos};"
              f'font-size:13px;font-weight:800">{posicao}º</span>') if posicao else ""
    atributos = "".join(_atributo(d, cartao["atributos"][d["sigla"]]) for d in cartao["definicoes"])

    relacao = _em_relacao(nota, cartao["media_das_notas"])
    selo = ""
    if relacao:
        fundo_selo, tinta_selo, texto_selo = ESTILO_MEDIA[relacao]
        selo = (f'<span style="display:inline-block;margin-top:7px;padding:3px 9px;border-radius:7px;background:{fundo_selo};color:{tinta_selo};'
                f'font-size:clamp(12px,3cqi,14px);font-weight:700">{texto_selo}</span>')
    texto_aviso = aviso_de_dados(atleta, cartao)
    aviso = (f'<div style="margin:0 clamp(12px,3.4cqi,20px) clamp(12px,3.4cqi,20px);padding:9px 12px;border-radius:10px;background:#fdf3dc;'
             f'color:#7a4708;font-size:clamp(12.5px,3.1cqi,14.5px);line-height:1.4;font-weight:500">{escape(texto_aviso)}</div>') if texto_aviso else ""
    nota_aprox = (f'<div style="padding:0 clamp(14px,3.8cqi,22px) clamp(10px,2.6cqi,14px);font-size:clamp(11px,2.7cqi,12.5px);color:#64748b">'
                  "* teste aproximado: é o mais próximo que a bateria tem.</div>") if any(
        d.get("aproximado") for d in cartao["definicoes"]) else ""

    return f"""
<div style="container-type:inline-size;height:100%">
  <div style="display:flex;flex-direction:column;height:100%;border:1px solid #12228e;border-radius:16px;overflow:hidden;background:#fff;box-shadow:0 8px 22px rgba(18,34,142,.12)">
    <div style="display:flex;align-items:center;justify-content:space-between;gap:3cqi;padding:clamp(14px,4.4cqi,26px);background:radial-gradient(circle at 50% 122%,transparent 0 54px,rgba(255,255,255,.13) 54px 56px,transparent 56px),linear-gradient(90deg,transparent 0 49.2%,rgba(255,255,255,.13) 49.2% 50.6%,transparent 50.6%),linear-gradient(160deg,#1b30b4,#0e1a6b)">
      <div style="display:flex;align-items:center;gap:clamp(10px,3.6cqi,22px);flex:1;min-width:0">
        <div style="display:grid;place-items:center;width:clamp(72px,23cqi,132px);height:clamp(72px,23cqi,132px);flex-shrink:0;border-radius:50%;background:#dbe0f0;box-shadow:0 0 0 3px #c2f24a;color:#6b7590;font-size:clamp(11px,3cqi,14px);font-weight:600">Foto</div>
        <div style="min-width:0">
          <div style="font-size:clamp(44px,17cqi,88px);font-weight:800;line-height:1;color:#fff">{numero}</div>
          <div style="margin-top:4px;font-size:clamp(9px,2.5cqi,13px);font-weight:700;letter-spacing:.08em;text-transform:uppercase;white-space:nowrap;color:#c2f24a">Nota provisória</div>
        </div>
      </div>
      <div style="display:flex;flex-direction:column;align-items:center;gap:4px;flex-shrink:0">
        <div style="display:grid;place-items:center;width:clamp(44px,14cqi,76px);height:clamp(44px,14cqi,76px);border-radius:clamp(11px,3cqi,18px);background:{fundo_nivel};color:{tinta_nivel};font-size:clamp(22px,7.4cqi,40px);font-weight:800">{nivel or "—"}</div>
        <div style="font-size:clamp(9px,2.3cqi,12.5px);font-weight:700;letter-spacing:.08em;text-transform:uppercase;white-space:nowrap;color:#c2f24a">{cartao["metal"] or "Sem nível"}</div>
      </div>
    </div>
    <div style="padding:clamp(11px,3.2cqi,18px) clamp(14px,3.8cqi,22px) clamp(10px,2.6cqi,14px)">
      <div style="display:flex;align-items:center;gap:9px;font-size:clamp(17px,4.8cqi,25px);font-weight:700;line-height:1.2;color:#0f172a">{pilula}<span class="cartao-nome" style="min-width:0">{escape(atleta["nome"])}</span></div>
      <div style="margin-top:5px;font-size:clamp(13px,3.3cqi,16px);color:#475569">{escape(categoria)}{idade} · {escape(cartao["modalidade"])}</div>
      <div style="margin-top:1px;font-size:clamp(12px,2.9cqi,14px);color:#64748b">Comparado com {escape(cartao["grupo"].lower())}</div>
      {selo}
    </div>
    <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));grid-auto-rows:1fr;gap:clamp(6px,1.8cqi,10px);flex:1;padding:0 clamp(12px,3.4cqi,20px) clamp(12px,3.4cqi,20px)">{atributos}</div>
    {nota_aprox}
    {aviso}
  </div>
</div>"""
