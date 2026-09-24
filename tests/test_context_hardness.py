"""Finite validation of the geometric UNSAT-to-dominance reduction.
Not a proof of the complexity theorem; the written reduction is in proofs/.
"""
import itertools,json,random,resource,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src')]
from instances import balanced,pin,single_region
from checker import Replay

def instance(n,clauses):
    # Literals are signed, one-based variable indices. A positive literal is
    # true in alternative 0; a negative literal is true in alternative 1.
    assert clauses and all(c and len({abs(l) for l in c})==len(c) for c in clauses)
    bottom=[pin('p'+str(j),'e'+str(j),0,0) for j in range(len(clauses))]
    upper=[pin('p'+str(j),'e'+str(j),0,0) for j in range(len(clauses))]+[pin('local','local',0,0)]
    macros=[{'id':'bottom','size':[1,1],'pins':bottom},
            {'id':'upper','size':[1,1],'pins':upper},
            {'id':'anchor','size':[1,1],'pins':[pin('local','local',0,0)]}]
    portfolios=[[{'macro':'bottom','xy':[0,0],'rotation':0},
                 {'macro':'upper','xy':[x,0],'rotation':0},
                 {'macro':'anchor','xy':[3,0],'rotation':0}] for x in (1,2)]
    regs=[{'id':'inside','box':[0,0,4,2],'macros':macros,'candidates':portfolios}]
    for i in range(1,n+1):
        pins=[pin('p'+str(j),'e'+str(j),1 if i in clause else 0,0)
              for j,clause in enumerate(clauses) if i in clause or -i in clause]
        # Unused variables still have a pin on a singleton dummy net, whose
        # diameter is always zero and cancels from both responses.
        if not pins:pins=[pin('unused','dummy'+str(i),0,0)]
        regs.append(single_region('x'+str(i),[0,10*i,4,10*i+2],[1,1],pins,
                                  [([1,10*i],0),([1,10*i],180)]))
    nets={p['net'] for r in regs for m in r['macros'] for p in m['pins']}
    return {'name':'context_hardness','regions':regs,'weights':{e:1 for e in sorted(nets)},
            'tree':['inside',balanced(['x'+str(i) for i in range(1,n+1)])]}

def main():
    start=time.process_time();formulas=[]
    clauses=[tuple(s*(i+1) for i,s in enumerate(signs)) for signs in itertools.product((-1,1),repeat=3)]
    for mask in range(1,256):formulas.append((3,[c for j,c in enumerate(clauses) if (mask>>j)&1]))
    rng=random.Random(731)
    for t in range(80):
        n=4;m=3+t%12;f=[]
        for j in range(m):f.append(tuple(v*rng.choice((-1,1)) for v in rng.sample(range(1,n+1),rng.choice((1,2,3)))))
        formulas.append((n,f))
    assignments=satisfiable=unsatisfiable=0;records=[]
    for n,f in formulas:
        data=instance(n,f);model=Replay(data);best=None;mins=None
        for bits in itertools.product((0,1),repeat=n):
            wp=tuple([(0,0)]+[(i+1,b) for i,b in enumerate(bits)])
            wq=tuple([(0,1)]+[(i+1,b) for i,b in enumerate(bits)])
            p=model.evaluate('',wp,'support')['cost'];q=model.evaluate('',wq,'support')['cost']
            failures=sum(not any((bits[abs(l)-1]==0)==(l>0) for l in clause) for clause in f)
            assert p-q==1-failures
            best=p-q if best is None else max(best,p-q)
            mins=failures if mins is None else min(mins,failures);assignments+=1
        assert (best<=0)==(mins>0)
        satisfiable+=mins==0;unsatisfiable+=mins>0
        records.append({'n':n,'clauses':[list(c) for c in f],'max_response_difference':best,'minimum_unsatisfied':mins})
    out={'formulas':len(formulas),'assignments':assignments,'satisfiable':satisfiable,'unsatisfiable':unsatisfiable,
         'cpu_seconds':time.process_time()-start,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'records':records}
    (ROOT/'results/context-hardness-tests.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='records'}))
if __name__=='__main__':main()
