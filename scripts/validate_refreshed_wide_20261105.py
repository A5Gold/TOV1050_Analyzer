"""Read back new candidates and exercise real metadata providers in isolation."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import sys
import openpyxl

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/metadata-review-2026-11-05/wide-v3'
sys.path.insert(0,str(ROOT/'backend'))
from app.core.tov1050_metadata import TOV1050MetadataManager

def rows(sheet):
    values=[list(r) for r in sheet.values]
    while values and not any(x is not None for x in values[-1]): values.pop()
    return values

def normalized(matrix):
    return [tuple(round(v,7) if isinstance(v,float) else v for v in row) for row in matrix]

def validate():
    layouts=json.loads((OUT/'layouts.json').read_text(encoding='utf-8'))
    results=[]
    for layout in layouts:
        source=Path(layout['source']); target=OUT/'candidates'/layout['filename']
        if '--existing' in sys.argv and not target.exists(): continue
        assert hashlib.sha256(source.read_bytes()).hexdigest()==layout['source_sha256']
        before=openpyxl.load_workbook(source,data_only=False)
        after=openpyxl.load_workbook(target,data_only=False)
        changed={x['name']:x for x in layout['changes']}
        for old in before:
            if old.title in changed: continue
            new=after[old.title]
            a,b=rows(old),rows(new)
            width=max(max(map(len,a),default=0),max(map(len,b),default=0))
            assert normalized([r+[None]*(width-len(r)) for r in a])==normalized([r+[None]*(width-len(r)) for r in b]),(target.name,old.title)
            assert old.sheet_state==new.sheet_state
        for name,change in changed.items():
            actual=rows(after[name]);expected=change['matrix']
            width=max(max(map(len,actual),default=0),max(map(len,expected),default=0))
            assert normalized([r+[None]*(width-len(r)) for r in actual])==normalized([r+[None]*(width-len(r)) for r in expected]),(target.name,name)
        manager=TOV1050MetadataManager(target)
        sample_results=[]
        for route in layout['routes']:
            sheet=route['sheet']; identity,direction=sheet.rsplit(' ',1)
            line=identity.removeprefix('LAR_'); session='Mainline'
            if identity=='TKS': line,session='TKL','TKS'
            if identity=='DRL' and direction=='PL':session,direction='PL','UT'
            provider=manager.approved_interval_provider()
            context=provider.context(line,session,direction)
            assert provider.source_kind=='wide_excel'
            main=rows(after[sheet]);lm=[r for r in main[1:] if r[2] is not None]
            assert len(context['landmarks'])==len(lm)
            assert sorted((r['from_m'],r['to_m']) for r in context['landmarks']) == sorted((r[0],r[1]) for r in lm) # No repeated +/-100.
            for row in main[1:]:
                if row[3] is None:continue
                position=(row[3]+row[4])/2
                value=provider.lookup(position,line,session,direction)
                expected=set(str(row[6]).split(',')) if row[6] is not None else set()
                actual=set(value['Tension Length'].split(' / ')) if value['Tension Length'] else set()
                assert actual==expected,(sheet,position,actual,expected)
                assert value['Overlap']==('Y' if len(expected)>1 else 'N' if expected else None)
            manager.get_track_type_intervals(line,session,direction)
            manager.get_exception_boundaries(line,direction,session)
            sample_results.append({'sheet':sheet,'tl_atoms':len(context['atoms']),'landmarks':len(context['landmarks'])})
        provider.verify_sources()
        results.append({'file':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'routes':sample_results,'status':'passed'})
        before.close();after.close()
        print(target.name+' passed',flush=True)
    if '--existing' in sys.argv and len(results)<len(layouts):
        print(f'Partial validation: {len(results)}/{len(layouts)} workbooks',flush=True)
        return
    twl=TOV1050MetadataManager(OUT/'candidates/TWL metadata.xlsx')
    assert twl.enrichment_evidence(154.2,'TWL','Mainline','UT')['Tension Length']=='1'
    match=twl.enrichment_evidence(750,'TWL','Mainline','UT')
    assert match['Tension Length']=='1 / 11' and match['Overlap']=='Y'
    drl=TOV1050MetadataManager(OUT/'candidates/DRL metadata.xlsx')
    assert len(drl.get_track_type_intervals('DRL','PL','UT'))==7
    assert len(drl.get_track_type_intervals('DRL','Mainline','UT'))==10
    summary={'status':'passed','workbooks':len(results),'production_activation':False,'results':results}
    (OUT/'validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':validate()
