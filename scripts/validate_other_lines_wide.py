"""Independent read-back checks for the seven wide metadata candidates."""
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile
import hashlib
import json
import math
import sys

from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/metadata-review-2026-11-03/other-lines-wide-v1'
sys.path.insert(0,str(ROOT/'backend'))
from app.core.tov1050_boundary_review import termination_evidence

def equal(actual,expected,where):
    if isinstance(expected,(int,float)) and not isinstance(expected,bool):
        assert isinstance(actual,(int,float)) and abs(actual-expected)<1e-7,(where,actual,expected)
    else:
        assert actual==expected,(where,actual,expected)

def validate():
    layouts=json.loads((OUT/'workbook-layouts.json').read_text(encoding='utf-8'))
    results=[]
    for layout in layouts:
        source=Path(layout['source'])
        assert hashlib.sha256(source.read_bytes()).hexdigest()==layout['source_sha256']
        target=OUT/'candidates'/layout['filename']
        before=load_workbook(source,data_only=False)
        after=load_workbook(target,data_only=False)
        changed={s['name'] for s in layout['changes']}
        original_cells=0
        for sheet in before:
            assert sheet.title in after
            if sheet.title in changed:
                continue
            new=after[sheet.title]
            source_rows,source_columns=sheet.max_row,sheet.max_column
            assert new.sheet_state==sheet.sheet_state,(sheet.title,'visibility changed')
            for row in sheet:
                for cell in row:
                    equal(new.cell(cell.row,cell.column).value,cell.value,f'{sheet.title}!{cell.coordinate}')
                    original_cells+=1
            # Detect extra nonempty rows or columns in the preserved sheets.
            for row in new:
                for cell in row:
                    if cell.row>source_rows or cell.column>source_columns:
                        assert cell.value is None,(sheet.title,cell.coordinate,'unexpected extra value')
        with ZipFile(target) as archive:
            assert set(layout['native_features']) <= set(archive.namelist())
        for data in layout['changes']+layout['added']:
            new=after[data['name']]
            for r,row in enumerate(data['matrix'],1):
                for c,value in enumerate(row,1):
                    equal(new.cell(r,c).value,value,f'{data["name"]}!{r},{c}')
        tl_records=[row for row in after['TL Boundaries'].iter_rows(min_row=2,values_only=True) if row[0]]
        landmark_records=[row for row in after['Landmark Points'].iter_rows(min_row=2,values_only=True) if row[0]]
        for route in layout['routes']:
            name=route['name']
            old=before[name]
            new=after[name]
            original_tracks=[tuple(old.cell(r,c).value for c in (1,2,3)) for r in range(2,old.max_row+1)
                             if old.cell(r,1).value is not None]
            new_tracks=[tuple(new.cell(r,c).value for c in (8,9,10)) for r in range(2,new.max_row+1)
                        if new.cell(r,8).value is not None]
            assert len(original_tracks)==len(new_tracks)
            for a,b in zip(original_tracks,new_tracks):
                for x,y in zip(a,b):
                    equal(y,x,name+' track')
            old_points=Counter(tuple(old.cell(r,c).value for c in (5,6,7)) for r in range(2,old.max_row+1)
                               if old.cell(r,5).value is not None or old.cell(r,7).value is not None)
            point_rows=[row for row in after[name+' Brackets'].iter_rows(min_row=2,values_only=True) if row[0] is not None]
            assert Counter(tuple(row[:3]) for row in point_rows)==old_points,(name,'point multiset')
            groups=defaultdict(list)
            expected_landmarks=[]
            for row in point_rows:
                position,tl,bracket,classification,role,origin_sheet,origin_row,*_=row
                assert origin_sheet==name
                assert tuple(old.cell(origin_row,c).value for c in (5,6,7))==tuple(row[:3])
                evidence=termination_evidence(bracket) if classification=='termination' else None
                assert role==(evidence['wire_role'] if evidence else None)
                if classification=='landmark':
                    expected_landmarks.append((position,position,bracket))
                elif classification in {'normal','termination'} and role not in {'messenger','ambiguous'}:
                    identity=str(int(tl)) if isinstance(tl,float) and tl.is_integer() else str(tl)
                    groups[identity].append(position)
            intervals={str(row[1]):(row[2],row[3]) for row in tl_records if row[0]==name}
            assert set(intervals)==set(groups)
            for tl,values in groups.items():
                equal(intervals[tl][0],min(values),name+' '+tl+' min')
                equal(intervals[tl][1],max(values),name+' '+tl+' max')
            exported_landmarks=[tuple(new.cell(r,c).value for c in (1,2,3)) for r in range(2,new.max_row+1)
                                if new.cell(r,3).value is not None]
            assert Counter(exported_landmarks)==Counter(expected_landmarks)
            assert Counter(tuple(row[1:4]) for row in landmark_records if row[0]==name)==Counter(expected_landmarks)
            atoms=[]
            for r in range(2,new.max_row+1):
                lower,upper,state,tls=[new.cell(r,c).value for c in (4,5,6,7)]
                if lower is None:
                    continue
                closed=new.cell(r,11).value
                assert lower<=upper and closed==('both' if lower==upper else 'neither')
                position=(lower+upper)/2
                active=tuple(sorted(tl for tl,(a,b) in intervals.items() if a<=position<=b))
                assert tls==(','.join(active) or None),(name,r,'active TL')
                assert state==('Y' if len(active)>1 else 'N' if active else None)
                atoms.append((lower,upper,closed,active))
            # Every physical boundary must have one and only one point atom.
            for position in {x for interval in intervals.values() for x in interval}:
                matches=[a for a in atoms if a[0]==a[1]==position and a[2]=='both']
                assert len(matches)==1,(name,position,'missing/duplicate endpoint')
        assert hashlib.sha256(source.read_bytes()).hexdigest()==layout['source_sha256']
        results.append({'identity':layout['identity'],'file':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
            'unchanged_original_cells':original_cells,'source_unchanged':True,'routes':layout['routes'],
            'sheets':len(after.sheetnames),'status':'passed'})
        print(layout['identity']+' passed',flush=True)
    summary={'status':'passed','workbooks':len(results),'source_files_unchanged':True,
        'original_cells_compared':sum(r['unchanged_original_cells'] for r in results),
        'points':sum(s['point_count'] for r in results for s in r['routes']),
        'landmarks':sum(s['landmark_count'] for r in results for s in r['routes']),
        'tension_lengths':sum(s['tl_count'] for r in results for s in r['routes']),
        'production_activation':False,'results':results}
    (OUT/'validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='results'}))

if __name__=='__main__':
    validate()
