"""Lightweight empty-string, legacy schema and localhost final-job smoke."""
import io
import tempfile
from pathlib import Path
import validate_final_compact as v
from app.core.tov1050_report_export import REPORT_NUMERIC_COLUMNS

v.LOG = io.StringIO()
v.equal(None, "", "exact empty string")
v.equal("", "", "empty string")
for wrong, expected in ((None, " "), (0, ""), (False, ""), (None, 0)):
    try:
        v.equal(wrong, expected, "must reject")
    except AssertionError:
        pass
    else:
        raise AssertionError((wrong, expected))
columns = v.ExcelExporter.CATENARY_COLUMNS
raw = v.pd.DataFrame({name: [1., 3., 5.] if name in REPORT_NUMERIC_COLUMNS else ["TWL"] * 3 for name in columns})
raw["Chainage"] = [1., 1., 2.]
raw["SampleCount [n.]"] = [10, 11, 12]
raw["source_row_number"] = [101, 102, 103]
raw["Last Pole Code [---]"] = ["", "", " "]
raw["Landmark"] = ["", "", "value"]
derived, aggregation = v.aggregate_chainage(raw)
oracle = v.verify_groups(raw, derived, aggregation)
metadata = {"analysis_revision": "smoke", "chart_data_mode": "chainage_mean", "raw_row_count": 3,
            "grouped_row_count": 2, **aggregation}
with tempfile.TemporaryDirectory(prefix="tov1050-empty-smoke-") as temp:
    directory = Path(temp)
    modern = directory / "modern.xlsx"
    v.export_analysis_report({}, derived, metadata, line="TWL", chart_statistics_df=derived, output_path=modern)
    v.verify_workbook(modern, derived, metadata, {})
    old = directory / "legacy.xlsx"
    old_meta = dict(metadata)
    old_meta.pop("sample_counter_column")
    old_meta["pass_rule"] = "SampleCount decrease"
    old_meta["analysis_revision"] = "old-smoke"
    v.export_analysis_report({}, derived, old_meta, line="TWL",
                            chart_statistics_df=derived.drop(columns=["SampleCount_first", "SampleCount_last"]), output_path=old)
    v.verify_workbook(old, derived, metadata, {}, legacy_alias_schema=True)
    v.analysis.ANALYSIS_SESSIONS["smoke"] = {
        "analysis_revision": "smoke", "raw_df": raw, "results": {},
        "params": {"line": "TWL", "track": "UT", "section": "Mainline", "session": "Mainline",
                   "date_str": "20260907", "station_start": "CEN", "station_end": "TSW", "task_no": "U1"}}
    http_path = directory / "http.xlsx"
    metrics = v.export_over_http("smoke", "smoke", http_path)
    v.verify_workbook(http_path, derived, metadata, {})
    assert metrics["poll_latency"]["count"] > 0
print("empty-string/strict negatives/modern+legacy schemas/real HTTP export smoke passed")
