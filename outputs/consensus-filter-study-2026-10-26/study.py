"""Read-only design experiment. No production filter, report writer or DB writes.

Delta is TOTAL cluster span in mm. Tied maximum-support windows are rejected,
including overlapping windows. Strict majority uses retained run length, not
only finite count. Missing channels are never counted as rejected noise.
"""
import sys, json, time, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
sys.path.insert(0, str(ROOT/'backend'))
from app.core.tov1050_data_ingestion import TOV1050DataLoader, MEASUREMENT_COLUMNS
from app.core.tov1050_metadata import TOV1050MetadataManager
from app.core.tov1050_contract import metadata_workbook_for
from app.core.config import get_config_dir
from app.core.analyzers import ExceptionDetector
from profile import run_starts

PARAMS = [dict(height=.25,stagger=1.,wear=.005),
          dict(height=.5,stagger=2.,wear=.01),
          dict(height=1.,stagger=4.,wear=.02),
          dict(height=2.,stagger=8.,wear=.05)]
CTX = dict(line='TWL',section='Mainline',track='UT',date_str='20260907',
           task_no='U1',station_start='CEN',station_end='TSW')

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def emit(**kw): print(json.dumps(kw),flush=True)

def cluster_batch(original, delta, required):
    # One batch has equal physical run length; small vectorized square matrices.
    valid=np.isfinite(original)
    order=np.argsort(np.where(valid,original,np.inf),axis=1,kind='stable')
    a=np.take_along_axis(original,order,axis=1)
    finite=np.isfinite(a)
    diff=a[:,None,:]-a[:,:,None]
    index=np.arange(a.shape[1])
    eligible=(index[None,:]>=index[:,None])
    counts=((diff<=delta+1e-10)&eligible[None,:,:]&finite[:,None,:]&finite[:,:,None]).sum(axis=2)
    support=counts.max(axis=1)
    left=counts.argmax(axis=1)
    tied=(counts==support[:,None]).sum(axis=1)>1
    good=(support>=required)&~tied
    lo=left+np.maximum(support-1,0)//2
    hi=left+support//2
    lo=np.clip(lo,0,a.shape[1]-1); hi=np.clip(hi,0,a.shape[1]-1)
    row=np.arange(len(a))
    central_low=a[row,lo]; central_high=a[row,hi]
    # Select actual central sample; among the two central values use first acquired.
    candidates=(original==central_low[:,None])|(original==central_high[:,None])
    chosen=candidates.argmax(axis=1)
    value=np.where(good,original[row,chosen],np.nan)
    status=np.full(len(a),'no_consensus',dtype=object)
    status[(support>=required)&tied]='ambiguous'
    status[valid.sum(axis=1)<required]='insufficient'
    status[valid.sum(axis=1)==0]='missing'
    status[good]='accepted'
    return value,chosen,support,status

