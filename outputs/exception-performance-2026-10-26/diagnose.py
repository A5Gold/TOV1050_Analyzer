import sys, asyncio, time, json, os, traceback
from pathlib import Path
ROOT=Path.cwd()
sys.path.insert(0,str(ROOT/'backend'))
from app.api.endpoints import analysis as a
from app.core.tov1050_report_export import export_analysis_report
import pandas as pd
import numpy as np
try:
 import psutil
 process=psutil.Process()
except ImportError:
 process=None
OUT=ROOT/'outputs/exception-performance-2026-10-26'
report=[]
def emit(kind,**kw):
 data={'stage':kind,**kw}
 if process:data['rss_mb']=round(process.memory_info().rss/2**20,1)
 print(json.dumps(data,ensure_ascii=False),flush=True)
async def main():
 for size in ['partial','full']:
  path=ROOT/f'00 Reference Document/Raw data/TWL/test file {size}.csv'
  start=time.perf_counter()
  response=await a.analyze_data(a.AnalyzeRequest(file_path=str(path),line='TWL',section='Mainline',session='Mainline',track='UT',date_str='20260907',station_start='CEN',station_end='TSW',task_no='U1',client_session_id=f'benchmark-{size}'))
  elapsed=time.perf_counter()-start
  state=a.ANALYSIS_SESSIONS[f'benchmark-{size}']
  frame=state['raw_df']
  x=frame.Chainage.to_numpy()
  counts=frame.groupby('Chainage',sort=False).size()
  duplicates=frame[frame.Chainage.duplicated(keep=False)]
  conflicts={c:int((duplicates.groupby('Chainage')[c].nunique(dropna=True)>1).sum()) for c in ['height1','height2','stagger1','stagger2','wear1','wear2']}
  dx=np.diff(x)
  selected=frame.loc[frame.Chainage.between(9137,9145),['source_row_number','Chainage','height1','stagger1','wear1']]
  selected.to_csv(OUT/f'{size}-zigzag-source-window.csv',index=False)
  reversal=np.flatnonzero(dx>0)[:8]
  examples=[{'source_row':int(frame.iloc[i].source_row_number),'from_m':float(x[i]),'to_m':float(x[i+1])} for i in reversal]
  item={'size':size,'input_bytes':path.stat().st_size,'analysis_seconds':round(elapsed,3),'cleaning':response['cleaning_summary'],'exceptions':{k:len(v) for k,v in response['exceptions'].items()},'chart':response['chart_resolution'],'chainage_range':[float(x.min()),float(x.max())],'adjacent_increases':int((dx>0).sum()),'adjacent_decreases':int((dx<0).sum()),'adjacent_equal':int((dx==0).sum()),'unique_chainages':len(counts),'duplicate_chainages':int((counts>1).sum()),'rows_at_duplicate_chainages':len(duplicates),'conflicting_chainages':conflicts,'increase_examples':examples}
  emit('analysis_done',**item)
  start=time.perf_counter()
  emit('export_start',size=size,rows=len(frame))
  stream=export_analysis_report(response['exceptions'],chart_df=frame,metadata={'benchmark':'2026-10-26'},line='TWL')
  item['export_seconds']=round(time.perf_counter()-start,3)
  item['export_bytes']=stream.getbuffer().nbytes
  output=OUT/f'TWL-{size}-baseline.xlsx'
  output.write_bytes(stream.getvalue())
  emit('export_done',size=size,seconds=item['export_seconds'],bytes=item['export_bytes'])
  report.append(item)
  (OUT/'baseline.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
  del stream
  a.ANALYSIS_SESSIONS.clear()
  a.LAST_RAW_DF=pd.DataFrame()
  del frame,state,response
asyncio.run(main())
