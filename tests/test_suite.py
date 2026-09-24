"""Finite differential tests and benign malformed-certificate controls."""
from pathlib import Path
import copy
import itertools
import json
import resource
import sys
import time
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parent)]
from producer import solve,Model,InvalidInstance,strict_object
from checker import verify,Rejected,Replay
from instances import random_small,masked,exposed,public_case,single_region,pin
from oracle import optimum
from constant_net_baseline import solve_reduced,verify_reduced


def extended_algebra():
    intervals=list(itertools.combinations_with_replacement(range(-2,4),2));checks=0;profiles=0
    for A,B in itertools.product(intervals,repeat=2):
        # Ranges of minima and maxima must be ordered componentwise.
        if A[0]>B[0] or A[1]>B[1]:continue
        contexts=[(a,b) for a in range(A[0],A[1]+1) for b in range(B[0],B[1]+1) if a<=b]
        observed={}
        for l,u in intervals:
            kl=min(A[1],max(A[0],l));ku=min(B[1],max(B[0],u))
            delta=max(A[0]-l,0)+max(u-B[1],0)
            responses=[]
            for a,b in contexts:
                v=max(u,b)-min(l,a)
                assert v==delta+max(ku,b)-min(kl,a)
                responses.append(v);checks+=1
            difference=tuple(x-responses[0] for x in responses)
            if difference in observed:assert observed[difference]==(kl,ku)
            observed[difference]=(kl,ku);profiles+=1
    return checks,profiles


