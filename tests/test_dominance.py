"""Fresh Cartesian-oracle and adversarial certificate tests for coverage pruning."""
import copy,itertools,json,math,resource,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from response_cover import solve,MODES,excess
from response_checker import verify
from checker import Rejected
from instances import random_small,public_case,core_public_case,exposed,masked
from dominance_instances import biased
from oracle import optimum

def main():
    start=time.process_time();rows=[];assignments=0
    cases=[random_small(s,4,3) for s in range(40)]
    cases += [public_case(ROOT/'data/upstream',h) for h in ('balanced','columns','chain')]
    cases += [core_public_case(ROOT/'data/upstream/core',c,h)
              for c in ('hp','n10','apte','xerox') for h in ('balanced','netaware')]
    cases += [f(k,q) for f in (biased,masked,exposed) for k in (1,2,3) for q in (2,3)]
    for c in cases:
        truth=optimum(c);assignments+=truth['assignments']
        for mode in MODES:
            cert,stats=solve(c,mode);checked=verify(c,cert)
            assert cert['optimum']==truth['optimum']==checked['optimum']
            assert checked['replayed_transitions']==stats['transitions']
            rows.append({'case':c['name'],'mode':mode,'optimum':cert['optimum'],
                         'transitions':stats['transitions'],'states':stats['total_states']})
    # Changes that cannot be rescued by a different, still-valid certificate.
    c=random_small(2,4,3);valid,_=solve(c,'response')
    mutations=[]
    def add(name,change):
        packet=copy.deepcopy(valid);change(packet);mutations.append((name,packet))
    add('missing_table',lambda p:p['tables'].pop())
    add('extra_table',lambda p:p['tables'].append(copy.deepcopy(p['tables'][-1])))
    add('wrong_node',lambda p:p['tables'][0].__setitem__('node','bad'))
    add('unknown_field',lambda p:p.__setitem__('extra',0))
    add('unknown_mode',lambda p:p.__setitem__('dominance','unverified'))
    add('wrong_method',lambda p:p.__setitem__('method','support'))
    add('missing_edge',lambda p:p['tables'][0]['cover'].pop())
    add('edge_outside_table',lambda p:p['tables'][0]['cover'].__setitem__(0,99999))
    add('boolean_edge',lambda p:p['tables'][0]['cover'].__setitem__(0,True))
    add('bad_source',lambda p:p['tables'][0]['source'].__setitem__(0,99999))
    add('boolean_source',lambda p:p['tables'][0]['source'].__setitem__(0,False))
    add('wrong_row_cost',lambda p:p['tables'][0]['rows'][0].__setitem__('cost',-1))
    add('wrong_optimum',lambda p:p.__setitem__('optimum',p['optimum']+1))
    add('boolean_optimum',lambda p:p.__setitem__('optimum',True))
    add('empty_root_placement',lambda p:p.__setitem__('placement',[]))
    add('wrong_row_choices',lambda p:p['tables'][0]['rows'][0].__setitem__('choices',[]))
    add('extra_row_key',lambda p:p['tables'][0]['rows'][0]['key'].append(['fake',0,0,0,0]))
    # Find a coverage edge to another existing, geometrically valid but
    # non-dominating row. Rejection must come from the inequality, not syntax.
    adversarial=None
    for table_i,t in enumerate(valid['tables']):
        if len(t['rows'])<2:continue
        for j,old in enumerate(t['cover']):
            for new in range(len(t['rows'])):
                if new==old:continue
                packet=copy.deepcopy(valid);packet['tables'][table_i]['cover'][j]=new
                try:verify(c,packet)
                except Rejected as e:
                    if 'positive self-context excess' in str(e):
                        adversarial=('false_dominance_edge',packet);break
            if adversarial:break
        if adversarial:break
    assert adversarial is not None;mutations.append(adversarial)
    rejected=[]
    for name,packet in mutations:
        try:verify(c,packet)
        except (Rejected,ValueError,KeyError,TypeError):rejected.append(name)
        else:raise AssertionError('accepted invalid certificate '+name)
    out={'cases':len(cases),'method_cases':len(rows),'oracle_assignments':assignments,
         'rejected_mutations':rejected,'rows':rows,'cpu_seconds':time.process_time()-start,
         'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    (ROOT/'results/dominance-tests.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='rows'}))
if __name__=='__main__':main()
