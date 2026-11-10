import datetime as dt
import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from pypdf import PdfReader


SYNTHETIC_ID = "synthetic-pkz-0001"


def evaluation(day, value, *, test="sprint_20m", side=None,
               greater_is_better=False, confirmed=True, evaluation_id=None):
    return {
        "atleta_id": SYNTHETIC_ID,
        "avaliacao_id": evaluation_id or f"eval-{day}-{test}-{side or 'single'}",
        "data_avaliacao": day,
        "teste": test,
        "teste_nome": test.replace("_", " ").title(),
        "lado": side,
        "unidade_medida": "s" if test == "sprint_20m" else "hits",
        "maior_melhor": greater_is_better,
        "confirmado": confirmed,
        "valor": value,
    }


def pdf_text(path):
    text = "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    return " ".join(text.split())


def test_example_json_files_match_contract_and_load(generator, sample_json_dir):
    athletes = generator.carregar_json("atleta.json", sample_json_dir)
    evolutions = generator.carregar_json("evolucao.json", sample_json_dir)
    comparisons = generator.carregar_json("comparacao.json", sample_json_dir)

    assert athletes and all(row.get("atleta_id") for row in athletes)
    assert evolutions and comparisons
    assert all({"teste", "data_avaliacao", "valor", "maior_melhor", "confirmado"} <= row.keys() for row in evolutions)


def test_root_pkz_examples_stay_synced_with_backend_fixtures(sample_json_dir):
    backend_dir = sample_json_dir.parents[1] / "backend" / "exemplos" / "api"
    for name in ("atleta.json", "comparacao.json", "evolucao.json"):
        assert (sample_json_dir / name).read_bytes() == (backend_dir / name).read_bytes()


def test_json_mode_selects_atleta_and_filters_related_rows(generator, sample_json_dir):
    athlete, comparisons, evolutions, attendances = generator.buscar_dados_atleta(None, sample_json_dir)

    assert athlete["unidade"] == "PKZ"
    assert comparisons == []  # O gerador calcula a comparação a partir da evolução.
    assert evolutions
    assert all(row["atleta_id"] == athlete["atleta_id"] for row in evolutions)
    assert attendances == []  # presenca.json é opcional nos exemplos atuais.


@pytest.mark.parametrize("contents", ["{}", "[1, 2]"])
def test_json_loader_rejects_non_record_lists(generator, tmp_path, contents):
    (tmp_path / "bad.json").write_text(contents, encoding="utf-8")
    with pytest.raises(ValueError):
        generator.carregar_json("bad.json", tmp_path)


