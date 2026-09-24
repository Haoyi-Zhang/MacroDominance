"""Reproduce the public-adapter development null and frozen orientation pilot."""
import json,sys,time,resource
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from instances import core_public_case
from response_cover import solve,MODES
from response_checker import verify
from oracle import optimum

def main():
    rows=[];start=time.process_time()
    for circuit in ('hp','n10'):
        for layout in ('balanced','netaware'):
            for portfolio in ('translation','orientation'):
                case=core_public_case(ROOT/'data/upstream/core',circuit,layout,portfolio)
                truth=optimum(case,limit=100000)
                for mode in MODES:
                    cert,stats=solve(case,mode,max_joins=50000,max_states=10000,
                                     max_comparisons=500000,seconds=15)
                    checked=verify(case,cert,max_joins=50000,max_states=10000,seconds=30)
                    assert cert['optimum']==truth['optimum']==checked['optimum']
                    rows.append({'case':case['name'],'portfolio':portfolio,'mode':mode,
                                 'optimum':cert['optimum'],'assignments':truth['assignments'],
                                 'transitions':stats['transitions'],'states':stats['total_states'],
                                 'comparisons':stats['comparisons']})
    out={'development_circuits':['hp','n10'],
         'translation_null':'center pins and two diagonal translations; inspected first',
         'frozen_adapter':'sorted incident nets cycle over four quarter-offset pin sites; R0/R180 candidates',
         'held_out_after_freeze':['apte'],
         'prospective_postfreeze_extension':['xerox'],
         'rows':rows,'cpu_seconds':time.process_time()-start,
         'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    (ROOT/'results/public-adapter-pilot.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='rows'},sort_keys=True))
if __name__=='__main__':main()
