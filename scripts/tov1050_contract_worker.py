"""Isolated, read-only worker. Imports exactly one repository per process."""
import argparse
import hashlib
import gzip
import io
import json
from pathlib import Path
import sys

import pandas as pd


def serial(frame):
    return dict(columns=list(frame.columns), rows=json.loads(frame.to_json(orient="records", double_precision=15)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--streaming", action="store_true")
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(args.repo / "backend"))
    from app.core.analyzers import ExceptionDetector
    from app.core.metadata import MetadataManager
    from app.core.exporter import ExcelExporter
    spec = json.loads(args.input.read_text(encoding="utf-8"))
    frame = pd.DataFrame(spec["measurements"])
    if spec.get("datac"):
        from app.core.data_ingestion import DataLoader
        frame = DataLoader().load_data(spec["datac"])
    results, boundaries = ExceptionDetector(MetadataManager(spec["metadata"])).analyze(frame, **spec["context"])
    if args.streaming:
        from app.core.tov1050_report_export import export_tov1050_report
        exported=export_tov1050_report(results,chart_df=frame)
    else:
        exported = ExcelExporter.export_report(results, chart_df=frame)
    report = pd.read_excel(exported, sheet_name=None)
    output = dict(results={k: serial(v) for k, v in results.items()},
                  report={k: serial(v) for k, v in report.items()},
                  boundaries=serial(boundaries), raw_rows=len(frame),
                  detector_sha256=hashlib.sha256((args.repo / "backend/app/core/analyzers.py").read_bytes()).hexdigest())
    with gzip.open(args.output, "wt", encoding="utf-8") as stream:
        json.dump(output, stream, ensure_ascii=False, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
