import importlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def generator():
    """Importa o gerador sem carregar o .env local durante os testes."""
    with patch("dotenv.load_dotenv"):
        return importlib.import_module("gerador_pkz.gerar_pdf")


@pytest.fixture
def sample_json_dir():
    return REPO_ROOT / "exemplos" / "api"


@pytest.fixture
def output_dir(generator, tmp_path, monkeypatch):
    destino = tmp_path / "relatorios-ficticios"
    monkeypatch.setattr(generator, "SAIDA_DIR", destino)
    return destino


@pytest.fixture
def pkz_json_factory(tmp_path):
    def create(evolucoes=None, presencas=None, atleta=None):
        directory = tmp_path / f"pkz-fixture-{len(list(tmp_path.iterdir()))}"
        directory.mkdir()
        atleta_id = "synthetic-pkz-0001"
        dados_atleta = atleta or {
            "atleta_id": atleta_id,
            "unidade": "PKZ",
            "nome": "Atleta Sintético",
            "idade": 14,
            "categoria": "Sub-15",
            "ativo": True,
        }
        (directory / "atleta.json").write_text(
            json.dumps([dados_atleta], ensure_ascii=False), encoding="utf-8"
        )
        (directory / "evolucao.json").write_text(
            json.dumps(evolucoes or [], ensure_ascii=False), encoding="utf-8"
        )
        if presencas is not None:
            (directory / "presenca.json").write_text(
                json.dumps(presencas, ensure_ascii=False), encoding="utf-8"
            )
        return directory

    return create


@pytest.fixture
def synthetic_evolutions():
    athlete_id = "synthetic-pkz-0001"
    return [
        {
            "atleta_id": athlete_id, "avaliacao_id": "eval-mar",
            "data_avaliacao": "2026-03-10", "teste": "sprint_20m",
            "teste_nome": "Sprint 20 m", "lado": None,
            "unidade_medida": "s", "maior_melhor": False,
            "confirmado": True, "valor": 3.3,
        },
        {
            "atleta_id": athlete_id, "avaliacao_id": "eval-may",
            "data_avaliacao": "2026-05-22", "teste": "sprint_20m",
            "teste_nome": "Sprint 20 m", "lado": None,
            "unidade_medida": "s", "maior_melhor": False,
            "confirmado": True, "valor": 3.2,
        },
        {
            "atleta_id": athlete_id, "avaliacao_id": "eval-aug",
            "data_avaliacao": "2026-08-20", "teste": "sprint_20m",
            "teste_nome": "Sprint 20 m", "lado": None,
            "unidade_medida": "s", "maior_melhor": False,
            "confirmado": True, "valor": 3.1,
        },
        {
            "atleta_id": athlete_id, "avaliacao_id": "eval-sep",
            "data_avaliacao": "2026-09-05", "teste": "sprint_20m",
            "teste_nome": "Sprint 20 m", "lado": None,
            "unidade_medida": "s", "maior_melhor": False,
            "confirmado": True, "valor": 2.0,
        },
    ]


@pytest.fixture
def oto_data_factory():
    def create(trainings=None, attendances=None):
        return (
            {
                "atleta_id": "synthetic-oto-0001",
                "unidade": "ONE_TO_ONE",
                "nome": "Aluno Sintético",
                "idade": 15,
                "ativo": True,
            },
            attendances or [],
            trainings or [],
        )

    return create


@pytest.fixture
def one_year_trainings():
    return [
        {
            "data": f"2026-{month:02d}-10",
            "objetivos": f"Objetivo sintético {month:02d}",
            "tipo_treino": "Força e mobilidade",
            "intensidade": "Média",
            "desempenho": f"Execução fictícia {month:02d}",
        }
        for month in range(1, 13)
    ]
