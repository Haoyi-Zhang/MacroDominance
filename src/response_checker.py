"""Replay a response-coverage certificate without importing either producer.

Reconstructs each retained row from a cited leaf/child-pair source, then checks
one exact dominance obligation for every possible transition. The key inequality
is evaluated as a difference of spans at the target row's self-context, not via
the producer's positive-part expression.
"""
from __future__ import annotations
import argparse
import itertools
import json
import math
import time
from checker import Replay, Rejected, enc, need, read

MODES=('equality','containment','leaf','response')

def verify(data,certificate,max_joins=200000,max_states=20000,seconds=30):
    start=time.perf_counter();cpu=time.process_time()
    need(type(max_joins) is int and max_joins>0 and type(max_states) is int and max_states>0,'positive work limits')
    need(type(seconds) in (int,float) and math.isfinite(seconds) and seconds>0,'positive finite deadline')
    need(type(certificate) is dict and set(certificate)=={'method','dominance','tables','optimum','placement'},'coverage certificate fields')
    need(certificate['method']=='response-cover' and certificate['dominance'] in MODES,'coverage method')
    mode=certificate['dominance'];model=Replay(data)
    packet=certificate['tables'];need(type(packet) is list and len(packet)==len(model.order),'all nodes required')
    verified={};transitions=0;row_evaluations=0
    def poll():need(time.perf_counter()-start<=seconds,'coverage replay deadline')
    for path,supplied in zip(model.order,packet):
        poll();isleaf=path in model.leaf
        policy='response' if mode=='leaf' and isleaf else 'equality' if mode=='leaf' else mode
        need(type(supplied) is dict and set(supplied)=={'node','rows','source','cover'} and supplied['node']==path,'coverage table schema/order')
        rows=supplied['rows'];sources=supplied['source'];cover=supplied['cover']
        need(type(rows) is list and 1<=len(rows)<=max_states,'nonempty bounded retained table')
        need(type(sources) is list and len(sources)==len(rows),'source coverage')
        if isleaf:
            r=model.leaf[path];count=len(model.points[r])
            def candidate(i):return ((r,i),)
        else:
            a,b=model.kids[path];left,right=verified[a],verified[b];count=len(left)*len(right)
            def candidate(i):
                x,y=divmod(i,len(right));return tuple(sorted(left[x]+right[y]))
        need(transitions+count<=max_joins,'coverage replay transition limit')
        need(all(type(i) is int and 0<=i<count for i in sources) and len(set(sources))==len(sources),'valid unique transition sources')
        need(type(cover) is list and len(cover)==count and all(type(i) is int and 0<=i<len(rows) for i in cover),'one valid coverage edge per transition')
        witnesses=[];evaluated=[]
        for row,source in zip(rows,sources):
            poll();w=candidate(source);actual=model.evaluate(path,w,'support');row_evaluations+=1
            need(enc(row)==enc(actual),'retained row not its cited actual transition')
            witnesses.append(w);evaluated.append(actual)
        # Geometry and source identities are now established without trusting the
        # certificate. Check coverage of the complete Cartesian transition set.
        for i,target_index in enumerate(cover):
            transitions+=1
            if transitions%128==0:poll()
            q=model.evaluate(path,candidate(i),'support');p=evaluated[target_index]
            if policy=='equality':
                need(p['key']==q['key'] and p['cost']<=q['cost'],'equality coverage')
            elif policy=='containment':
                need(p['cost']<=q['cost'] and all(a[1]>=b[1] and a[2]<=b[2] and a[3]>=b[3] and a[4]<=b[4]
                                                for a,b in zip(p['key'],q['key'])),'containment coverage')
            else:
                difference=p['cost']-q['cost']
                for a,b in zip(p['key'],q['key']):
                    for lo,hi in ((1,2),(3,4)):
                        # Evaluate p minus q at the canonical box of q.
                        difference+=model.weights[b[0]]*(max(a[hi],b[hi])-min(a[lo],b[lo])-(b[hi]-b[lo]))
                need(difference<=0,'uncovered transition: positive self-context excess')
        verified[path]=witnesses
    root=packet[-1]['rows'];need(len(root)==1 and root[0]['key']==[],'one closed root')
    need(type(certificate['optimum']) is int and certificate['optimum']==root[0]['cost'],'certified optimum')
    need(enc(certificate['placement'])==enc(root[0]['choices']),'root placement')
    poll()
    return {'accepted':True,'optimum':certificate['optimum'],'replayed_transitions':transitions,
            'retained_row_evaluations':row_evaluations,'dominance_obligations':transitions,
            'cpu_seconds':time.process_time()-cpu,'wall_seconds':time.perf_counter()-start}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('instance');p.add_argument('certificate')
    p.add_argument('--max-joins',type=int,default=200000);p.add_argument('--max-states',type=int,default=20000);p.add_argument('--seconds',type=float,default=30)
    a=p.parse_args()
    try:print(json.dumps(verify(read(a.instance),read(a.certificate),a.max_joins,a.max_states,a.seconds),sort_keys=True))
    except (Rejected,KeyError,TypeError,ValueError,OSError,RecursionError) as e:p.exit(2,'REJECTED: '+str(e)+'\n')
if __name__=='__main__':main()