def test_json_loader_rejects_malformed_json(generator, tmp_path):
    (tmp_path / "bad.json").write_text("[", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        generator.carregar_json("bad.json", tmp_path)


@pytest.mark.parametrize(
    ("previous", "current", "greater_is_better", "expected"),
    [
        (10, 12, True, "melhorou"),
        (10, 8, True, "piorou"),
        (10, 8, False, "melhorou"),
        (10, 12, False, "piorou"),
    ],
)
def test_comparison_uses_greater_is_better_and_percentage(
    generator, previous, current, greater_is_better, expected
):
    rows = [
        evaluation("2026-05-01", previous, greater_is_better=greater_is_better),
        evaluation("2026-08-01", current, greater_is_better=greater_is_better),
    ]
    result = generator.montar_comparacoes(rows)[0]

    assert result["valor_anterior"] == previous
    assert result["valor_atual"] == current
    assert result["variacao_pct"] == pytest.approx((current - previous) / previous * 100)
    assert result["situacao"] == expected


def test_comparison_without_direction_is_not_classified(generator):
    result = generator.montar_comparacoes([
        evaluation("2026-05-01", 10, greater_is_better=None),
        evaluation("2026-08-01", 12, greater_is_better=None),
    ])[0]
    assert result["situacao"] == "sem_classificacao"


def test_equal_values_are_stable_even_without_direction(generator):
    result = generator.montar_comparacoes([
        evaluation("2026-05-01", 0, greater_is_better=None),
        evaluation("2026-08-01", 0, greater_is_better=None),
    ])[0]
    assert result["variacao_pct"] is None
    assert result["situacao"] == "estavel"


@pytest.mark.parametrize("confirmed", [False, None])
def test_unconfirmed_or_missing_confirmation_never_says_improved_or_worse(generator, confirmed):
    result = generator.montar_comparacoes([
        evaluation("2026-05-01", 10, greater_is_better=True),
        evaluation("2026-08-01", 12, greater_is_better=True, confirmed=confirmed),
    ])[0]
    assert result["situacao"] == "em_validacao"
    assert result["situacao"] not in {"melhorou", "piorou"}


def test_comparison_without_previous_value(generator):
    result = generator.montar_comparacoes([
        evaluation("2026-08-01", 12),
    ])[0]
    assert result["valor_anterior"] is None
    assert result["variacao_pct"] is None
    assert result["situacao"] == "sem_comparacao"


def test_comparisons_are_separated_by_test_and_side(generator):
    rows = [
        evaluation("2026-05-01", 10, test="cross_hop", side="dir", greater_is_better=True),
        evaluation("2026-05-01", 20, test="cross_hop", side="esq", greater_is_better=True),
        evaluation("2026-08-01", 12, test="cross_hop", side="dir", greater_is_better=True),
        evaluation("2026-08-01", 18, test="cross_hop", side="esq", greater_is_better=True),
        evaluation("2026-08-01", 5, test="sprint_20m", greater_is_better=False),
    ]
    results = generator.montar_comparacoes(rows)
    by_key = {(row["teste"], row["lado"]): row for row in results}

    assert set(by_key) == {("cross_hop", "dir"), ("cross_hop", "esq"), ("sprint_20m", None)}
    assert by_key[("cross_hop", "dir")]["valor_anterior"] == 10
    assert by_key[("cross_hop", "esq")]["valor_anterior"] == 20


@pytest.mark.parametrize(
    ("current", "expected_situation"),
    [(0, "estavel"), (2, "piorou")],
)
def test_aquabag_zero_previous_has_no_fabricated_percentage(
    generator, current, expected_situation
):
    rows = [
        evaluation("2026-05-01", 0, test="estabilidade_aquabag", greater_is_better=False),
        evaluation("2026-08-01", current, test="estabilidade_aquabag", greater_is_better=False),
    ]
    result = generator.montar_comparacoes(rows)[0]

    assert result["variacao_pct"] is None
    assert result["situacao"] == expected_situation


def test_aquabag_zero_previous_obeys_greater_is_better(generator):
    result = generator.montar_comparacoes([
        evaluation("2026-05-01", 0, test="estabilidade_aquabag", greater_is_better=True),
        evaluation("2026-08-01", 2, test="estabilidade_aquabag", greater_is_better=True),
    ])[0]
    assert result["variacao_pct"] is None
    assert result["situacao"] == "melhorou"


def test_pkz_comparison_wraps_long_aquabag_values_inside_cells(
    generator, monkeypatch, pkz_json_factory, output_dir
):
    evolutions = [
        evaluation(
            "2026-05-01", 0, test="estabilidade_aquabag", greater_is_better=False
        ),
        evaluation(
            "2026-08-20", 1, test="estabilidade_aquabag", greater_is_better=False
        ),
    ]
    for row in evolutions:
        row["teste_nome"] = "Estabilidade Aquabag"
        row["unidade_medida"] = "desequilibrios"

    tables = []
    criar_tabela_original = generator.criar_tabela

    def capturar_tabela(*args, **kwargs):
        tabela = criar_tabela_original(*args, **kwargs)
        celulas = [
            [
                (
                    type(valor).__name__,
                    valor.getPlainText() if isinstance(valor, generator.Paragraph) else str(valor),
                )
                for valor in linha
            ]
            for linha in tabela._cellvalues
        ]
        tables.append((args, kwargs, celulas))
        return tabela

    monkeypatch.setattr(generator, "criar_tabela", capturar_tabela)
    data_dir = pkz_json_factory(evolucoes=evolutions, presencas=[])
    result = generator.gerar_relatorio(
        SYNTHETIC_ID, "mensal", dt.date(2026, 8, 20), json_dir=data_dir
    )

    assert result.exists()
    comparison_table = next(
        (kwargs, celulas)
        for args, kwargs, celulas in tables
        if len(args[0][0]) == 5 and args[0][0] == [
            "Teste", "Anterior", "Atual", "Variação", "Situação"
        ]
    )
    table_options, cells = comparison_table
    assert table_options["envolver_todas_colunas"] is True
    assert all(
        cells[1][column][0] == "Paragraph"
        for column in (1, 2)
    )
    assert cells[1][1][1] == "0,00 desequilíbrios"
    assert cells[1][2][1] == "1,00 desequilíbrios"


def test_blazepod_sample_is_used_only_if_a_valid_fixture_exists(generator, sample_json_dir):
    rows = generator.carregar_json("evolucao.json", sample_json_dir)
    blazepod = [row for row in rows if "blazepod" in str(row.get("teste", "")).lower()]
    valid = [row for row in blazepod if isinstance(row.get("valor"), (int, float)) and row.get("confirmado") is True]
    if not valid:
        pytest.skip("O repositório não contém fixture Blazepod validada; valores não serão inventados.")

    chart = generator.criar_grafico(valid, valid[0].get("teste_nome", "Blazepod"))
    assert chart is not None
    chart.close()


@pytest.mark.parametrize(
    ("period", "reference", "start", "end"),
    [
        ("semanal", "2026-08-20", "2026-08-17", "2026-08-23"),
        ("semanal", "2026-05-15", "2026-05-11", "2026-05-17"),
        ("mensal", "2026-08-20", "2026-08-01", "2026-08-31"),
        ("mensal", "2026-05-15", "2026-05-01", "2026-05-31"),
        ("anual", "2026-08-20", "2026-01-01", "2026-12-31"),
        ("anual", "2026-05-15", "2026-01-01", "2026-12-31"),
    ],
)
def test_period_boundaries(generator, period, reference, start, end):
    actual = generator.periodo_datas(period, dt.date.fromisoformat(reference))
    assert actual == (dt.date.fromisoformat(start), dt.date.fromisoformat(end))


def test_monthly_may_comparison_includes_only_rows_through_month_end(
    generator, pkz_json_factory, synthetic_evolutions, output_dir
):
    data_dir = pkz_json_factory(synthetic_evolutions)
    result = generator.gerar_relatorio(
        SYNTHETIC_ID, "mensal", dt.date(2026, 5, 15), json_dir=data_dir
    )
    text = pdf_text(result)

    # May 22 belongs to the full May calendar month; August and September do not.
    assert "3,20 s" in text
    assert "2,00 s" not in text


def test_august_comparison_excludes_evaluations_after_month_end(
    generator, monkeypatch, pkz_json_factory, synthetic_evolutions, output_dir
):
    captured = []
    original = generator.montar_comparacoes

    def capture(rows):
        captured.extend(rows)
        return original(rows)

    monkeypatch.setattr(generator, "montar_comparacoes", capture)
    data_dir = pkz_json_factory(synthetic_evolutions)
    result = generator.gerar_relatorio(
        SYNTHETIC_ID, "mensal", dt.date(2026, 8, 20), json_dir=data_dir
    )

    assert result.exists()
    assert captured
    assert max(row["data_avaliacao"] for row in captured) == "2026-08-20"
    text = pdf_text(result)
    assert "3,10 s" in text
    assert "2,00 s" not in text


def test_pkz_does_not_create_pdf_without_evaluations_or_attendance(
    generator, pkz_json_factory, output_dir, capsys
):
    data_dir = pkz_json_factory(evolucoes=[], presencas=[])
    result = generator.gerar_relatorio(
        SYNTHETIC_ID, "mensal", dt.date(2026, 8, 20), json_dir=data_dir
    )

    assert result is None
    assert not output_dir.exists()
    assert "PDF não gerado" in capsys.readouterr().out


def test_pkz_with_attendance_but_no_evaluation_renders_empty_evaluation_message(
    generator, pkz_json_factory, output_dir
):
    data_dir = pkz_json_factory(
        evolucoes=[],
        presencas=[{
            "atleta_id": SYNTHETIC_ID, "data": "2026-08-20", "status": "presente"
        }],
    )
    result = generator.gerar_relatorio(
        SYNTHETIC_ID, "mensal", dt.date(2026, 8, 20), json_dir=data_dir
    )
    assert "Nenhuma avaliação registrada" in pdf_text(result)


def test_attendance_frequency_counts_statuses_and_filters_period(generator):
    attendances = [
        {"data": "2026-08-17", "status": "presente"},
        {"data": "2026-08-18", "status": "presente"},
        {"data": "2026-08-19", "status": "presente"},
        {"data": "2026-08-20", "status": "falta"},
        {"data": "2026-08-21", "status": "cancelado"},
        {"data": "2026-08-22", "status": "agendado"},
        {"data": "2026-08-23", "status": "agendado"},
        {"data": "2026-08-24", "status": "presente"},
    ]
    result = generator.calcular_frequencia(
        attendances, dt.date(2026, 8, 17), dt.date(2026, 8, 23)
    )
    rows, present, absent, canceled, scheduled, percentage = result

    assert len(rows) == 7
    assert (present, absent, canceled, scheduled) == (3, 1, 1, 2)
    assert percentage == pytest.approx(75.0)


def test_api_pagination_reads_more_than_one_thousand_rows(generator, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://supabase.invalid")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "synthetic-test-key")
    records = [{"seq": i} for i in range(1205)]
    calls = []

    def fake_get(url, headers, params, timeout):
        start = int(headers["Range"].split("-", 1)[0])
        end = min(start + 1000, len(records))
        page = records[start:end]
        calls.append((url, headers.copy(), params.copy(), timeout, start))
        range_value = f"{start}-{end - 1}/{len(records)}" if page else f"*/{len(records)}"
        return Mock(ok=True, headers={"Content-Range": range_value}, json=Mock(return_value=page))

    monkeypatch.setattr(generator.requests, "get", fake_get)
    actual = generator.buscar_api("evolucao", {"atleta_id": "eq.synthetic"}, order="data_avaliacao.asc")

    assert actual == records
    assert [call[4] for call in calls] == [0, 1000]
    assert calls[0][1]["Prefer"] == "count=exact"
    assert calls[0][2] == {"atleta_id": "eq.synthetic", "order": "data_avaliacao.asc"}
    assert all(call[1]["Accept-Profile"] == "api" for call in calls)


def test_api_pagination_handles_server_page_cap_below_requested_range(generator, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://supabase.invalid")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "synthetic-test-key")
    records = [{"seq": i} for i in range(1200)]
    calls = []

    def fake_get(url, headers, params, timeout):
        start = int(headers["Range"].split("-", 1)[0])
        end = min(start + 500, len(records))
        page = records[start:end]
        calls.append(start)
        return Mock(ok=True, headers={"Content-Range": f"{start}-{end - 1}/{len(records)}"}, json=Mock(return_value=page))

    monkeypatch.setattr(generator.requests, "get", fake_get)
    actual = generator.buscar_api("treino")
    assert len(actual) == 1200
    assert calls == [0, 500, 1000]


def test_api_empty_response_returns_empty_list(generator, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://supabase.invalid")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "synthetic-test-key")
    response = Mock(ok=True, headers={"Content-Range": "*/0"}, json=Mock(return_value=[]))
    request = Mock(return_value=response)
    monkeypatch.setattr(generator.requests, "get", request)

    assert generator.buscar_api("presenca", {"atleta_id": "eq.synthetic"}) == []
    request.assert_called_once()


def test_api_http_failure_raises_without_exposing_api_key(generator, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://supabase.invalid")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "synthetic-test-key")
    response = Mock(ok=False, status_code=401, text="unauthorized", headers={})
    monkeypatch.setattr(generator.requests, "get", Mock(return_value=response))

    with pytest.raises(RuntimeError, match="HTTP 401") as error:
        generator.buscar_api("evolucao")
    assert "synthetic-test-key" not in str(error.value)


def test_api_rejects_non_list_response(generator, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://supabase.invalid")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "synthetic-test-key")
    response = Mock(ok=True, headers={}, json=Mock(return_value={"error": "invalid shape"}))
    monkeypatch.setattr(generator.requests, "get", Mock(return_value=response))

    with pytest.raises(RuntimeError, match="não retornou uma lista"):
        generator.buscar_api("evolucao")


def test_api_propagates_invalid_json_body(generator, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://supabase.invalid")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "synthetic-test-key")
    response = Mock(ok=True, headers={}, json=Mock(side_effect=ValueError("invalid JSON")))
    monkeypatch.setattr(generator.requests, "get", Mock(return_value=response))

    with pytest.raises(ValueError, match="invalid JSON"):
        generator.buscar_api("evolucao")


def test_api_rejects_page_when_range_is_ignored(generator, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://supabase.invalid")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "synthetic-test-key")
    page = [{"seq": i} for i in range(1000)]

    def fake_get(url, headers, params, timeout):
        return Mock(ok=True, headers={"Content-Range": "0-999/2000"}, json=Mock(return_value=page))

    monkeypatch.setattr(generator.requests, "get", fake_get)
    with pytest.raises(RuntimeError, match="não respeitou a paginação"):
        generator.buscar_api("evolucao")


def test_api_respects_explicit_limit(generator, monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://supabase.invalid")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "synthetic-test-key")
    page = [{"seq": 1}]
    request = Mock(return_value=Mock(
        ok=True, headers={"Content-Range": "0-0/50"}, json=Mock(return_value=page)
    ))
    monkeypatch.setattr(generator.requests, "get", request)

    assert generator.buscar_api("atleta", {"limit": 1}) == page
    request.assert_called_once()


def test_pkz_api_queries_all_required_views_with_atleta_and_unit_filters(generator, monkeypatch):
    athlete = {"atleta_id": SYNTHETIC_ID, "unidade": "PKZ"}
    calls = []

    def fake_api(view, filters=None, order=None):
        calls.append((view, filters, order))
        return [athlete] if view == "atleta" else []

    monkeypatch.setattr(generator, "buscar_api", fake_api)
    generator.buscar_dados_atleta(SYNTHETIC_ID)

    assert [call[0] for call in calls] == ["atleta", "comparacao", "evolucao", "presenca"]
    assert calls[0][1]["unidade"] == "eq.PKZ"
    assert calls[0][1]["atleta_id"] == f"eq.{SYNTHETIC_ID}"
    assert all(call[1]["atleta_id"] == f"eq.{SYNTHETIC_ID}" for call in calls[1:])


def test_one_to_one_api_filters_athlete_unit_and_period(generator, monkeypatch):
    calls = []

    def fake_api(view, filters=None, order=None):
        calls.append((view, filters, order))
        return [{"atleta_id": "synthetic-oto-0001", "unidade": "ONE_TO_ONE"}] if view == "atleta" else []

    monkeypatch.setattr(generator, "buscar_api", fake_api)
    start, end = dt.date(2026, 8, 17), dt.date(2026, 8, 23)
    generator.carregar_dados_one_to_one("synthetic-oto-0001", start, end)

    by_view = {view: filters for view, filters, _ in calls}
    assert set(by_view) == {"atleta", "presenca", "treino"}
    assert by_view["presenca"]["atleta_id"] == "eq.synthetic-oto-0001"
    assert by_view["presenca"]["unidade"] == "eq.ONE_TO_ONE"
    assert by_view["presenca"]["and"] == "(data.gte.2026-08-17,data.lte.2026-08-23)"
    assert by_view["treino"]["and"] == by_view["presenca"]["and"]


def test_one_to_one_frequency_excludes_cancelled_and_scheduled_from_percentage(generator):
    attendances = [
        {"data": "2026-08-17", "status": "presente"},
        {"data": "2026-08-18", "status": "presente"},
        {"data": "2026-08-19", "status": "presente"},
        {"data": "2026-08-20", "status": "falta"},
        {"data": "2026-08-21", "status": "cancelado"},
        {"data": "2026-08-22", "status": "agendado"},
        {"data": "2026-08-23", "status": "aguardando_confirmacao"},
    ]
    rows, present, absent, canceled, scheduled, percentage = generator.calcular_frequencia(
        attendances, dt.date(2026, 8, 17), dt.date(2026, 8, 23)
    )

    assert len(rows) == 7
    assert (present, absent, canceled, scheduled) == (3, 1, 1, 1)
    assert percentage == pytest.approx(75)


def test_one_to_one_pdf_summarizes_all_attendance_statuses_and_percentage(
    generator, monkeypatch, output_dir, oto_data_factory
):
    attendances = [
        {"data": "2026-08-17", "status": "presente"},
        {"data": "2026-08-18", "status": "presente"},
        {"data": "2026-08-19", "status": "presente"},
        {"data": "2026-08-20", "status": "falta"},
        {"data": "2026-08-21", "status": "cancelado"},
        {"data": "2026-08-22", "status": "agendado"},
    ]
    bundle = oto_data_factory(trainings=[], attendances=attendances)
    monkeypatch.setattr(generator, "carregar_dados_one_to_one", lambda *args: bundle)
    path = generator.gerar_relatorio_one_to_one(
        "synthetic-oto-attendance", "semanal", dt.date(2026, 8, 20)
    )
    text = pdf_text(path)

    for label in ("Presenças", "Faltas", "Cancelamentos", "Agendamentos"):
        assert label in text
    assert "75,0%" in text


def test_one_to_one_missing_frequency_is_none_not_zero(generator):
    result = generator.calcular_frequencia([], dt.date(2026, 8, 1), dt.date(2026, 8, 31))
    assert result[-1] is None


@pytest.mark.parametrize(
    ("kind", "period", "reference"),
    [
        ("pkz", "semanal", "2026-08-20"),
        ("pkz", "mensal", "2026-05-15"),
        ("pkz", "anual", "2026-11-10"),
        ("oto", "semanal", "2026-08-20"),
        ("oto", "mensal", "2026-05-15"),
        ("oto", "anual", "2026-11-10"),
    ],
)
def test_all_six_report_types_generate_valid_pdf_outside_repository(
    generator, monkeypatch, tmp_path, output_dir, pkz_json_factory,
    synthetic_evolutions, oto_data_factory, one_year_trainings,
    kind, period, reference,
):
    if kind == "pkz":
        source_dir = pkz_json_factory(synthetic_evolutions)
        path = generator.gerar_relatorio(
            SYNTHETIC_ID, period, dt.date.fromisoformat(reference), json_dir=source_dir
        )
    else:
        if period == "anual":
            trainings = one_year_trainings
        else:
            trainings = [{
                "data": reference, "objetivos": "Objetivo sintético",
                "tipo_treino": "Treino fictício", "intensidade": "Média",
                "desempenho": "Execução fictícia",
            }]
        bundle = oto_data_factory(
            trainings=trainings,
            attendances=[{"data": reference, "status": "presente"}],
        )
        monkeypatch.setattr(generator, "carregar_dados_one_to_one", lambda *args: bundle)
        path = generator.gerar_relatorio_one_to_one(
            "synthetic-oto-0001", period, dt.date.fromisoformat(reference)
        )

    assert path.exists()
    assert path.parent == output_dir
    assert generator.BASE_DIR.resolve() not in path.resolve().parents
    reader = PdfReader(str(path))
    assert len(reader.pages) >= 1
    assert "Relat" in pdf_text(path)


def test_one_to_one_pdf_contains_filled_fields_and_accented_text(
    generator, monkeypatch, output_dir, oto_data_factory
):
    training = {
        "data": "2026-08-20",
        "objetivos": "Equilíbrio, força e mobilidade",
        "tipo_treino": "Preparação física",
        "intensidade": "Média",
        "desempenho": "Execução técnica concluída",
    }
    bundle = oto_data_factory(
        trainings=[training],
        attendances=[{"data": "2026-08-20", "status": "presente"}],
    )
    monkeypatch.setattr(generator, "carregar_dados_one_to_one", lambda *args: bundle)
    path = generator.gerar_relatorio_one_to_one(
        "synthetic-oto-fields", "semanal", dt.date(2026, 8, 20)
    )
    text = pdf_text(path)

    assert "Equilíbrio, força e mobilidade" in text
    assert "Preparação física" in text
    assert "Execução técnica concluída" in text
    assert "Frequência" in text
    assert "período" in text


def test_one_to_one_missing_values_are_not_fabricated(
    generator, monkeypatch, output_dir, oto_data_factory
):
    trainings = [
        {"data": "2026-08-20", "objetivos": "Objetivo sintético", "tipo_treino": "Técnico"},
        {"data": "2026-08-21", "objetivos": None, "tipo_treino": "Técnico", "intensidade": None, "desempenho": ""},
    ]
    bundle = oto_data_factory(
        trainings=trainings,
        attendances=[{"data": "2026-08-20", "status": "presente"}],
    )
    monkeypatch.setattr(generator, "carregar_dados_one_to_one", lambda *args: bundle)
    path = generator.gerar_relatorio_one_to_one(
        "synthetic-oto-missing", "mensal", dt.date(2026, 8, 20)
    )
    text = pdf_text(path)

    assert "Objetivo sintético" in text
    assert "—" in text
    assert "valor fictício" not in text.lower()


def test_one_to_one_annual_shows_ten_recent_and_total_twelve(
    generator, monkeypatch, output_dir, oto_data_factory, one_year_trainings
):
    bundle = oto_data_factory(
        trainings=one_year_trainings,
        attendances=[{"data": "2026-12-10", "status": "presente"}],
    )
    monkeypatch.setattr(generator, "carregar_dados_one_to_one", lambda *args: bundle)
    path = generator.gerar_relatorio_one_to_one(
        "synthetic-oto-annual-12", "anual", dt.date(2026, 12, 15)
    )
    text = pdf_text(path)

    assert "Total de treinos no período: 12" in text
    assert "Objetivo sintético 01" not in text
    assert "Objetivo sintético 02" not in text
    for month in range(3, 13):
        assert f"Objetivo sintético {month:02d}" in text
    assert "10 treinos mais recentes" in text


def test_one_to_one_with_all_training_fields_absent_shows_message(
    generator, monkeypatch, output_dir, oto_data_factory
):
    bundle = oto_data_factory(
        trainings=[{
            "data": "2026-08-20", "objetivos": None,
            "tipo_treino": None, "intensidade": None, "desempenho": None,
        }],
        attendances=[{"data": "2026-08-20", "status": "presente"}],
    )
    monkeypatch.setattr(generator, "carregar_dados_one_to_one", lambda *args: bundle)
    path = generator.gerar_relatorio_one_to_one(
        "synthetic-oto-no-fields", "mensal", dt.date(2026, 8, 20)
    )
    text = pdf_text(path)

    assert "ainda não estão registrados" in text
    assert "Objetivos" not in text


def test_pkz_and_one_to_one_do_not_generate_pdf_without_period_data(
    generator, monkeypatch, output_dir, pkz_json_factory, oto_data_factory, capsys
):
    empty_json = pkz_json_factory(evolucoes=[], presencas=[])
    pkz_path = generator.gerar_relatorio(
        SYNTHETIC_ID, "mensal", dt.date(2026, 8, 20), json_dir=empty_json
    )
    empty_bundle = oto_data_factory(trainings=[], attendances=[])
    monkeypatch.setattr(generator, "carregar_dados_one_to_one", lambda *args: empty_bundle)
    oto_path = generator.gerar_relatorio_one_to_one(
        "synthetic-oto-empty", "mensal", dt.date(2026, 8, 20)
    )

    assert pkz_path is None and oto_path is None
    assert not output_dir.exists()
    output = capsys.readouterr().out
    assert "Nenhuma avaliação ou agendamento" in output
    assert "Nenhum agendamento ou treino" in output


def test_cli_accepts_json_directory_without_atleta_id(generator, monkeypatch):
    calls = []
    monkeypatch.setattr(generator, "gerar_relatorio", lambda *args: calls.append(args))
    monkeypatch.setattr("sys.argv", ["gerar_pdf.py", "--json-dir", "exemplos/api", "--referencia", "2026-08-20"])

    generator.main()
    assert calls[0][0] is None
    assert calls[0][3] == Path("exemplos/api")


def test_cli_runs_one_to_one_with_period_and_reference(
    generator, monkeypatch, output_dir, oto_data_factory
):
    bundle = oto_data_factory(
        trainings=[{
            "data": "2026-08-20",
            "objetivos": "Objetivo sintético da CLI",
            "tipo_treino": "Treino fictício",
            "intensidade": "Média",
            "desempenho": "Execução fictícia",
        }],
        attendances=[{"data": "2026-08-20", "status": "presente"}],
    )
    chamadas = []

    def carregar_dados(atleta_id, inicio, fim):
        chamadas.append((atleta_id, inicio, fim))
        return bundle

    monkeypatch.setattr(generator, "carregar_dados_one_to_one", carregar_dados)
    monkeypatch.setattr(
        generator,
        "gerar_relatorio",
        lambda *args: pytest.fail("A CLI desviou para o relatório PKZ."),
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "gerar_pdf.py", "synthetic-oto-cli", "--one-to-one",
            "--periodo", "semanal", "--referencia", "2026-08-20",
        ],
    )

    generator.main()

    assert chamadas == [(
        "synthetic-oto-cli", dt.date(2026, 8, 17), dt.date(2026, 8, 23)
    )]
    pdfs = list(output_dir.glob(
        "relatorio_one_to_one_semanal_synthetic-oto-cli_2026-08-20.pdf"
    ))
    assert len(pdfs) == 1
    text = pdf_text(pdfs[0])
    assert "Relatório semanal — 17/08 a 23/08/2026" in text
    assert "Objetivo sintético da CLI" in text
