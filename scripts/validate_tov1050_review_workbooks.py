"""Read back artifact-authored review candidates; verify every populated cell."""
import argparse
import hashlib
import json
from pathlib import Path
import math
import pandas as pd


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    layouts=json.loads((args.output/"compatibility-layouts.json").read_text(encoding="utf-8"))
    results=[]
    for layout in layouts:
        path=args.output/"candidates"/layout["filename"]
        workbook=pd.read_excel(path,sheet_name=None,dtype=object,keep_default_na=False)
        assert set(workbook)=={s["name"] for s in layout["sheets"]}
        for sheet in layout["sheets"]:
            frame=workbook[sheet["name"]]
            assert list(frame.columns)==sheet["columns"],(path,sheet["name"],"columns")
            assert len(frame)==len(sheet["rows"]),(path,sheet["name"],"row count")
            for index,row in enumerate(sheet["rows"]):
                for column in sheet["columns"]:
                    expected=row.get(column)
                    value=frame.iloc[index][column]
                    if expected is None:
                        assert value=="",(path,sheet["name"],index,column)
                    elif isinstance(expected,(int,float)):
                        assert math.isclose(float(value),expected,rel_tol=0,abs_tol=1e-9)
                    else:
                        assert str(value)==str(expected),(path,sheet["name"],index,column,value,expected)
        results.append(dict(file=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                            status="pass_all_cells",point_rows=sum(len(s["rows"]) for s in layout["sheets"] if s["name"].endswith("Brackets")),
                            intervals="TL/Overlap/Landmark unavailable; no inferred interval populated"))
    (args.output/"candidate-readback-validation.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(dict(workbooks=len(results),point_rows=sum(r["point_rows"] for r in results),status="pass")))


if __name__=="__main__":
    main()