def validate_kernel():
    checks=0
    rng=np.random.default_rng(61026)
    examples=[[0]*8+[10]*2,[0]*6+[10]*4,[0]*5+[10]*5,
              [0]*4+[10]*3+[20]*3,list(range(10)),[1,2,3,4],
              [np.nan]*10,[0]*5+[np.nan]*5]
    for n in [1,4,5,9,10,11,20,30]:
        examples.extend(rng.integers(-8,9,size=(12,n)).astype(float).tolist())
    for x in examples:
        for d in [0.,1.,3.]:
            for strict in [False,True]:
                required=max(5,len(x)//2+1) if strict else 5
                value,chosen,support,status=cluster_batch(np.array([x],float),d,required)
                finite=sorted(v for v in x if np.isfinite(v))
                windows=[]
                for l,v in enumerate(finite):
                    w=[u for u in finite[l:] if u-v<=d+1e-10]
                    windows.append(w)
                best=max(map(len,windows),default=0)
                winners=[w for w in windows if len(w)==best]
                accepted=best>=required and len(winners)==1
                assert int(support[0])==best
                assert (status[0]=='accepted')==accepted
                if accepted:
                    w=winners[0]; central={w[(best-1)//2],w[best//2]}
                    expected=next(v for v in x if v in central)
                    assert value[0]==expected and x[int(chosen[0])]==expected
                checks+=1
    return checks

def build_runs(raw):
    starts=run_starts(raw)
    boundary=np.zeros(len(raw),dtype=bool); boundary[starts]=True
    for c in ['Class','Track Type','Overlap','Tension Length','Landmark']:
        s=raw[c].fillna('<missing>').astype(str).to_numpy()
        boundary[1:] |= s[1:]!=s[:-1]
    starts=np.flatnonzero(boundary)
    ends=np.r_[starts[1:],len(raw)]
    return starts,ends

def representatives(raw,starts,ends,params,strict,save_examples=False):
    result=raw.iloc[starts].copy().reset_index(drop=True)
    lengths=ends-starts
    summary={}; provenance={}; cases=[]
    for channel in MEASUREMENT_COLUMNS:
        kind=channel.rstrip('1234'); delta=params[kind]
        values=raw[channel].to_numpy(float)
        rep=np.full(len(starts),np.nan); source=np.full(len(starts),-1,dtype=np.int64)
        support=np.zeros(len(starts),dtype=int); status=np.full(len(starts),'missing',object)
        baseline5=0; continuous5=0; point_radius5=0
        for n in np.unique(lengths):
            rows=np.flatnonzero(lengths==n)
            positions=starts[rows,None]+np.arange(n)[None,:]
            original=values[positions]
            required=max(5,int(n)//2+1) if strict else 5
            v,chosen,k,q=cluster_batch(original,delta,required)
            rep[rows]=v; source[rows]=positions[np.arange(len(rows)),chosen]
            support[rows]=k; status[rows]=q
            if save_examples:
                baseline5 += int((k>=5).sum())
                # Radius epsilon=delta/2 so its diameter matches bounded-span Delta.
                neighbors=(np.abs(original[:,:,None]-original[:,None,:])<=delta/2+1e-10).sum(axis=2)
                point_radius5 += int((neighbors.max(axis=1)>=5).sum())
                if n>=5:
                    w=np.lib.stride_tricks.sliding_window_view(original,5,axis=1)
                    accepted=(np.isfinite(w).all(axis=2)&((w.max(axis=2)-w.min(axis=2))<=delta+1e-10)).any(axis=1)
                    continuous5+=int(accepted.sum())
        good=np.isfinite(rep)
        assert np.array_equal(rep[good],values[source[good]])
        result[channel]=rep
        # Research saves no complete raw arrays; only actual selected source identity.
        provenance[channel]=(source,support,status)
        cnt=dict(zip(*[a.tolist() for a in np.unique(status,return_counts=True)]))
        populated=len(status)-cnt.get('missing',0)
        summary[channel]={'delta_mm':delta,'status':cnt,'populated_runs':populated,
                          'acceptance_pct':round(100*int(good.sum())/populated,4) if populated else None}
        if save_examples:
            summary[channel]['alternative_support_counts']={'B_at_least5_before_tie_policy':baseline5,'A_radius_delta_over2_at_least5':point_radius5,'C_contiguous5':continuous5}
            # Show largest within-run spans for review, not labels of real noise.
            spans=np.fmax.reduceat(np.where(np.isfinite(values),values,-np.inf),starts)-np.fmin.reduceat(np.where(np.isfinite(values),values,np.inf),starts)
            pick=np.argsort(np.where(np.isfinite(spans),spans,-np.inf))[-8:][::-1]
            for g in pick:
                if not np.isfinite(spans[g]): continue
                lo,hi=int(starts[g]),int(ends[g])
                cases.append({'channel':channel,'chainage_m':float(raw.Chainage.iloc[lo]),'source_first':int(raw.source_row_number.iloc[lo]),'source_last':int(raw.source_row_number.iloc[hi-1]),'status':status[g],'support':int(support[g]),'representative':float(rep[g]) if good[g] else None,'source_values':values[lo:hi].tolist()})
    return result,summary,provenance,cases

def records(results):
    parts=[]
    for kind,frame in results.items():
        if len(frame):
            f=frame.copy();f['kind']=kind;parts.append(f)
    return pd.concat(parts,ignore_index=True) if parts else pd.DataFrame(columns=['kind','FromM','ToM','maxValue','maxLocation','level'])

def compare(base,candidate):
    relations=[]; summary={}
    for kind in base.keys()|candidate.keys():
        b=base[kind];c=candidate[kind]
        metrics={'raw_count':len(b),'candidate_count':len(c),'raw_without_overlap':0,'candidate_without_overlap':0,'exact_geometry_peak_level':0,'raw_with_changed_overlaps':0,'raw_with_multiple_overlaps':0}
        matched=set()
        for i,r in b.iterrows():
            # Interval overlap in metres, includes zero-length exceptions.
            hits=c[(c.FromM<=r.ToM+1e-8)&(c.ToM>=r.FromM-1e-8)] if len(c) else c
            same=False
            for j,s in hits.iterrows():
                matched.add(j)
                equal=all(abs(float(r[k])-float(s[k]))<1e-8 for k in ['FromM','ToM','maxValue','maxLocation']) and r['level']==s['level']
                same |= equal
                relations.append(dict(kind=kind,raw_index=int(i),candidate_index=int(j),raw_from=r.FromM,raw_to=r.ToM,raw_peak=r.maxValue,raw_peak_m=r.maxLocation,raw_level=r['level'],candidate_from=s.FromM,candidate_to=s.ToM,candidate_peak=s.maxValue,candidate_peak_m=s.maxLocation,candidate_level=s['level'],exact=equal))
            if not len(hits):
                metrics['raw_without_overlap']+=1
                relations.append(dict(kind=kind,raw_index=int(i),candidate_index=None,raw_from=r.FromM,raw_to=r.ToM,raw_peak=r.maxValue,raw_peak_m=r.maxLocation,raw_level=r['level'],exact=False))
            elif same: metrics['exact_geometry_peak_level']+=1
            else: metrics['raw_with_changed_overlaps']+=1
            if len(hits)>1: metrics['raw_with_multiple_overlaps']+=1
        metrics['candidate_without_overlap']=len(c)-len(matched)
        summary[kind]=metrics
    return summary,relations

def main():
    checks=validate_kernel(); emit(stage='kernel_checked',cases=checks)
    metadata_path=metadata_workbook_for('TWL','Mainline',get_config_dir())
    meta_hash=digest(metadata_path)
    meta=TOV1050MetadataManager(metadata_path)
    detector=ExceptionDetector(meta)
    report={'parameters':PARAMS,'kernel_checks':checks,'metadata_path':str(metadata_path),'metadata_sha256_before':meta_hash,'datasets':{}}
    summary_rows=[]
    for size in ['partial','full']:
        start=time.perf_counter();path=ROOT/f'00 Reference Document/Raw data/TWL/test file {size}.csv'
        source_hash=digest(path)
        loader=TOV1050DataLoader();raw=loader.load_data(path)
        raw['Line']='TWL';raw['Track']='UT'
        meta.require_measurement_coverage(raw.Chainage,'TWL','Mainline','UT')
        baseline,_=detector.analyze(raw,**CTX,auto_save=False)
        baseline_seconds=time.perf_counter()-start
        records(baseline).to_csv(OUT/f'{size}-raw-exceptions.csv',index=False)
        starts,ends=build_runs(raw)
        dataset={'input_path':str(path),'source_sha256_before':source_hash,'cleaning':loader.last_cleaning_summary,'baseline_seconds':baseline_seconds,'raw_counts':{k:len(v) for k,v in baseline.items()},'runs':len(starts),'run_sizes':dict(zip(*[a.tolist() for a in np.unique(ends-starts,return_counts=True)])),'profiles':{}}
        emit(stage='baseline',size=size,seconds=baseline_seconds,counts=dataset['raw_counts'],runs=len(starts))
        # Four separable parameter profiles x two support policies. Each channel
        # depends only on its own Delta, so no need for all 4^3 combinations.
        for strict in [True,False]:
            for ix,params in enumerate(PARAMS,1):
                tag=f'p{ix}-'+('majority' if strict else 'five')
                t=time.perf_counter()
                derived,stats,provenance,cases=representatives(raw,starts,ends,params,strict,save_examples=(strict and ix==2))
                filter_seconds=time.perf_counter()-t
                t=time.perf_counter()
                results,_=detector.analyze(derived,**CTX,auto_save=False)
                detect_seconds=time.perf_counter()-t
                impacts,relations=compare(baseline,results)
                records(results).to_csv(OUT/f'{size}-{tag}-exceptions.csv',index=False)
                pd.DataFrame(relations).to_csv(OUT/f'{size}-{tag}-overlap-comparison.csv',index=False)
                dataset['profiles'][tag]={'params':params,'support_rule':'max(5,floor(retained_run_size/2)+1)' if strict else '5','filter_seconds':filter_seconds,'detector_seconds':detect_seconds,'channels':stats,'impacts':impacts}
                if cases:
                    (OUT/f'{size}-{tag}-review-cases.json').write_text(json.dumps(cases,indent=2,allow_nan=True),encoding='utf-8')
                    audit=pd.DataFrame({'Chainage_m':derived.Chainage,'source_first':raw.source_row_number.iloc[starts].to_numpy(),'source_last':raw.source_row_number.iloc[ends-1].to_numpy()})
                    for c,(source,support,status) in provenance.items():
                        audit[c]=derived[c].to_numpy();audit[c+'_source_row']=np.where(status=='accepted',raw.source_row_number.to_numpy()[source],-1);audit[c+'_support']=support;audit[c+'_quality']=status
                    audit.to_csv(OUT/f'{size}-{tag}-representative-audit.csv',index=False)
                summary_rows.append({'dataset':size,'profile':tag,'height_delta':params['height'],'stagger_delta':params['stagger'],'wear_delta':params['wear'],**{k.replace(' ','_')+'_count':v['candidate_count'] for k,v in impacts.items()},**{c+'_accept_pct':s['acceptance_pct'] for c,s in stats.items() if c.endswith(('1','2'))}})
                emit(stage='candidate',size=size,profile=tag,filter_seconds=round(filter_seconds,2),detector_seconds=round(detect_seconds,2),counts={k:v['candidate_count'] for k,v in impacts.items()})
        dataset['source_sha256_after']=digest(path)
        assert dataset['source_sha256_after']==source_hash
        report['datasets'][size]=dataset
        (OUT/'study.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        pd.DataFrame(summary_rows).to_csv(OUT/'candidate-summary.csv',index=False)
    report['metadata_sha256_after']=digest(metadata_path)
    assert meta_hash==report['metadata_sha256_after']
    report['status']='completed_read_only_study'
    (OUT/'study.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    emit(stage='complete')

if __name__=='__main__': main()