def main():
    start=time.perf_counter();cpu=time.process_time();algebra=extended_algebra()
    cases=[random_small(seed,n=1+seed%6,q=1+seed%4) for seed in range(72)]
    cases+=[masked(3,3),exposed(3,3),exposed(3,3,True)]
    upstream=Path(__file__).resolve().parents[1]/'data'/'upstream'
    cases+=[public_case(upstream,l) for l in ('balanced','columns','chain')]
    # Multi-macro local geometry with internal nets, boundary contact and no-net macro.
    multi=random_small(701,n=2,q=2)
    r=multi['regions'][0]
    r['macros'].append({'id':'extra','size':[2,2],'pins':[pin('p','internal',1,1)]})
    r['macros'][0]['pins'].append(pin('aux','internal',1,1));multi['weights']['internal']=2
    r['macros'].append({'id':'nopins','size':[1,1],'pins':[]})
    for c in r['candidates']:
        c.extend([{'macro':'extra','xy':[32,32],'rotation':0},{'macro':'nopins','xy':[34,32],'rotation':0}])
    cases.append(multi)
    # Realizable-context equivalence can be coarser than independent extrema ranges.
    correlation={'name':'actual_context_correlation','regions':[
        {'id':'inside','box':[0,0,4,4],
         'macros':[{'id':m,'size':[1,1],'pins':[pin('p','e',0,0)]} for m in ('a','b')],
         'candidates':[[{'macro':'a','xy':[0,0],'rotation':0},{'macro':'b','xy':[2,2],'rotation':0}],
                       [{'macro':'a','xy':[1,0],'rotation':0},{'macro':'b','xy':[1,2],'rotation':0}]]},
        {'id':'outside','box':[0,5,4,7],
         'macros':[{'id':'c','size':[1,1],'pins':[pin('p','e',0,0)]}],
         'candidates':[[{'macro':'c','xy':[x,5],'rotation':0}] for x in (0,2)]}],
        'weights':{'e':1},'tree':['inside','outside']}
    cases.append(correlation)
    assert [max(2,x)-min(0,x) for x in (0,2)]==[2,2]
    assert [abs(1-x) for x in (0,2)]==[1,1]
    assert max(2,2)-min(0,0)==max(1,2)-min(1,0)==2
    assignments=0;differential=0;partial_assignments=0;table_comparisons=0
    for instance in cases:
        oracle=optimum(instance);assignments+=oracle['assignments']
        for method in ('raw','envelope','support'):
            cert,stats=solve(instance,method)
            assert cert['optimum']==oracle['optimum'],(instance['name'],method,cert['optimum'],oracle)
            expected=[[r['id'],c] for r,c in zip(instance['regions'],oracle['choices'])]
            assert cert['placement']==expected,(instance['name'],method,'tie witness')
            assert verify(instance,cert)['accepted'];differential+=1
            # Attack the per-key induction, not just the root optimum: every
            # partial portfolio, including ones discarded below, is enumerated.
            direct=Replay(instance)
            for table in cert['tables']:
                path=table['node'];rs=sorted(direct.groups[path]);best={}
                for choices in itertools.product(*(range(len(direct.points[r])) for r in rs)):
                    witness=tuple(zip(rs,choices));row=direct.evaluate(path,witness,method)
                    key=tuple(tuple(t) for t in row['key']);old=best.get(key)
                    if old is None or (row['cost'],witness)<(old[0]['cost'],old[1]):best[key]=(row,witness)
                    partial_assignments+=1
                exhaustive=[best[k][0] for k in sorted(best)]
                assert exhaustive==table['rows'],(instance['name'],method,path,'partial table mismatch')
                table_comparisons+=1
    baseline_comparisons=0
    for instance in cases:
        packet,_=solve_reduced(instance)
        assert packet['optimum']==optimum(instance)['optimum']
        assert verify_reduced(instance,packet)['accepted']
        baseline_comparisons+=1
    fixed=masked(3,3);packet,_=solve_reduced(fixed)
    for field,value in [('constant',-1),('removed',[]),('optimum',-1)]:
        mutant=copy.deepcopy(packet);mutant[field]=value
        try:verify_reduced(fixed,mutant)
        except Rejected:pass
        else:raise AssertionError('accepted constant baseline mutant '+field)
    base=exposed(3,3);cert,_=solve(base)
    mutations=[]
    def altered(name,edit):
        c=copy.deepcopy(cert);edit(c);mutations.append((name,c))
    altered('root optimum',lambda c:c.__setitem__('optimum',c['optimum']+1))
    altered('root witness',lambda c:c['placement'][0].__setitem__(1,999))
    altered('missing node',lambda c:c['tables'].pop(0))
    altered('duplicate node',lambda c:c['tables'].insert(0,copy.deepcopy(c['tables'][0])))
    altered('missing state',lambda c:c['tables'][0]['rows'].pop())
    altered('duplicate state',lambda c:c['tables'][0]['rows'].append(copy.deepcopy(c['tables'][0]['rows'][0])))
    altered('cost',lambda c:c['tables'][0]['rows'][0].__setitem__('cost',-1))
    altered('fake coordinates',lambda c:c['tables'][0]['rows'][0]['key'][0].__setitem__(1,999))
    altered('unknown net',lambda c:c['tables'][0]['rows'][0]['key'][0].__setitem__(0,'missing'))
    altered('invalid choice',lambda c:c['tables'][0]['rows'][0]['choices'][0].__setitem__(1,999))
    altered('missing region witness',lambda c:c['tables'][0]['rows'][0]['choices'].clear())
    altered('float cost',lambda c:c['tables'][0]['rows'][0].__setitem__('cost',float(c['tables'][0]['rows'][0]['cost'])))
    altered('boolean cost',lambda c:c['tables'][0]['rows'][0].__setitem__('cost',True))
    altered('foreign field',lambda c:c.__setitem__('claimed_width',0))
    altered('method substitution',lambda c:c.__setitem__('method','arbitrary'))
    rejected=[]
    for name,c in mutations:
        try:verify(base,c)
        except (Rejected,KeyError,TypeError,ValueError):rejected.append(name)
        else:raise AssertionError('accepted mutant '+name)
    bad=[]
    def bad_input(name,edit):
        d=copy.deepcopy(base);edit(d);bad.append((name,d))
    bad_input('overlapping owners',lambda d:d['regions'][1].__setitem__('box',d['regions'][0]['box'].copy()))
    bad_input('out of owner',lambda d:d['regions'][0]['candidates'][0][0].__setitem__('xy',[9999,9999]))
    bad_input('invalid rotation',lambda d:d['regions'][0]['candidates'][0][0].__setitem__('rotation',45))
    bad_input('missing tree leaf',lambda d:d.__setitem__('tree',d['regions'][0]['id']))
    bad_input('negative net weight',lambda d:d['weights'].__setitem__('e0',-1))
    bad_input('pin outside rectangle',lambda d:d['regions'][0]['macros'][0]['pins'][0].__setitem__('offset',[2,0]))
    bad_input('duplicate region id',lambda d:d['regions'][1].__setitem__('id',d['regions'][0]['id']))
    bad_input('empty portfolio',lambda d:d['regions'][0].__setitem__('candidates',[]))
    for name,d in bad:
        for constructor,exc in ((Model,InvalidInstance),(Replay,Rejected)):
            try:constructor(d)
            except (exc,TypeError,KeyError,ValueError):pass
            else:raise AssertionError('accepted input '+name)
    # Exact input framing and decoder behavior.
    try:json.loads('{"name":"x","name":"y"}',object_pairs_hook=strict_object)
    except InvalidInstance:pass
    else:raise AssertionError('duplicate keys')
    report={'algebra_identities':algebra[0],'algebra_profiles':algebra[1],
            'instances':len(cases),'oracle_assignments':assignments,'solver_checker_comparisons':differential,
            'partial_assignments_checked':partial_assignments,'per_node_table_comparisons':table_comparisons,
            'constant_baseline_comparisons':baseline_comparisons,'constant_baseline_mutants_rejected':3,
            'certificate_mutants_rejected':rejected,'invalid_inputs_rejected_by_both':[name for name,d in bad],
            'cpu_seconds':time.process_time()-cpu,'wall_seconds':time.perf_counter()-start,
            'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'scope':'finite exact tests, not machine-checked proofs or independent external review'}
    dest=Path(__file__).resolve().parents[1]/'results'/'tests.json';dest.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
