"""Recheck preserved A/B files after normalizing absent-cell General format."""
import json
from benchmark_xlsxwriter import HERE, digest_workbook

summary = json.loads((HERE / "summary.json").read_text(encoding="utf-8"))
fingerprints = {name: digest_workbook(HERE / name) for name in summary["fingerprints"]}
reference = next(iter(fingerprints.values()))
summary["fingerprints"] = fingerprints
summary["matches"] = {name: value == reference for name, value in fingerprints.items()}
summary["all_equal"] = all(summary["matches"].values())
summary["validation_correction"] = "Absent openpyxl EmptyCell.number_format=None normalized to Excel General; first failed summary retained unchanged. No workbook or timing rerun."
with (HERE / "validated-summary.json").open("x", encoding="utf-8") as output:
    json.dump(summary, output, ensure_ascii=False, indent=2)
print(json.dumps({key: value for key, value in summary.items() if key not in ("fingerprints", "records")}, ensure_ascii=False, indent=2), flush=True)
assert summary["all_equal"]
