"""De onde vêm os dados do contrato: API (Supabase), CSVs e a ficha de matrícula.

Tudo termina no mesmo contrato (contrato.py). Nada aqui calcula indicador: só lê e organiza.

Credenciais da API, nesta ordem:
1. variáveis de ambiente já definidas;
2. o arquivo indicado em --env (ou PKZ_ENV_FILE);
3. backend/.env e frontend/dashboard_atleta/.env do repositório.
Aceita a chave de serviço (SUPABASE_SECRET_KEY) ou o login de teste do dashboard
(SUPABASE_PUBLISHABLE_KEY + API_TESTE_EMAIL + API_TESTE_SENHA). As credenciais nunca vão para o contrato.
"""
import csv
import json
import os
from datetime import date, datetime
from pathlib import Path

import requests
from dotenv import dotenv_values

from . import contrato as C

RAIZ = Path(__file__).resolve().parents[2]
CATALOGO = RAIZ / "frontend" / "catalogo_atributos.json"
LIMITE = 1000
TEMPO = 30
# Colunas da ficha de matrícula que o relatório usa. As demais (CPF, endereço, telefone, e-mail,
# responsável) são descartadas na leitura e nunca chegam ao contrato.
COLUNAS_FICHA = {"nome": "nome completo aluno", "nascimento": "data de nascimento", "modalidade": "esporte/modalidade",
                 "clube": "clube/ escolinha", "turno": "turno escolar"}


# ---------------------------------------------------------------- API
class Api:
    def __init__(self, arquivo_env=None):
        valores = {}
        candidatos = [arquivo_env or os.environ.get("PKZ_ENV_FILE"), RAIZ / "backend" / ".env",
                      RAIZ / "frontend" / "dashboard_atleta" / ".env"]
        for caminho in candidatos:
            if caminho and Path(caminho).exists():
                valores = {**dotenv_values(caminho), **valores}
        def ler(nome):
            return os.environ.get(nome) or valores.get(nome)
        self.url = (ler("SUPABASE_URL") or "").rstrip("/")
        self.secreta = ler("SUPABASE_SECRET_KEY")
        self.publica = ler("SUPABASE_PUBLISHABLE_KEY")
        self.email, self.senha = ler("API_TESTE_EMAIL"), ler("API_TESTE_SENHA")
        if not self.url or not (self.secreta or (self.publica and self.email and self.senha)):
            raise RuntimeError("Credenciais da API não encontradas. Informe --env com o arquivo .env do backend ou do dashboard.")
        self._token = None

    def _cabecalhos(self):
        if self.secreta:
            return {"apikey": self.secreta, "Authorization": f"Bearer {self.secreta}", "Accept-Profile": "api"}
        if not self._token:
            r = requests.post(f"{self.url}/auth/v1/token", params={"grant_type": "password"}, headers={"apikey": self.publica},
                              json={"email": self.email, "password": self.senha}, timeout=TEMPO)
            if not r.ok:
                raise RuntimeError(f"O login na API falhou (HTTP {r.status_code}).")
            self._token = r.json()["access_token"]
        return {"apikey": self.publica, "Authorization": f"Bearer {self._token}", "Accept-Profile": "api"}

    def ler(self, view, **filtros):
        linhas = []
        while True:
            r = requests.get(f"{self.url}/rest/v1/{view}", headers=self._cabecalhos(), timeout=TEMPO,
                             params={**filtros, "limit": LIMITE, "offset": len(linhas)})
            if not r.ok:
                raise RuntimeError(f"A API recusou a leitura da view {view} (HTTP {r.status_code}).")
            pagina = r.json()
            linhas += pagina
            if len(pagina) < LIMITE:
                return linhas


def _faixas():
    try:
        return json.loads(CATALOGO.read_text(encoding="utf-8"))["faixas_de_idade"]
    except (OSError, KeyError, ValueError):
        return [{"nome": "Até 10 anos", "ate": 10}, {"nome": "11 e 12 anos", "ate": 12},
                {"nome": "13 a 17 anos", "ate": 17}, {"nome": "18 anos ou mais", "ate": None}]


def faixa_de_idade(idade):
    if idade is None:
        return None
    for f in _faixas():
        if f["ate"] is None or idade <= f["ate"]:
            return f["nome"]
    return None


