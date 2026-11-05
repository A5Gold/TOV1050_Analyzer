"""Activate the eight user-approved wide-v3 workbooks with verified backups."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib
import json
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'config'
REVIEW=ROOT/'outputs/metadata-review-2026-11-05/wide-v3'
OUT=ROOT/'outputs/metadata-activation-2026-11-05/wide-v3'
sys.path.insert(0,str(ROOT/'backend'))
from app.core.tov1050_metadata import TOV1050MetadataManager

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

validation=json.loads((REVIEW/'validation.json').read_text(encoding='utf-8'))
assert validation['status']=='passed' and validation['workbooks']==8
assert json.loads((REVIEW/'landmark-validation.json').read_text(encoding='utf-8'))['status']=='passed'
expected={'ISL','KTL','LAR_AEL','LAR_TCL','TKL','TKS','TWL','DRL'}
assert {Path(x['file']).name.removesuffix(' metadata.xlsx') for x in validation['results']}==expected
records=[]
for row in validation['results']:
    source=Path(row['file']).resolve();destination=CONFIG/source.name
    assert source.parent==(REVIEW/'candidates').resolve() and destination.is_file()
    assert sha(source)==row['sha256'],f'Candidate changed: {source}'
    records.append(dict(identity=source.name.removesuffix(' metadata.xlsx'),source=str(source),
        destination=str(destination),previous_sha256=sha(destination),approved_sha256=row['sha256']))
untouched={str(p):sha(p) for p in CONFIG.iterdir() if p.is_file() and p.name not in {Path(r['destination']).name for r in records} and p.name!='tov1050-metadata-release.json'}
for attempt in range(1,100):
    backup=CONFIG/'backups'/f'2026-11-05-wide-v3-activation-{attempt:02}'
    if not backup.exists():break
else:raise RuntimeError('No unused backup directory')
backup.mkdir(parents=True)
OUT.mkdir(parents=True,exist_ok=True)
release_path=CONFIG/'tov1050-metadata-release.json'
shutil.copy2(release_path,backup/release_path.name)
for row in records:
    target=Path(row['destination']);saved=backup/target.name
    shutil.copy2(target,saved)
    assert sha(saved)==row['previous_sha256']
    row['backup']=str(saved)
(backup/'backup-manifest.json').write_text(json.dumps(dict(authorization='User: approve and proceed',files=records,
    release_backup=str(backup/release_path.name),release_sha256=sha(release_path)),ensure_ascii=False,indent=2),encoding='utf-8')
changed=[]
try:
    for row in records:
        source,target=Path(row['source']),Path(row['destination'])
        assert sha(target)==row['previous_sha256'],'Config changed during activation'
        staged=target.with_suffix('.activation.tmp')
        shutil.copy2(source,staged)
        assert sha(staged)==row['approved_sha256']
        staged.replace(target)
        changed.append(row)
        assert sha(target)==row['approved_sha256']
    for row,original in zip(records,validation['results']):
        manager=TOV1050MetadataManager(Path(row['destination']))
        row['runtime_preflight']={}
        for route in original['routes']:
            identity,direction=route['sheet'].rsplit(' ',1)
            line,session=identity.removeprefix('LAR_'),'Mainline'
            if identity=='TKS':line,session='TKL','TKS'
            if direction=='PL':session,direction='PL','UT'
            assert manager.approved_interval_provider().source_kind=='wide_excel'
            context=manager.approved_interval_provider().context(line,session,direction)
            row['runtime_preflight'][route['sheet']]=dict(
                boundaries=len(manager.get_exception_boundaries(line,direction,session)),
                track_intervals=len(manager.get_track_type_intervals(line,session,direction)),
                thresholds=len(manager.get_all_thresholds()),tl_atoms=len(context['atoms']),landmarks=len(context['landmarks']))
        manager.approved_interval_provider().verify_sources()
        assert sha(Path(row['source']))==row['approved_sha256']
    twl=TOV1050MetadataManager(CONFIG/'TWL metadata.xlsx')
    assert twl.enrichment_evidence(154.2,'TWL','Mainline','UT')['Overlap']=='N'
    assert twl.enrichment_evidence(750,'TWL','Mainline','UT')['Tension Length']=='1 / 11'
    assert twl.enrichment_evidence(2853.8,'TWL','Mainline','UT')['Tension Length'] is None
    tkl=TOV1050MetadataManager(CONFIG/'TKL metadata.xlsx')
    assert tkl.enrichment_evidence(63700,'TKL','Mainline','UT')['Landmark']=='AFW / TIS901'
    assert all(sha(Path(p))==digest for p,digest in untouched.items())
    release=dict(release='2026-11-05-wide-v3',status='activated',
        approved_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),
        authorization='User: approve and proceed. Activate the eight reviewed wide-v3 candidates.',
        candidate_artifacts_unchanged=True,candidate_internal_review_status='Historical candidate labels retained; activation authorized by this manifest.',
        validation_report=str(REVIEW/'validation.json'),landmark_validation_report=str(REVIEW/'landmark-validation.json'),
        request='docs/requests/2026-11-05-wide-metadata-enrichment-rules.md',chainage_unit='m',
        enrichment_version='wide-excel-enrichment-2026-11-05-v1',files=records,
        rollback='Restore the eight backup workbooks and tov1050-metadata-release.json from '+str(backup))
    staged=release_path.with_suffix('.activation.tmp')
    staged.write_text(json.dumps(release,ensure_ascii=False,indent=2),encoding='utf-8')
    staged.replace(release_path)
    result=dict(status='passed',production_activation=True,backup=str(backup),release=release,
                unrelated_config_unchanged=True,files=8,routes=16)
    (OUT/'activation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(status='passed',files=8,routes=16,backup=str(backup)),ensure_ascii=False),flush=True)
except Exception:
    for row in changed:shutil.copy2(row['backup'],row['destination'])
    shutil.copy2(backup/release_path.name,release_path)
    raise
