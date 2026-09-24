"""One isolated, bounded benchmark job; JSON output only."""
import argparse
import gc
import json
import resource
import time
from pathlib import Path
from producer import solve,load_json,BudgetExceeded
from checker import verify
from constant_net_baseline import solve_reduced,verify_reduced


def main():
    p=argparse.ArgumentParser();p.add_argument('instance');p.add_argument('method');p.add_argument('result');p.add_argument('certificate');a=p.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
    data=load_json(a.instance);cpu=time.process_time();wall=time.perf_counter()
    row={'case':data['name'],'method':a.method,'status':'pending','limits':{'max_states':20000,'max_transitions':200000,'producer_seconds':10,'checker_seconds':10},'repetitions':[]}
    prior=None
    try:
        for _ in range(3):
            gc.collect()
            cert,stats=(solve_reduced(data,seconds=10) if a.method=='constant_raw' else solve(data,a.method,seconds=10))
            payload=json.dumps(cert,sort_keys=True,separators=(',',':'))+'\n'
            if prior is not None and prior!=payload:raise AssertionError('nondeterministic certificate')
            prior=payload
            checked=(verify_reduced(data,cert,seconds=10) if a.method=='constant_raw' else verify(data,cert,seconds=10))
            row['repetitions'].append({'producer':stats,'checker':checked,'certificate_bytes':len(payload.encode())})
        Path(a.certificate).write_text(prior)
        row['status']='complete';row['optimum']=cert['optimum']
    except BudgetExceeded as exc:
        row['status']='producer_capped';row['reason']=str(exc)
    row['cpu_seconds']=time.process_time()-cpu;row['wall_seconds']=time.perf_counter()-wall
    row['peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    Path(a.result).write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps({'case':row['case'],'method':row['method'],'status':row['status'],'cpu_seconds':row['cpu_seconds']}))


if __name__=='__main__':main()
