"""Painel comparativo: o grupo inteiro, lado a lado, no mesmo app do dashboard do atleta.

Usa o mesmo cartão, o mesmo catálogo e a mesma nota provisória. Cada atleta é visto nos atributos
da própria modalidade; para comparar por um atributo, escolhe-se uma modalidade. Tudo o que vem do
banco passa pelo escape. Aqui só se monta HTML: os filtros ficam no app.py.
"""
from datetime import datetime, timedelta, timezone
from html import escape

import cartao
import graficos

NOTA = "nota"
PKZ, ONE_TO_ONE = "PKZ", "One to One"
FAIXA = cartao.REGRAS["faixa_da_media"]
ESTADOS = {
    "acima": ("#dcf3e2", "#0d5132", "acima da média"),
    "media": ("#f1f4f9", "#475569", "na média"),
    "abaixo": ("#fdeccb", "#7a4708", "abaixo da média"),
    "sem": ("#f8fafc", "#94a3b8", "sem dado"),
}
CSS = """
  .grade-cartoes { display:grid; grid-template-columns:repeat(auto-fill,minmax(min(300px,100%),1fr)); gap:14px; align-items:stretch; }
  .cmp-rodape { display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:6px 10px; margin:0 clamp(12px,3.4cqi,20px); padding:10px 0 12px; border-top:1px solid #eef1f6; font-size:13px; color:#0f172a; }
  .cmp-rodape small { display:block; width:100%; font-size:12.5px; color:#475569; }
  .titulo-lista { display:flex; flex-wrap:wrap; align-items:baseline; justify-content:space-between; gap:4px 14px; margin-top:4px; }
  .ranking { overflow:hidden; border:1px solid #dbe0f0; border-radius:14px; background:#fff; }
  .ranking-linha { display:grid; grid-template-columns:44px minmax(0,1fr) auto; align-items:center; gap:14px; padding:10px 16px; border-top:1px solid #eef1f6; }
  .ranking-linha:first-child { border-top:0; }
  .ranking-pos { display:grid; place-items:center; width:38px; height:38px; border-radius:10px; font-size:14.5px; font-weight:800; }
  .trilho { position:relative; display:block; height:10px; border-radius:5px; background:#eef1f6; }
  .trilho > i { position:absolute; left:0; top:0; bottom:0; border-radius:5px; }
  .trilho > b { position:absolute; top:-4px; bottom:-4px; width:2px; background:#0f172a; }
  .niveis { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:clamp(6px,.6vw,12px); }
  .nivel-caixa { position:relative; display:flex; align-items:flex-end; overflow:hidden; height:clamp(58px,4vw,76px); border-radius:10px; background:#f3f5fd; }
  .nivel-caixa > span { position:absolute; inset:0; display:grid; place-items:center; font-size:clamp(20px,1.6vw,28px); font-weight:800; color:#0f172a; text-shadow:0 0 6px #fff,0 0 2px #fff; }
  .resumo-dia { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:8px; }
  .resumo-dia > div { padding:9px 11px; border-radius:10px; background:#f3f5fd; }
  .resumo-dia b { display:block; font-size:clamp(22px,1.8vw,32px); font-weight:800; line-height:1.05; }
  .resumo-dia span { font-size:12.5px; color:#475569; }
  .cmp-atributos { display:grid; grid-template-columns:repeat(auto-fit,minmax(min(280px,100%),1fr)); gap:10px 26px; }
  .cmp-atributo { display:flex; flex-direction:column; gap:6px; padding:9px 0; border-top:1px solid #eef1f6; }
  @media (max-width:640px) { .resumo-dia { grid-template-columns:repeat(2,minmax(0,1fr)); } .niveis { gap:4px; } }
"""


# ---------------------------------------------------------------- contas
def hoje_em_sao_paulo() -> str:
    """O Brasil não tem horário de verão desde 2019: São Paulo é sempre UTC-3."""
    return (datetime.now(timezone.utc) - timedelta(hours=3)).date().isoformat()


def valor(c: dict, chave: str):
    return c["nota"] if chave == NOTA else c["atributos"].get(chave)


def media(cartoes: list[dict], chave: str) -> float | None:
    valores = [v for c in cartoes if (v := valor(c, chave)) is not None]
    return sum(valores) / len(valores) if valores else None


def estado(v, m) -> str:
    if v is None or m is None:
        return "sem"
    return "acima" if v - m > FAIXA else "abaixo" if m - v > FAIXA else "media"


