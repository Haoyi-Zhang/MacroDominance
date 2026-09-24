"""Replay every successful coverage certificate and check campaign inventory."""
import argparse,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'src'))
from response_checker import verify
from checker import read

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory');a=p.parse_args();root=Path(a.directory)
    start=time.process_time();rows=read(root/'records.json');summary=read(root/'summary.json');oracles=read(root/'oracles.json')
    assert len(rows)==summary['jobs']==308
    assert len({(r['case'],r['mode']) for r in rows})==len(rows)
    assert len({r['case'] for r in rows})==summary['cases']==77
    assert len(oracles)==51 and sum(x['assignments'] for x in oracles.values())==176128
    expected=set();accepted=limits=0;counts=0
    for r in rows:
        if r['status']=='limit':
            assert r['reason'].startswith(('coverage transition limit','coverage comparison limit','coverage state limit','coverage wall-time limit'))
            limits+=1;continue
        assert r['status']=='success',r
        name=r['case']+'_'+r['mode']+'.json';expected.add(name)
        packet=read(root/'certificates'/name);assert packet['dominance']==r['mode']
        checked=verify(read(root/'inputs'/(r['case']+'.json')),packet,max_joins=50000,max_states=10000,seconds=30)
        assert checked['optimum']==r['producer']['optimum']==r['checker']['optimum']
        assert checked['replayed_transitions']==r['producer']['transitions']
        assert (root/'certificates'/name).stat().st_size==r['certificate_bytes']
        if r['case'] in oracles:assert checked['optimum']==oracles[r['case']]['optimum']
        accepted+=1;counts+=checked['dominance_obligations']
    assert {x.name for x in (root/'certificates').iterdir()}==expected
    assert accepted==summary['success'] and limits==summary['limit'] and summary['failure']==0
    assert accepted+limits==308
    print(json.dumps(dict(accepted=accepted,structural_caps=limits,dominance_obligations=counts,cpu_seconds=time.process_time()-start),sort_keys=True))
if __name__=='__main__':main()
