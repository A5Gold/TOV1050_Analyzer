"""Current design experiment: actual median sample, then noise candidate flags.

Prior study.py is superseded. Nothing here is imported by the application.
Hampel outputs are sensitivity experiments, not validated noise labels.
"""
import json, time, warnings
import numpy as np
import pandas as pd
from study import (ROOT,OUT,CTX,digest,emit,build_runs,compare,records,
                   TOV1050DataLoader,TOV1050MetadataManager,ExceptionDetector,
                   metadata_workbook_for,get_config_dir,MEASUREMENT_COLUMNS)

PROFILES=[('tight',dict(height=.5,stagger=2.,wear=.01),3.),
          ('middle',dict(height=1.,stagger=4.,wear=.02),3.),
          ('wide',dict(height=2.,stagger=8.,wear=.05),3.),
          ('middle_k5',dict(height=1.,stagger=4.,wear=.02),5.)]

def medians(raw,starts,ends):
    derived=raw.iloc[starts].copy().reset_index(drop=True)
    audit=pd.DataFrame({'Chainage_m':derived.Chainage,'source_first':raw.source_row_number.iloc[starts].to_numpy(),'source_last':raw.source_row_number.iloc[ends-1].to_numpy(),'run_size':ends-starts})
    stats={}
    lengths=ends-starts
    for c in MEASUREMENT_COLUMNS:
        v=raw[c].to_numpy(float)
        representative=np.full(len(starts),np.nan)
        source=np.full(len(starts),-1,dtype=np.int64)
        counts=np.zeros(len(starts),dtype=int)
        average_differs=0
        for n in np.unique(lengths):
            rows=np.flatnonzero(lengths==n)
            pos=starts[rows,None]+np.arange(n)[None,:]
            original=v[pos];valid=np.isfinite(original)
            a=np.sort(np.where(valid,original,np.inf),axis=1)
            count=valid.sum(axis=1);counts[rows]=count
            low=a[np.arange(len(rows)),np.maximum(count-1,0)//2]
            high=a[np.arange(len(rows)),count//2]
            selected=((original==low[:,None])|(original==high[:,None]))&valid
            offset=selected.argmax(axis=1);good=count>0
            representative[rows[good]]=original[np.arange(len(rows))[good],offset[good]]
            source[rows[good]]=pos[np.arange(len(rows))[good],offset[good]]
            average_differs+=int(((count%2==0)&good&(low!=high)).sum())
        good=source>=0
        assert np.array_equal(representative[good],v[source[good]])
        # Independent per-run scalar oracle for every populated run.
        for g in np.flatnonzero(good):
            x=v[starts[g]:ends[g]];a=sorted(x[np.isfinite(x)].tolist());n=len(a)
            centers={a[(n-1)//2],a[n//2]}
            offset=next(i for i,value in enumerate(x) if value in centers)
            assert source[g]==starts[g]+offset
        derived[c]=representative
        audit[c]=representative
        audit[c+'_source_row']=np.where(good,raw.source_row_number.to_numpy()[np.maximum(source,0)],-1)
        audit[c+'_valid_count']=counts
        stats[c]={'populated_runs':int(good.sum()),'missing_runs':int((~good).sum()),'even_medians_with_distinct_central_values':average_differs}
    return derived,audit,stats

def segments(frame,audit):
    n=len(frame);boundary=np.zeros(n,bool);boundary[0]=True
    x=frame.Chainage.to_numpy(float)
    # Prevent local filters crossing missing source rows, context, reversal or
    # unusually large spatial gaps; derive nominal step from this file rather
    # than assuming truncation precision equals actual acquisition spacing.
    boundary[1:] |= (audit.source_first.to_numpy()[1:]!=audit.source_last.to_numpy()[:-1]+1)
    dx=np.diff(x)
    positive=np.abs(dx)[np.abs(dx)>1e-8]
    nominal=float(np.median(positive)) if len(positive) else 0.
    boundary[1:] |= np.abs(dx)>3*nominal+1e-8
    direction=np.sign(dx)
    boundary[2:] |= (direction[1:]!=direction[:-1])
    for c in ['Class','Track Type','Overlap','Tension Length','Landmark']:
        a=frame[c].fillna('<missing>').astype(str).to_numpy()
        boundary[1:] |= a[1:]!=a[:-1]
    return np.cumsum(boundary)-1,nominal

def local_stats(frame,segment):
    result={}
    for c in MEASUREMENT_COLUMNS:
        x=frame[c].to_numpy(float)
        med=np.full(len(x),np.nan);mad=np.full(len(x),np.nan);neighbors=np.zeros(len(x),int)
        for seg in np.unique(segment):
            ix=np.flatnonzero(segment==seg)
            a=x[ix]
            pad=np.pad(a,(5,5),constant_values=np.nan)
            windows=np.lib.stride_tricks.sliding_window_view(pad,11).copy()
            windows[:,5]=np.nan
            with warnings.catch_warnings():
                warnings.simplefilter('ignore',RuntimeWarning)
                m=np.nanmedian(windows,axis=1)
                s=np.nanmedian(np.abs(windows-m[:,None]),axis=1)
            med[ix]=m;mad[ix]=s;neighbors[ix]=np.isfinite(windows).sum(axis=1)
        result[c]=(med,mad,neighbors)
    return result

def mask_candidates(frame,local,params,k):
    candidate=frame.copy()
    stats={};flags=[]
    for c in MEASUREMENT_COLUMNS:
        med,mad,n=local[c];v=frame[c].to_numpy(float)
        floor=params[c.rstrip('1234')]
        limit=np.maximum(floor,k*1.4826*mad)
        flag=np.isfinite(v)&(n>=6)&(np.abs(v-med)>limit+1e-10)
        candidate.loc[flag,c]=np.nan
        stats[c]={'flagged':int(flag.sum()),'evaluated':int((np.isfinite(v)&(n>=6)).sum()),'absolute_floor_mm':floor,'k':k}
        for i in np.flatnonzero(flag):
            flags.append(dict(index=int(i),channel=c,Chainage_m=float(frame.Chainage.iloc[i]),value=float(v[i]),neighbor_median=float(med[i]),neighbor_MAD=float(mad[i]),limit_mm=float(limit[i])))
    return candidate,stats,flags

def main():
    mp=metadata_workbook_for('TWL','Mainline',get_config_dir());mh=digest(mp)
    meta=TOV1050MetadataManager(mp);detector=ExceptionDetector(meta)
    report={'status':'running','semantics':'actual central raw sample per channel; Hampel flags AFTER reduction; no interpolation; flags are not confirmed noise','median_even_rule':'two central order-statistic values: earliest original acquisition whose value equals either central value','noise_profiles':PROFILES,'noise_window':'11 median positions, center excluded, >=6 finite neighbors, context/source/direction and >3x observed nominal step gap isolation','metadata_path':str(mp),'metadata_sha256_before':mh,'datasets':{}}
    rows=[]
    for size in ['partial','full']:
        path=ROOT/f'00 Reference Document/Raw data/TWL/test file {size}.csv';before=digest(path)
        t=time.perf_counter();loader=TOV1050DataLoader();raw=loader.load_data(path)
        raw['Line']='TWL';raw['Track']='UT'
        meta.require_measurement_coverage(raw.Chainage,'TWL','Mainline','UT')
        baseline,_=detector.analyze(raw,**CTX,auto_save=False)
        baseline_s=time.perf_counter()-t;starts,ends=build_runs(raw)
        t=time.perf_counter();median,audit,stats=medians(raw,starts,ends);median_s=time.perf_counter()-t
        t=time.perf_counter();median_results,_=detector.analyze(median,**CTX,auto_save=False);detect_s=time.perf_counter()-t
        impact,relations=compare(baseline,median_results)
        records(baseline).to_csv(OUT/f'{size}-current-raw-exceptions.csv',index=False)
        records(median_results).to_csv(OUT/f'{size}-median-exceptions.csv',index=False)
        audit.to_csv(OUT/f'{size}-median-audit.csv',index=False)
        pd.DataFrame(relations).to_csv(OUT/f'{size}-median-vs-raw.csv',index=False)
        segment,nominal_step=segments(median,audit)
        ds={'source_path':str(path),'source_sha256_before':before,'cleaning':loader.last_cleaning_summary,'raw_counts':{k:len(v) for k,v in baseline.items()},'baseline_seconds':baseline_s,'runs':len(median),'run_sizes':dict(zip(*[a.tolist() for a in np.unique(ends-starts,return_counts=True)])),'reduction_pct':100*(1-len(median)/len(raw)),'median_seconds_including_all_row_oracle':median_s,'median_detector_seconds':detect_s,'median_channels':stats,'median_impacts':impact,'noise_profiles':{},'noise_segments':int(segment.max()+1),'nominal_step_m':nominal_step}
        emit(stage='median',size=size,raw_rows=len(raw),median_rows=len(median),counts={k:len(v) for k,v in median_results.items()},median_seconds=round(median_s,2))
        t=time.perf_counter();local=local_stats(median,segment);ds['noise_local_stats_seconds']=time.perf_counter()-t
        assert (local['height1'][2]>=6).sum()>0, 'No valid neighborhoods: inspect segmentation before interpreting noise flags'
        for tag,params,k in PROFILES:
            hypothetical,noise_stats,flags=mask_candidates(median,local,params,k)
            t=time.perf_counter();r,_=detector.analyze(hypothetical,**CTX,auto_save=False);detect_noise_s=time.perf_counter()-t
            vsmedian,relations=compare(median_results,r)
            ds['noise_profiles'][tag]={'candidate_flags':noise_stats,'hypothetical_mask_impacts_vs_median':vsmedian,'detector_seconds':detect_noise_s}
            pd.DataFrame(flags).to_csv(OUT/f'{size}-{tag}-noise-candidates.csv',index=False)
            records(r).to_csv(OUT/f'{size}-{tag}-hypothetical-exceptions.csv',index=False)
            pd.DataFrame(relations).to_csv(OUT/f'{size}-{tag}-noise-vs-median.csv',index=False)
            rows.append({'dataset':size,'profile':tag,'median_rows':len(median),**{c+'_flags':v['flagged'] for c,v in noise_stats.items() if c.endswith(('1','2'))},**{kind.replace(' ','_')+'_count':len(v) for kind,v in r.items()}})
            emit(stage='post_median_noise_candidates',size=size,profile=tag,flags={c:v['flagged'] for c,v in noise_stats.items() if c.endswith(('1','2'))},counts={kind:len(v) for kind,v in r.items()})
        ds['source_sha256_after']=digest(path);assert before==ds['source_sha256_after']
        report['datasets'][size]=ds
        (OUT/'median-study.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        pd.DataFrame(rows).to_csv(OUT/'median-noise-summary.csv',index=False)
    report['metadata_sha256_after']=digest(mp);assert mh==report['metadata_sha256_after']
    report['status']='completed_read_only_median_and_noise_sensitivity_study'
    (OUT/'median-study.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    emit(stage='complete')

if __name__=='__main__': main()
