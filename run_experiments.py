"""Resumable, one-child-at-a-time experiment runner.

Existing reports, including cap failures, are skipped. Use an EMPTY --out directory
for a fresh reproduction; no source-identity check is implied by resuming a folder.
Distributed measurements live in results/campaign. The default results/reproduction
is deliberately different, so a first run after clean extraction performs work.
No output directories are deleted by this program.
"""
import argparse
import csv
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from instances import generate


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',default='results/reproduction');p.add_argument('--start',type=int,default=0);p.add_argument('--stop',type=int,default=10000);p.add_argument('--methods',nargs='+',choices=['raw','envelope','support','constant_raw'],default=['raw','envelope','support']);a=p.parse_args()
    out=Path(a.out);out=out if out.is_absolute() else ROOT/out
    (out/'jobs').mkdir(parents=True,exist_ok=True);(out/'certificates').mkdir(exist_ok=True)
    cases=generate(ROOT/'data'/'cases',ROOT/'data'/'upstream')
    jobs=[(c['name'],m) for c in cases for m in a.methods]
    for index,(name,method) in enumerate(jobs):
        if not(a.start<=index<a.stop):continue
        result=out/'jobs'/(name+'__'+method+'.json');certificate=out/'certificates'/(name+'__'+method+'.json')
        if result.exists():continue
        command=[sys.executable,str(ROOT/'src'/'benchmark_job.py'),str(ROOT/'data'/'cases'/(name+'.json')),method,str(result),str(certificate)]
        begin=time.perf_counter()
        env=os.environ.copy();env.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
        try:
            done=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,text=True,timeout=35)
            record={'command':['python','src/benchmark_job.py','data/cases/'+name+'.json',method,'<output job>','<output certificate>'],'exit_code':done.returncode,'stdout':done.stdout,'stderr':done.stderr,'wall_seconds':time.perf_counter()-begin}
            if not result.exists():
                result.write_text(json.dumps({'case':name,'method':method,'status':'process_error','process':record},indent=2)+'\n')
            else:
                row=json.loads(result.read_text());row['process']=record;result.write_text(json.dumps(row,indent=2)+'\n')
            print(index,done.stdout.strip() or 'process_error',flush=True)
        except subprocess.TimeoutExpired as exc:
            result.write_text(json.dumps({'case':name,'method':method,'status':'process_timeout','wall_seconds':time.perf_counter()-begin},indent=2)+'\n')
            print(index,name,method,'process_timeout',flush=True)
    allrows=[json.loads(f.read_text()) for f in sorted((out/'jobs').glob('*.json'))]
    summary=[]
    for r in allrows:
        d={k:r.get(k,'') for k in ('case','method','status','optimum','cpu_seconds','peak_rss_kib')}
        if r['status']=='complete':
            reps=r['repetitions'];s=reps[0]['producer']
            d.update({k:s[k] for k in ('transitions','table_states','peak_states','width')})
            d['producer_median_seconds']=statistics.median(x['producer']['wall_seconds'] for x in reps)
            d['checker_median_seconds']=statistics.median(x['checker']['wall_seconds'] for x in reps)
            d['certificate_bytes']=reps[0]['certificate_bytes']
        summary.append(d)
    fields=['case','method','status','optimum','width','transitions','table_states','peak_states','producer_median_seconds','checker_median_seconds','certificate_bytes','cpu_seconds','peak_rss_kib']
    with (out/'summary.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(summary)
    counts={s:sum(r['status']==s for r in allrows) for s in sorted(set(r['status'] for r in allrows))}
    (out/'totals.json').write_text(json.dumps({'expected_jobs':len(jobs),'recorded_jobs':len(allrows),'statuses':counts,'reported_child_cpu_seconds':sum(r.get('cpu_seconds',0) for r in allrows),'maximum_child_peak_rss_kib':max((r.get('peak_rss_kib',0) for r in allrows),default=0)},indent=2)+'\n')
    print(json.dumps(counts),flush=True)


if __name__=='__main__':main()