def ordenar(atletas: list[dict], cartoes: dict, chave: str) -> list[tuple[dict, int | None]]:
    """Do maior para o menor; sem dado no fim. Quem empata no valor arredondado divide a posição, igual ao painel."""
    def ordem(a):
        v = valor(cartoes[a["atleta_id"]], chave)
        return (v is None, -(v or 0), a["nome"] or "")
    saida, anterior, posicao_anterior = [], None, 0
    for i, a in enumerate(sorted(atletas, key=ordem), start=1):
        v = valor(cartoes[a["atleta_id"]], chave)
        if v is None:
            saida.append((a, None))
            continue
        arredondado = cartao._arredondar(v)
        posicao = posicao_anterior if arredondado == anterior else i
        anterior, posicao_anterior = arredondado, posicao
        saida.append((a, posicao))
    return saida


def frequencia(presencas: list[dict]) -> str:
    presentes = sum(p["status"] == "presente" for p in presencas)
    faltas = sum(p["status"] == "falta" for p in presencas)
    if not presentes + faltas:
        return "Sem chamada registrada"
    total = presentes + faltas
    return f"{round(100 * presentes / total)}% de presença em {total} {'chamada' if total == 1 else 'chamadas'}"


def sessao_de_hoje(presencas: list[dict], hoje: str) -> str:
    de_hoje = next((p for p in presencas if p["data"] == hoje and p["status"] != "cancelado"), None)
    if not de_hoje:
        return "Sem sessão hoje"
    situacao = {"presente": "presença registrada", "falta": "falta registrada"}.get(de_hoje["status"], "aguardando chamada")
    return f"Hoje, {(de_hoje.get('hora_inicio') or '')[:5]} · {situacao}"


# ---------------------------------------------------------------- blocos
def heroi(nome_da_chave: str, atletas: list[dict], cartoes: dict, chave: str, area: str) -> str:
    lista = [cartoes[a["atleta_id"]] for a in atletas]
    m = media(lista, chave)
    contagem = {k: 0 for k in ESTADOS}
    for c in lista:
        contagem[estado(valor(c, chave), m)] += 1
    n = len(lista)
    if not n:
        frase = "Nenhum atleta com esses filtros."
    elif contagem["sem"] == n:
        frase = (f"Os {n} alunos do One to One ainda não têm avaliações físicas na API, por isso não há nota nem atributos."
                 if area == ONE_TO_ONE else f"Ainda não há dados de {nome_da_chave.lower()} para este recorte.")
    else:
        frase = (f"{contagem['acima']} {'atleta está' if contagem['acima'] == 1 else 'atletas estão'} acima da média em "
                 f"{nome_da_chave.lower()}, {contagem['media']} na média e {contagem['abaixo']} abaixo."
                 + (f" {contagem['sem']} sem dado." if contagem["sem"] else ""))
    fmt = "—" if m is None else cartao._arredondar(m)
    tiles = [graficos.tile(fmt, "Média do grupo", escape(nome_da_chave.lower())),
             graficos.tile(contagem["acima"], "Acima da média", f"mais de {FAIXA} pontos acima", "#c2f24a"),
             graficos.tile(contagem["media"], "Na média", f"até {FAIXA} pontos de diferença"),
             graficos.tile(contagem["abaixo"], "Abaixo da média", f"mais de {FAIXA} pontos abaixo", "#f5c77e")]
    return graficos.heroi(f"Comparar por {escape(nome_da_chave.lower())}", escape(frase), tiles)


def resumo_do_dia(atletas: list[dict], presencas_por_atleta: dict, hoje: str) -> str:
    de_hoje = [p for a in atletas for p in presencas_por_atleta.get(a["atleta_id"], []) if p["data"] == hoje and p["status"] != "cancelado"]
    presentes = sum(p["status"] == "presente" for p in de_hoje)
    faltas = sum(p["status"] == "falta" for p in de_hoje)
    itens = [(len(de_hoje), "sessões hoje", "#12228e"), (presentes, "presentes", "#4d6b0f"),
             (faltas, "falta" if faltas == 1 else "faltas", "#be123c"), (len(de_hoje) - presentes - faltas, "aguardando chamada", "#64748b")]
    data = datetime.fromisoformat(hoje).strftime("%d/%m/%Y")
    return ('<div class="painel">' + graficos.titulo_de_painel("Resumo do dia", f"{data} · chamada registrada no sistema, só leitura")
            + '<div class="resumo-dia">' + "".join(f'<div><b style="color:{cor}">{v}</b><span>{r}</span></div>' for v, r, cor in itens)
            + "</div></div>")


