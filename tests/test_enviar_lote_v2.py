"""O envio em lote usa o gerador v2 por padrão, sem chamar a API (fontes e render simulados)."""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "relatorios"))

import enviar_lote  # noqa: E402
from gerador_pkz.v2 import contrato as C  # noqa: E402
from gerador_pkz.v2 import fontes, render  # noqa: E402

ALUNO = {"atleta_id": "00000000-0000-4000-8000-000000000001", "unidade": "PKZ", "nome": "Teste Automatizado"}
REFERENCIA = date(2026, 8, 15)


def contrato(sessoes):
    inicio, fim = C.periodo_padrao("mensal", REFERENCIA)
    return {"modalidade": "PKZ", "tipo_relatorio": "mensal",
            "periodo": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
            "aluno": {"nome": "Teste Automatizado", "idade": 12}, "sessoes": sessoes,
            "avaliacoes": [], "treinos": [], "grupo": {"descricao": None, "avaliacoes": []}}


@pytest.fixture
def chamadas(monkeypatch, tmp_path):
    feitas = {}
    monkeypatch.delenv("RELATORIO_RENDERIZADOR", raising=False)
    monkeypatch.setattr(enviar_lote, "SAIDA_V2", tmp_path)

    def gerar_pdf(bruto, destino, **_):
        feitas["destino"] = Path(destino)
        return Path(destino), [], []

    monkeypatch.setattr(render, "gerar_pdf", gerar_pdf)
    return feitas


def test_v2_e_o_padrao_e_gera_o_pdf(monkeypatch, chamadas, tmp_path):
    sessao = [{"data": "2026-08-04", "hora_inicio": "17:00", "status": "presente"}]
    monkeypatch.setattr(fontes, "exportar_da_api", lambda *a, **k: contrato(sessao))
    pdf = enviar_lote.gerar_relatorio(ALUNO, "mensal", REFERENCIA)
    assert pdf == chamadas["destino"]
    assert pdf.parent == tmp_path
    assert pdf.name == f"relatorio_v2_pkz_{ALUNO['atleta_id']}_mensal_2026-08-01.pdf"


def test_v2_sem_registro_no_periodo_pula_o_aluno(monkeypatch, chamadas):
    fora = [{"data": "2026-07-04", "hora_inicio": "17:00", "status": "presente"}]
    monkeypatch.setattr(fontes, "exportar_da_api", lambda *a, **k: contrato(fora))
    assert enviar_lote.gerar_relatorio(ALUNO, "mensal", REFERENCIA) is None
    assert "destino" not in chamadas


def test_v2_com_erro_de_validacao_vira_erro_do_aluno(monkeypatch, chamadas):
    invalida = [{"data": "2026-08-04", "hora_inicio": "17:00", "status": "inventado"}]
    monkeypatch.setattr(fontes, "exportar_da_api", lambda *a, **k: contrato(invalida))
    with pytest.raises(C.ContratoInvalido):
        enviar_lote.gerar_relatorio(ALUNO, "mensal", REFERENCIA)
    assert "destino" not in chamadas
