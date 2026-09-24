"""Fixed bounded response-cover campaign. See proofs/dominance-experiment-protocol.md."""
import argparse,json,resource,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from response_cover import solve,MODES
from response_checker import verify
from producer import BudgetExceeded
from campaign import dominance_cases
from oracle import optimum
LIMITS=dict(max_joins=50000,max_states=10000,max_comparisons=500000,seconds=15)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',default='results/dominance-campaign')
    args=parser.parse_args();out=Path(args.out)
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        parser.error('output directory must be absent or empty; refusing stale outcomes')
    out.mkdir(parents=True,exist_ok=True)
    (out/'certificates').mkdir(exist_ok=True);(out/'inputs').mkdir(exist_ok=True)
    # A single process, no workers. Leave room below the 4 GiB environment cap.
    resource.setrlimit(resource.RLIMIT_AS,(3500*1024*1024,3500*1024*1024))
    cases,oracle_names=dominance_cases(ROOT)
    rows=[];oracles={};start=time.process_time()
    for ci,case in enumerate(cases):
        name=case['name'];(out/'inputs'/(name+'.json')).write_text(json.dumps(case,sort_keys=True)+'\n')
        if name in oracle_names:oracles[name]=optimum(case)
        for mode in MODES:
            begin=time.process_time();record={'case':name,'mode':mode}
            try:
                cert,stats=solve(case,mode,**LIMITS)
                check=verify(case,cert,max_joins=LIMITS['max_joins'],max_states=LIMITS['max_states'],seconds=30)
                if name in oracles:assert cert['optimum']==oracles[name]['optimum']
                encoded=json.dumps(cert,sort_keys=True,separators=(',',':'))+'\n'
                (out/'certificates'/(name+'_'+mode+'.json')).write_text(encoded)
                record.update(status='success',producer=stats,checker=check,certificate_bytes=len(encoded.encode()))
            except BudgetExceeded as exc:record.update(status='limit',reason=str(exc))
            # Other failures are deliberately not relabeled as resource caps.
            except Exception as exc:
                record.update(status='failure',reason=type(exc).__name__+': '+str(exc))
            record['total_cpu_seconds']=time.process_time()-begin
            rows.append(record)
            (out/'records.json').write_text(json.dumps(rows,indent=2)+'\n')
        print(name+': '+','.join(r['mode']+'='+r['status'] for r in rows[-4:]),flush=True)
    summary={'cases':len(cases),'jobs':len(rows),'limits':LIMITS,'oracle_cases':len(oracles),
             'oracle_assignments':sum(o['assignments'] for o in oracles.values()),
             'cpu_seconds':time.process_time()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
             'success':sum(r['status']=='success' for r in rows),'limit':sum(r['status']=='limit' for r in rows),
             'failure':sum(r['status']=='failure' for r in rows)}
    (out/'oracles.json').write_text(json.dumps(oracles,indent=2)+'\n')
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary));assert summary['failure']==0
if __name__=='__main__':main()
