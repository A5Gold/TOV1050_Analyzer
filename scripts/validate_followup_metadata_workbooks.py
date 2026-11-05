"""Verify exported review workbooks against the full authored layout payload."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import openpyxl


def source_row_ranges(values):
    values = sorted(set(values))
    ranges = []
    i = 0
    while i < len(values):
        start = end = values[i]
        while i + 1 < len(values) and values[i + 1] == end + 1:
            i += 1
            end = values[i]
        ranges.append(str(start) if start == end else f"{start}-{end}")
        i += 1
    return ", ".join(ranges)


def validate(output):
    layouts = json.loads((output / "workbook-layouts.json").read_text(encoding="utf-8"))
    results = []
    for layout in layouts:
        path = output / "candidates" / layout["filename"]
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=False)
        assert workbook.sheetnames == [s["name"] for s in layout["sheets"]], path
        checked = 0
        for sheet in layout["sheets"]:
            expected = sheet["matrix"]
            actual = list(workbook[sheet["name"]].values)
            assert len(actual) == len(expected), (path, sheet["name"], len(actual), len(expected))
            for ri, row in enumerate(expected):
                for ci, value in enumerate(row):
                    if ri > 0 and expected[0][ci] == "source_excel_rows" and isinstance(value, list):
                        assert actual[ri][ci] == source_row_ranges(value)
                    elif isinstance(value, (dict, list)):
                        # JS JSON.stringify emits compact JSON; parse for semantic parity.
                        assert json.loads(actual[ri][ci]) == value, (path, sheet["name"], ri+1, ci+1)
                    elif isinstance(value, (int, float)) and not isinstance(value, bool):
                        assert isinstance(actual[ri][ci], (int, float)) and math.isclose(value, actual[ri][ci], rel_tol=0, abs_tol=1e-9), (path,sheet["name"],ri+1,ci+1)
                    else:
                        assert (actual[ri][ci] if actual[ri][ci] != "" else None) == (value if value != "" else None), (path,sheet["name"],ri+1,ci+1,value,actual[ri][ci])
                    checked += 1
        workbook.close()
        results.append(dict(path=str(path), checked_cells=checked, parity="pass"))
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    results = validate(args.output)
    (args.output / "workbook-validation.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False))
