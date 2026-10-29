import io

from fastapi.testclient import TestClient
from openpyxl import Workbook
import pytest

from app.main import app


def report(*, line="TWL", track="UT", section="Mainline", algorithm="median_v1", mode="chainage_median",
           chart_line=None):
    workbook = Workbook()
    summary = workbook.active
    summary.title = "Summary"
    headers = ["ID", "Exception Type", "MaxValue", "MaxLocation", "FromM", "ToM", "Length", "Level"]
    values = ["x", "Low Height", 3800., 100., 99., 101., 2., "L2"]
    if line:
        headers += ["Line", "Track", "Section"]
        values += [line, track, section]
    summary.append(headers)
    summary.append(values)
    exceptions = workbook.create_sheet("Low Height")
    exceptions.append(headers)
    exceptions.append(values)
    chart = workbook.create_sheet("ChartData")
    chart.append(["Chainage", "height1", "line", "track", "Section"])
    chart.append([100., 3800., chart_line if chart_line is not None else line, track if line else "", section if line else ""])
    meta = workbook.create_sheet("_Metadata")
    meta.append(["key", "value"])
    if algorithm:
        meta.append(["algorithm", algorithm])
    if mode:
        meta.append(["chart_data_mode", mode])
    provenance = workbook.create_sheet("ExceptionProvenance")
    provenance.append(["exception_id", "source_row"])
    provenance.append(["x", 12])
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def compare(first, second):
    with TestClient(app) as client:
        return client.post("/api/analyze/compare", files=[
            ("files", ("20260907_report.xlsx", first, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
            ("files", ("20260630_report.xlsx", second, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
        ])


@pytest.mark.parametrize("changed", [dict(line="AEL"), dict(track="DT"), dict(line="TKL", section="TKS"),
                                     dict(line="EAL", section="LMC")])
def test_known_scope_disagreement_is_structured_422(changed):
    response = compare(report(), report(**changed))
    assert response.status_code == 422, response.text
    assert response.json()["detail"]["code"] == "INCOMPATIBLE_REPORT_SCOPE"


def test_history_rejects_disagreeing_algorithm_mode_and_version():
    for changed in (dict(algorithm="other_v2"), dict(mode="raw")):
        response = compare(report(), report(**changed))
        assert response.status_code == 422
        assert response.json()["detail"]["code"] == "INCOMPATIBLE_REPORT_ALGORITHM"


def test_history_checks_chart_identity_and_skips_nonexception_pages():
    conflict = compare(report(chart_line="AEL"), report())
    assert conflict.status_code == 422
    assert conflict.json()["detail"]["code"] == "INCOMPATIBLE_REPORT_SCOPE"
    response = compare(report(), report())
    assert response.status_code == 200, response.text
    result = response.json()
    assert set(result["repeated"]) == {"Low Height"}
    assert result["stats"]["total"] == 1
    assert result["context"]["line"] == "TWL"
    assert result["algorithm_provenance"] == "verified"


def test_history_unknown_legacy_context_and_algorithm_stay_unknown():
    response = compare(report(line="", algorithm="", mode=""), report(line="", algorithm="", mode=""))
    assert response.status_code == 200, response.text
    assert response.json()["context"]["line"] == ""
    assert response.json()["algorithm_provenance"] == "unknown"


def test_history_rejects_multiple_sections_inside_one_chart():
    from openpyxl import load_workbook
    workbook = load_workbook(io.BytesIO(report()))
    workbook["ChartData"].append([101., 3801., "TWL", "UT", "Siding"])
    payload = io.BytesIO()
    workbook.save(payload)
    response = compare(payload.getvalue(), report())
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INCOMPATIBLE_REPORT_SCOPE"
