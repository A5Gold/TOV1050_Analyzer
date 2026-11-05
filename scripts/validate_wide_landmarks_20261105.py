"""Check every real landmark boundary and overlap against the confirmed rule."""
from pathlib import Path
import json
import sys
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/metadata-review-2026-11-05/wide-v3'
sys.path.insert(0,str(ROOT/'backend'))
from app.core.tov1050_metadata import TOV1050MetadataManager

manifest=json.loads((OUT/'validation.json').read_text(encoding='utf-8'))
checks=[]
for book in manifest['results']:
    manager=TOV1050MetadataManager(Path(book['file']))
    for route in book['routes']:
        if not route['landmarks']: continue
        identity,direction=route['sheet'].rsplit(' ',1)
        line,session=identity.removeprefix('LAR_'),'Mainline'
        if identity=='TKS':line,session='TKL','TKS'
        context=manager.approved_interval_provider().context(line,session,direction)
        landmarks=context['landmarks']
        points={p for r in landmarks for p in (r['from_m'],r['to_m'],(r['from_m']+r['to_m'])/2)}
        for a in landmarks:
            for b in landmarks:
                lo,hi=max(a['from_m'],b['from_m']),min(a['to_m'],b['to_m'])
                if lo<=hi: points.add((lo+hi)/2)
        frame=manager.map_approved_enrichment(pd.DataFrame({'Chainage':sorted(points)}),line,session,direction)
        multiple=0
        for _,row in frame.iterrows():
            names=sorted({r['landmark'] for r in landmarks if r['from_m']<=row['Chainage']<=r['to_m']})
            assert row['Landmark']==(' / '.join(names) or None)
            if len(names)>1: multiple+=1
        manager.approved_interval_provider().verify_sources()
        checks.append(dict(sheet=route['sheet'],positions=len(points),multiple_match_positions=multiple))
        print(route['sheet']+' passed',flush=True)
result=dict(status='passed',rule='all distinct landmark names joined by /',checks=checks)
(OUT/'landmark-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
