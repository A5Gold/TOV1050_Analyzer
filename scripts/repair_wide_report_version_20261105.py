"""Correct only the stale version label in reports made before the code fix.

This one-time test-output migration preserves every other XLSX ZIP part byte for
byte. It never touches config, source files, Summary, ChartData or evidence.
"""
from pathlib import Path
import hashlib
import json
import zipfile
import xml.etree.ElementTree as ET
from copy import copy

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/validation-2026-11-05/wide-enrichment'
N={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
   'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
manifest=json.loads((OUT/'validation.json').read_text(encoding='utf-8'))
assert manifest[-1]['history_stats']['total']==15, 'Finish real History validation first'
audit=[]
for record in manifest[:2]:
    path=Path(record['report']).resolve()
    assert path.parent==OUT.resolve()
    old_sha=hashlib.sha256(path.read_bytes()).hexdigest()
    assert old_sha==record['report_sha256']
    with zipfile.ZipFile(path) as source:
        workbook=ET.fromstring(source.read('xl/workbook.xml'))
        sheet=next(s for s in workbook.find('m:sheets',N) if s.attrib['name']=='_Metadata')
        relationship=sheet.attrib['{'+N['r']+'}id']
        rels=ET.fromstring(source.read('xl/_rels/workbook.xml.rels'))
        target=next(r.attrib['Target'] for r in rels if r.attrib['Id']==relationship)
        part=target.lstrip('/') if target.startswith('/') else 'xl/'+target
        tree=ET.fromstring(source.read(part))
        values={}
        for row in tree.findall('m:sheetData/m:row',N):
            cells=list(row)
            if len(cells)<2: continue
            key=cells[0].find('m:is/m:t',N)
            value=cells[1].find('m:is/m:t',N)
            if key is not None and value is not None: values[key.text]=value
        expected=json.loads(values['metadata_capabilities'].text)['enrichment_version']
        assert expected=='wide-excel-enrichment-2026-11-05-v1'
        previous=values['enrichment_version'].text
        assert previous in {'tov640-first-nonempty-v1',expected}
        values['enrichment_version'].text=expected
        temporary=path.with_suffix('.version-fix.xlsx')
        with zipfile.ZipFile(temporary,'w') as output:
            for info in source.infolist():
                output.writestr(copy(info),ET.tostring(tree,encoding='utf-8',xml_declaration=True) if info.filename==part else source.read(info))
        with zipfile.ZipFile(temporary) as after:
            changed=[name for name in source.namelist() if source.read(name)!=after.read(name)]
            assert changed==[part],changed
    temporary.replace(path)
    record['report_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    record['report_bytes']=path.stat().st_size
    record['metadata_version_corrected']=True
    audit.append(dict(file=str(path),old_sha256=old_sha,new_sha256=record['report_sha256'],
                      previous_version=previous,enrichment_version=expected,changed_parts=changed))
(OUT/'validation.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'version-correction-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print('Corrected version only; all other report parts unchanged',flush=True)