def distribuicao(atletas: list[dict], cartoes: dict) -> str:
    notas = [c["nota"] for a in atletas if (c := cartoes[a["atleta_id"]])["nota"] is not None]
    if not notas:
        return ('<div class="painel">' + graficos.titulo_de_painel("Como a turma se distribui por nível")
                + graficos.aviso("Sem dados para a distribuição.", "Nenhum atleta deste recorte tem nota provisória.") + "</div>")
    contagem = {}
    for nota in notas:
        nivel, _ = cartao.nivel_da_nota(cartao._arredondar(nota))
        contagem[nivel] = contagem.get(nivel, 0) + 1
    maior = max(contagem.values())
    caixas = ""
    for regra in reversed(cartao.REGRAS["niveis"]):
        qtd = contagem.get(regra["nivel"], 0)
        fundo, _ = cartao.ESTILO_NIVEL[regra["nivel"]]
        altura = max(8, round(100 * qtd / maior)) if qtd else 0
        caixas += (f'<div title="Nível {regra["nivel"]}: {qtd} {"atleta" if qtd == 1 else "atletas"}">'
                   f'<div class="nivel-caixa"><i style="display:block;width:100%;height:{altura}%;background:{fundo}"></i><span>{qtd}</span></div>'
                   f'<div style="margin-top:5px;text-align:center;font-size:13.5px;font-weight:700;color:#0f172a">{regra["nivel"]}'
                   f'<span style="font-weight:500;color:#64748b"> · {regra["metal"].lower()}</span></div></div>')
    return ('<div class="painel">' + graficos.titulo_de_painel("Como a turma se distribui por nível", f"{len(notas)} {'atleta' if len(notas) == 1 else 'atletas'} com nota provisória")
            + f'<div class="niveis">{caixas}</div></div>')


def _rodape_do_cartao(v, m, nome_da_chave: str, presencas: list[dict], hoje: str) -> str:
    fundo, tinta, texto = ESTADOS[estado(v, m)]
    numero = "" if v is None else f"{cartao._arredondar(v)} · "
    return (f'<div class="cmp-rodape"><span>{escape(nome_da_chave)}</span>'
            f'<span class="selo" style="background:{fundo};color:{tinta}">{numero}{texto}</span>'
            f'<small>{escape(sessao_de_hoje(presencas, hoje))} · {escape(frequencia(presencas))}</small></div>')


def grade_de_cartoes(ordenados, cartoes: dict, chave: str, nome_da_chave: str, presencas_por_atleta: dict, hoje: str) -> str:
    m = media([cartoes[a["atleta_id"]] for a, _ in ordenados], chave)
    return '<div class="grade-cartoes">' + "".join(
        cartao.html_do_cartao(a, {**cartoes[a["atleta_id"]], "posicao": pos, "titulo_da_posicao": f"Posição na lista, em {nome_da_chave.lower()}"},
                              _rodape_do_cartao(valor(cartoes[a["atleta_id"]], chave), m, nome_da_chave,
                                                presencas_por_atleta.get(a["atleta_id"], []), hoje))
        for a, pos in ordenados) + "</div>"


def ranking(ordenados, cartoes: dict, chave: str, nome_da_chave: str) -> str:
    m = media([cartoes[a["atleta_id"]] for a, _ in ordenados], chave)
    linhas = ""
    for a, pos in ordenados:
        c = cartoes[a["atleta_id"]]
        v = valor(c, chave)
        fundo_pos, tinta_pos = cartao.MEDALHAS.get(pos, ("#f3f5fd", "#12228e"))
        fundo, tinta, texto = ESTADOS[estado(v, m)]
        largura = 0 if v is None else max(2, min(100, v / 99 * 100))
        media_em = 0 if m is None else min(100, m / 99 * 100)
        linhas += (f'<div class="ranking-linha"><span class="ranking-pos" style="background:{fundo_pos};color:{tinta_pos}">{f"{pos}º" if pos else "—"}</span>'
                   f'<span style="display:flex;flex-direction:column;gap:6px;min-width:0"><span style="display:flex;flex-wrap:wrap;align-items:baseline;gap:2px 9px">'
                   f'<span class="cartao-nome" style="font-size:15px;font-weight:600;color:#0f172a">{escape(a["nome"] or "Sem nome")}</span>'
                   f'<span style="font-size:12.5px;color:#64748b">{escape(c["modalidade"])} · nível {c["nivel"] or "—"}</span></span>'
                   f'<span class="trilho"><i style="width:{largura:.1f}%;background:{"#c2a33a" if pos and pos <= 3 else "#2343c8"}"></i>'
                   f'{f"<b title=&quot;média do grupo&quot; style=&quot;left:{media_em:.1f}%&quot;></b>" if m is not None else ""}</span></span>'
                   f'<span style="display:flex;flex-direction:column;align-items:flex-end;gap:4px">'
                   f'<span style="font-size:22px;font-weight:800;line-height:1;color:#0f172a">{"—" if v is None else cartao._arredondar(v)}</span>'
                   f'<span class="selo" style="background:{fundo};color:{tinta}">{texto}</span></span></div>')
    return (f'<div class="ranking">{linhas}</div><div class="tst-rodape" style="margin-top:8px">'
            f"O risco escuro em cada barra é a média do grupo filtrado em {escape(nome_da_chave.lower())}.</div>")


