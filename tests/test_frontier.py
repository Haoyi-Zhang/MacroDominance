"""Finite common-self-context, complete frontier and work-monotonicity checks.

This is a post-campaign correctness extension, not an additional workload study.
The expected node frontier is built from every actual partial choice using the
checker model; it does not use the producer's excess/dominance helpers.
"""
import itertools,json,resource,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from checker import Replay,enc
from response_cover import solve,MODES
from instances import random_small,public_case,masked,exposed
from dominance_instances import biased

def direct_difference(p,q,weights):
    v=p['cost']-q['cost']
    for a,b in zip(p['key'],q['key']):
        for lo,hi in ((1,2),(3,4)):
            v+=weights[b[0]]*(max(a[hi],b[hi])-min(a[lo],b[lo])-(b[hi]-b[lo]))
    return v

def signature(row):return enc([row['key'],row['cost']])

def main():
    start=time.process_time();collective=contexts_checked=0
    intervals=[(a,b) for a in range(3) for b in range(a,3)]
    functions=[(cost,a,b) for cost in range(3) for a,b in intervals]
    contexts=[(a/2,b/2) for a in range(5) for b in range(a,5)]
    values=[[cost+max(u,b)-min(l,a) for a,b in contexts] for cost,l,u in functions]
    for qi,q in enumerate(functions):
        self_i=contexts.index((q[1],q[2]))
        for size in (1,2,3):
            for subset in itertools.combinations(range(len(functions)),size):
                lhs=max(min(values[pi][ci]-values[qi][ci] for pi in subset) for ci in range(len(contexts)))
                rhs=min(values[pi][self_i]-values[qi][self_i] for pi in subset)
                assert lhs==rhs
                collective+=1;contexts_checked+=len(contexts)
    cases=[random_small(s,4,3) for s in range(40)]
    cases += [public_case(ROOT/'data/upstream',h) for h in ('balanced','columns','chain')]
    cases += [f(k,q) for f in (biased,masked,exposed) for k in (1,2,3) for q in (2,3)]
    nodes=partials=pair_tests=cardinality_checks=0
    for data in cases:
        model=Replay(data);packets={m:solve(data,m)[0] for m in MODES}
        by_mode={m:{t['node']:t for t in p['tables']} for m,p in packets.items()}
        for path in model.order:
            rr=sorted(model.groups[path]);all_rows={}
            for choices in itertools.product(*(range(len(model.points[r])) for r in rr)):
                row=model.evaluate(path,tuple(zip(rr,choices)),'support');partials+=1
                key=enc(row['key'])
                if key not in all_rows or row['cost']<all_rows[key]['cost']:all_rows[key]=row
            candidates=list(all_rows.values());expected=set()
            for q in candidates:
                dominated=False
                for p in candidates:
                    if p is q:continue
                    pair_tests+=1
                    if direct_difference(p,q,model.weights)<=0:dominated=True;break
                if not dominated:expected.add(signature(q))
            actual=by_mode['response'][path]['rows']
            assert {signature(r) for r in actual}==expected
            assert len(actual)==len(expected)
            for mode in ('equality','containment','leaf'):
                assert len(actual)<=len(by_mode[mode][path]['rows']);cardinality_checks+=1
            nodes+=1
        response_m=sum(len(t['cover']) for t in packets['response']['tables'])
        for mode in ('equality','containment','leaf'):
            assert response_m<=sum(len(t['cover']) for t in packets[mode]['tables'])
    out=dict(cases=len(cases),node_frontiers=nodes,partial_assignments=partials,
             direct_pair_tests=pair_tests,cardinality_checks=cardinality_checks,
             collective_cases=collective,collective_context_evaluations=contexts_checked,
             cpu_seconds=time.process_time()-start,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    (ROOT/'results/frontier-tests.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,sort_keys=True))
if __name__=='__main__':main()
