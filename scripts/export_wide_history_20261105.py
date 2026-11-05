"""Export the validated new report chain through the application's exporter."""
from pathlib import Path
import json
import sys
import hashlib
import os

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/validation-2026-11-05/wide-enrichment'
os.environ['DB_PATH']=str(OUT/'isolated.db')
sys.path.insert(0,str(ROOT/'backend'))
from app.core.history_report_reader import read_history_report
from app.api.endpoints.analysis import RepeatedExceptionFinder
from app.core.exporter import ExcelExporter
import openpyxl

records=json.loads((OUT/'validation.json').read_text(encoding='utf-8'))
assert records[-1]['history_stats']['total']==15
reports=[read_history_report(Path(r['report']),Path(r['report']).name,preflight=True) for r in records[:2]]
frame=RepeatedExceptionFinder().find_repeated(reports[0].exceptions,reports[1].exceptions,new_id_label='Previous 1')
assert len(frame)==15
assert frame.groupby('exception type').size().to_dict()==records[-1]['history_stats']['breakdown']
latest=reports[0].context
metadata=dict(date_str='20260907',line=latest.line,track=latest.track,branch=latest.branch,
              direction=latest.direction,section=latest.section,session=latest.legacy_session,
              task_no=latest.task_no,station_start=latest.station_start,station_end=latest.station_end)
output=OUT/'20260907_TWL_UT_MAINLINE_CEN_TSW_Exception_Report_2_Repeated.xlsx'
output.write_bytes(ExcelExporter.export_history_compare(frame,[r.filename for r in reports],metadata).getvalue())
book=openpyxl.load_workbook(output,read_only=True,data_only=True)
summary=list(book['Summary'].values)
assert len(summary)-2==15,(len(summary),summary[:2])
assert 'Previous 1' in summary[1]
book.close()
result=dict(file=str(output),sha256=hashlib.sha256(output.read_bytes()).hexdigest(),rows=len(frame),
            enrichment_filled={field:int(frame[field].notna().sum()) for field in ('Tension Length','Overlap')})
(OUT/'history-export-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False),flush=True)