def comparacao(a: dict, b: dict, ca: dict, cb: dict, todos_os_cartoes: list[dict]) -> str:
    """Dois atletas, atributo por atributo, com a média do grupo marcada em cada barra."""
    primeiro = lambda atleta: escape((atleta["nome"] or "Atleta").split()[0])
    mesmos = [d["sigla"] for d in ca["definicoes"]] == [d["sigla"] for d in cb["definicoes"]]
    linhas_def = [(d["nome"], d["sigla"]) for d in ca["definicoes"]] if mesmos else []
    linhas_def = [("Nota provisória", NOTA)] + linhas_def
    blocos, frente_a, frente_b = "", 0, 0
    for nome, chave in linhas_def:
        va, vb = valor(ca, chave), valor(cb, chave)
        m = media(todos_os_cartoes, chave)
        if va is not None and vb is not None and chave != NOTA:
            frente_a += va > vb
            frente_b += vb > va
        if va is None or vb is None:
            diferenca, cor = "sem dado", "#94a3b8"
        elif va == vb:
            diferenca, cor = "iguais", "#64748b"
        else:
            diferenca = f"{primeiro(a) if va > vb else primeiro(b)} +{abs(cartao._arredondar(va) - cartao._arredondar(vb))}"
            cor = "#2343c8" if va > vb else "#2e9e5b"

        def barra(v, cor_barra):
            largura = 0 if v is None else max(2, min(100, v / 99 * 100))
            marca = "" if m is None else f'<b style="left:{min(100, m / 99 * 100):.1f}%"></b>'
            return (f'<div style="display:flex;align-items:center;gap:9px"><span class="trilho" style="flex:1"><i style="width:{largura:.1f}%;background:{cor_barra}"></i>{marca}</span>'
                    f'<span style="width:34px;text-align:right;font-size:14px;font-weight:800;color:#0f172a">{"—" if v is None else cartao._arredondar(v)}</span></div>')
        blocos += (f'<div class="cmp-atributo"><div style="display:flex;justify-content:space-between;gap:8px">'
                   f'<span style="font-size:14px;font-weight:600;color:#0f172a">{escape(nome)}</span>'
                   f'<span style="font-size:13px;font-weight:700;color:{cor}">{diferenca}</span></div>{barra(va, "#2343c8")}{barra(vb, "#2e9e5b")}</div>')
    legenda = (f'<div class="gr-legenda" style="font-size:13.5px"><span><i style="background:#2343c8"></i><span class="cartao-nome">{escape(a["nome"])}</span></span>'
               f'<span><i style="background:#2e9e5b"></i><span class="cartao-nome">{escape(b["nome"])}</span></span>'
               '<span><i style="background:#0f172a;width:2px;height:12px"></i>média do grupo</span></div>')
    if mesmos:
        resumo = (f"{primeiro(a)} está à frente em {frente_a} de {len(linhas_def) - 1} atributos e {primeiro(b)} em {frente_b}. "
                  f"Na nota provisória: {'—' if ca['nota'] is None else ca['nota']} contra {'—' if cb['nota'] is None else cb['nota']}.")
    else:
        resumo = "Os dois são de modalidades com atributos diferentes, então a comparação fica na nota provisória."
    return ('<div class="painel">' + graficos.titulo_de_painel("Comparação entre dois atletas", "Atributo por atributo, com a média do grupo marcada em cada barra.")
            + legenda + f'<div class="cmp-atributos">{blocos}</div><div class="tst-rodape">{resumo}</div></div>')
