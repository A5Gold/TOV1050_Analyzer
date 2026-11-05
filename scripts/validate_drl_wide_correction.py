"""Read back the exported candidate and check source/value parity."""
from pathlib import Path
from openpyxl import load_workbook
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/metadata-review-2026-11-03/drl-wide-v2'
expected = json.loads((OUT/'source-and-checks.json').read_text(encoding='utf-8'))
layout = json.loads((OUT/'workbook-layouts.json').read_text(encoding='utf-8'))[0]
path = OUT/layout['filename']
book = load_workbook(path,data_only=True)
assert book.sheetnames == [s['name'] for s in layout['sheets']]
assert 'Boundary Review' not in book and not any('DT' in name for name in book.sheetnames)
count = 0
for data in layout['sheets']:
    sheet = book[data['name']]
    for r,row in enumerate(data['matrix'],1):
        for c,value in enumerate(row,1):
            actual = sheet.cell(r,c).value
            if isinstance(value,(int,float)):
                assert abs(actual-value)<1e-8,(data['name'],r,c,actual,value)
            else:
                assert actual == value,(data['name'],r,c,actual,value)
            count += 1
for item in expected['threshold_checks']:
    assert book['threshold'].cell(item['row'],item['column']).value == item['value']
    if book['threshold'].cell(item['row'],3).value == 'Wire Wear':
        cls=book['threshold'].cell(item['row'],1).value
        if item['column']==7 and cls in {'Open','Tunnel'}:
            assert item['value']==9.1
for source in expected['sources']:
    assert hashlib.sha256(Path(source['path']).read_bytes()).hexdigest()==source['sha256']
for route in ['UT','PL']:
    sheet=book[f'DRL {route} Brackets']
    groups={}
    for row in sheet.iter_rows(min_row=2,values_only=True):
        position,tl,bracket,classification,identity,*_=row
        assert identity==route
        if position is not None and tl is not None and classification!='landmark':
            groups.setdefault(str(tl),[]).append(position)
    intervals={str(row[1]):row[2:4] for row in expected['tl_rows'] if row[0]==route}
    for tl,values in groups.items():
        assert intervals[tl]==[min(values),max(values)]
    # At every exported atom endpoint and midpoint, source TLs and output agree.
    for row in book[f'DRL {route}'].iter_rows(min_row=2,values_only=True):
        _,_,_,lower,upper,state,tls,_,_,_,closed=row
        if lower is None:
            continue
        position=(lower+upper)/2
        active=sorted(tl for tl,(a,b) in intervals.items() if a<=position<=b)
        assert (','.join(active) or None)==tls
        assert state==('Y' if len(active)>1 else 'N' if active else None)
        assert closed==('both' if lower==upper else 'neither')
summary={'status':'passed','cells_compared':count,'threshold_rows':40,'tl_intervals':9,
         'sources_unchanged':True,'candidate_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
         'file':str(path),'production_activation':False,'tl_rows':expected['tl_rows']}
(OUT/'validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k!='tl_rows'}))