def exportar_da_api(unidade, atleta_id, tipo, referencia, arquivo_env=None, ficha=None, hoje=None):
    """Monta o contrato de um aluno a partir da API (todo o histórico disponível; o período fica marcado)."""
    unidade = C.MODALIDADES.get(str(unidade).upper().replace("-", " "), "PKZ")
    api = Api(arquivo_env)
    alunos = api.ler("atleta", atleta_id=f"eq.{atleta_id}")
    if not alunos:
        raise ValueError(f"Aluno {atleta_id} não encontrado na API.")
    a = alunos[0]
    if a.get("unidade") != unidade:
        raise ValueError(f"O aluno {atleta_id} é da unidade {a.get('unidade')}, não de {unidade}.")
    inicio, fim = C.periodo_padrao(tipo, referencia)
    sessoes = api.ler("presenca", atleta_id=f"eq.{atleta_id}", select="data,hora_inicio,status", order="data.asc")
    treinos = api.ler("treino", atleta_id=f"eq.{atleta_id}", order="data.asc")
    contrato = C.modelo_vazio(unidade, tipo)
    contrato.update({
        "periodo": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
        "aluno": {"id": a["atleta_id"], "nome": a.get("nome"), "data_nascimento": None, "idade": a.get("idade"),
                  "categoria": a.get("categoria"), "modalidade": a.get("modalidade"), "clube": None, "turno": None},
        "sessoes": [{"data": s["data"], "hora_inicio": s.get("hora_inicio"), "status": s["status"]} for s in sessoes],
        "treinos": [{c: t.get(c) for c in ("data",) + C.CAMPOS_TREINO} for t in treinos],
        "origem": {"fonte": "api", "gerado_em": datetime.now().isoformat(timespec="seconds"), "view": "api.*"},
    })
    # Avaliações físicas e colegas da mesma unidade e faixa de idade (o One to One também usa, quando houver testes).
    contrato["avaliacoes"] = [{k: r.get(k) for k in ("avaliacao_id", "data_avaliacao", "teste", "teste_nome", "lado",
                                                     "unidade_medida", "maior_melhor", "confirmado", "valor")}
                              for r in api.ler("evolucao", atleta_id=f"eq.{atleta_id}", order="data_avaliacao.asc")]
    faixa = faixa_de_idade(a.get("idade"))
    colegas = [x for x in api.ler("atleta", unidade=f"eq.{unidade}", select="atleta_id,idade")
               if x["atleta_id"] != atleta_id and faixa and faixa_de_idade(x.get("idade")) == faixa]
    apelido = {x["atleta_id"]: f"colega-{i}" for i, x in enumerate(colegas, start=1)}
    grupo = []
    if apelido:
        for r in api.ler("evolucao", select="atleta_id,teste,lado,data_avaliacao,valor,confirmado,maior_melhor"):
            if r["atleta_id"] in apelido:
                grupo.append({**{k: r.get(k) for k in ("teste", "lado", "data_avaliacao", "valor", "confirmado", "maior_melhor")},
                              "aluno": apelido[r["atleta_id"]]})
    contrato["grupo"] = {"descricao": f"colegas {'da PKZ' if unidade == 'PKZ' else 'do One to One'} na faixa {faixa.lower()}" if faixa else None, "avaliacoes": grupo}
    reav = api.ler("reavaliacao", atleta_id=f"eq.{atleta_id}")
    if reav:
        contrato["reavaliacao"] = {k: reav[0].get(k) for k in ("ultima_avaliacao_em", "vence_em", "situacao")}
    if ficha:
        aplicar_ficha(contrato, ficha, hoje=hoje)
    return contrato


def listar_alunos(unidade, arquivo_env=None):
    """(id, nome, idade) dos alunos da unidade, para escolher de quem gerar."""
    api = Api(arquivo_env)
    return api.ler("atleta", unidade=f"eq.{unidade}", select="atleta_id,nome,idade,total_avaliacoes,ativo", order="nome.asc")


# ---------------------------------------------------------------- ficha de matrícula
def ler_ficha(caminho):
    """{nome normalizado: dados úteis} da ficha (CSV ou ZIP com um CSV). Descarta CPF, endereço e contatos."""
    caminho = Path(caminho)
    if caminho.suffix.lower() == ".zip":
        import io
        import zipfile
        with zipfile.ZipFile(caminho) as z:
            nomes = [n for n in z.namelist() if n.lower().endswith(".csv")]
            if not nomes:
                raise ValueError("O ZIP não tem nenhum CSV.")
            texto = z.read(nomes[0]).decode("utf-8-sig")
        linhas = list(csv.DictReader(io.StringIO(texto), delimiter=";" if texto.split("\n", 1)[0].count(";") > texto.split("\n", 1)[0].count(",") else ","))
    else:
        texto = caminho.read_text(encoding="utf-8-sig")
        primeira = texto.split("\n", 1)[0]
        import io
        linhas = list(csv.DictReader(io.StringIO(texto), delimiter=";" if primeira.count(";") > primeira.count(",") else ","))
    colunas = {C.chave_nome(k): k for k in (linhas[0].keys() if linhas else [])}
    def coluna(campo):
        return colunas.get(COLUNAS_FICHA[campo])
    if not coluna("nome"):
        raise ValueError("A ficha não tem a coluna 'Nome Completo Aluno'.")
    fichas, repetidos = {}, set()
    for linha in linhas:
        nome = C.texto_real(linha.get(coluna("nome")))
        if not nome:
            continue
        chave = C.chave_nome(nome)
        if chave in fichas:
            repetidos.add(chave)
        fichas[chave] = {
            "nascimento": C.ler_data(linha.get(coluna("nascimento"))) if coluna("nascimento") else None,
            "modalidade": C.texto_real(linha.get(coluna("modalidade"))) if coluna("modalidade") else None,
            "clube": C.texto_real(linha.get(coluna("clube"))) if coluna("clube") else None,
            "turno": C.texto_real(linha.get(coluna("turno"))) if coluna("turno") else None,
        }
    for chave in repetidos:  # nome repetido na ficha: não dá para saber qual é o certo
        fichas[chave] = None
    return fichas


def aplicar_ficha(contrato, fichas, hoje=None):
    """Completa a identificação do aluno com a ficha, se o nome bater exatamente. Devolve o que foi usado."""
    if not isinstance(fichas, dict):
        fichas = ler_ficha(fichas)
    chave = C.chave_nome(contrato["aluno"].get("nome"))
    registro = fichas.get(chave)
    origem = contrato.setdefault("origem", {})
    if chave in fichas and registro is None:
        origem["ficha"] = "nome repetido na ficha: não usada"
        return None
    if not registro:
        origem["ficha"] = "aluno não encontrado na ficha"
        return None
    aluno = contrato["aluno"]
    if registro["nascimento"]:
        aluno["data_nascimento"] = registro["nascimento"].isoformat()
        aluno["idade"] = C.idade_em(registro["nascimento"], hoje or date.today())
    for campo in ("modalidade", "clube", "turno"):
        if registro[campo] and not aluno.get(campo):
            aluno[campo] = registro[campo]
    origem["ficha"] = "dados da ficha de matrícula aplicados (nascimento, modalidade, clube e turno)"
    return registro


# ---------------------------------------------------------------- CSV
def importar_csv(pasta, modalidade, tipo, inicio, aluno):
    """Monta um contrato a partir de sessoes.csv, avaliacoes.csv e treinos.csv (os que existirem na pasta).

    As colunas têm os mesmos nomes dos campos do contrato. Separador , ou ;.
    """
    pasta = Path(pasta)
    contrato = C.modelo_vazio(modalidade, tipo)
    ini, fim = C.periodo_padrao(tipo, C.ler_data(inicio) or date.today())
    contrato["periodo"] = {"inicio": ini.isoformat(), "fim": fim.isoformat()}
    contrato["aluno"].update(aluno)
    contrato["origem"] = {"fonte": "csv", "pasta": str(pasta)}
    for nome, campo in (("sessoes.csv", "sessoes"), ("avaliacoes.csv", "avaliacoes"), ("treinos.csv", "treinos")):
        arquivo = pasta / nome
        if arquivo.exists():
            texto = arquivo.read_text(encoding="utf-8-sig")
            primeira = texto.split("\n", 1)[0]
            import io
            contrato[campo] = list(csv.DictReader(io.StringIO(texto), delimiter=";" if primeira.count(";") > primeira.count(",") else ","))
    return contrato
