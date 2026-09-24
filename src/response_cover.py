"""Exact response-dominance DP with linear-size transition coverage certificates.

Uses the producer's validated finite portfolio model. Replay lives in a separate
module which does not import this file or any producer functions. Coverage is
for the lower envelope, not a claim that every equality-key optimum is retained.
"""
from __future__ import annotations
import argparse
import itertools
import json
import math
import time
from pathlib import Path
from producer import Model, BudgetExceeded, require, load_json

MODES=('equality','containment','leaf','response')

def excess(left,right,weights):
    """Maximum relaxed-context response(left)-response(right), exactly."""
    value=left.cost-right.cost
    for a,b in zip(left.key,right.key):
        assert a[0]==b[0]
        value+=weights[a[0]]*sum(max(b[j]-a[j],0) if j%2 else max(a[j]-b[j],0)
                                for j in range(1,5))
    return value

def covers(left,right,weights,mode):
    if mode=='equality':
        return left.key==right.key and left.cost<=right.cost
    if mode=='containment':
        return left.cost<=right.cost and all(
            a[1]>=b[1] and a[2]<=b[2] and a[3]>=b[3] and a[4]<=b[4]
            for a,b in zip(left.key,right.key))
    return excess(left,right,weights)<=0

def solve(data,mode='response',max_joins=200000,max_states=20000,
          max_comparisons=2000000,seconds=30):
    require(mode in MODES,'unknown coverage mode')
    require(all(type(v) is int and v>0 for v in (max_joins,max_states,max_comparisons)),
            'positive work limits required')
    require(type(seconds) in (int,float) and math.isfinite(seconds) and seconds>0,
            'positive finite deadline required')
    wall=time.perf_counter();cpu=time.process_time();model=Model(data)
    transitions=comparisons=0;tables={};certificate_tables=[];counts=[]
    def poll():
        if time.perf_counter()-wall>seconds:raise BudgetExceeded('coverage wall-time limit')
    for node in model.nodes:
        poll();isleaf=node not in model.children
        localmode='response' if mode=='leaf' and isleaf else 'equality' if mode=='leaf' else mode
        if isleaf:
            r=next(iter(model.subsets[node]));count=len(model.leaves[r])
            candidates=(model.leaf(node,i,'support') for i in range(count))
        else:
            a,b=model.children[node];count=len(tables[a])*len(tables[b])
            candidates=(model.join(node,x,y,'support') for x,y in itertools.product(tables[a],tables[b]))
        if transitions+count>max_joins:raise BudgetExceeded('coverage transition limit at '+repr(node))
        # Each discarded candidate redirects to a currently retained dominator.
        # Transitivity means path compression resolves every source to a final row.
        redirect=[];kept={};key_index={};before=comparisons;peak=0
        def resolve(i):
            chain=[]
            while redirect[i]!=i:
                chain.append(i);i=redirect[i]
            for j in chain:redirect[j]=i
            return i
        for ordinal,s in enumerate(candidates):
            transitions+=1;redirect.append(ordinal)
            if transitions%128==0:poll()
            duplicate=key_index.get(s.key)
            if duplicate is not None:
                comparisons+=1
                if comparisons>max_comparisons:raise BudgetExceeded('coverage comparison limit')
                t=kept[duplicate]
                if (t.cost,t.choices)<=(s.cost,s.choices):
                    redirect[ordinal]=duplicate;continue
                redirect[duplicate]=ordinal;del kept[duplicate];del key_index[s.key]
            dominated=None;removed=[]
            if localmode!='equality':
                for old,t in kept.items():
                    comparisons+=1
                    if comparisons>max_comparisons:raise BudgetExceeded('coverage comparison limit')
                    if comparisons%256==0:poll()
                    if covers(t,s,model.weights,localmode):dominated=old;break
                    comparisons+=1
                    if comparisons>max_comparisons:raise BudgetExceeded('coverage comparison limit')
                    if covers(s,t,model.weights,localmode):removed.append(old)
            if dominated is not None:
                redirect[ordinal]=dominated
                # If a duplicate was removed, its path via this ordinal remains valid.
                continue
            for old in removed:
                redirect[old]=ordinal;del key_index[kept[old].key];del kept[old]
            kept[ordinal]=s;key_index[s.key]=ordinal
            peak=max(peak,len(kept))
            if len(kept)>max_states:raise BudgetExceeded('coverage state limit')
        ids=sorted(kept,key=lambda i:(kept[i].key,kept[i].cost,kept[i].choices))
        indices={ordinal:i for i,ordinal in enumerate(ids)}
        cover=[indices[resolve(i)] for i in range(count)]
        table=[kept[i] for i in ids];tables[node]=table
        certificate_tables.append({'node':node,'rows':[model.record(s) for s in table],
                                   'source':ids,'cover':cover})
        counts.append({'node':node,'width':len(model.live[node]),'transitions':count,
                       'states':len(table),'peak_online_states':peak,
                       'comparisons':comparisons-before})
    poll();root=tables[''];require(len(root)==1,'one closed root expected')
    cert={'method':'response-cover','dominance':mode,'tables':certificate_tables,
          'optimum':root[0].cost,'placement':model.record(root[0])['choices']}
    stats={'mode':mode,'optimum':root[0].cost,'transitions':transitions,
           'comparisons':comparisons,'total_states':sum(c['states'] for c in counts),
           'max_states':max(c['states'] for c in counts),
           'per_node':counts,'cpu_seconds':time.process_time()-cpu,
           'wall_seconds':time.perf_counter()-wall}
    return cert,stats

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('instance');p.add_argument('certificate');p.add_argument('--mode',choices=MODES,default='response')
    p.add_argument('--max-joins',type=int,default=200000);p.add_argument('--max-states',type=int,default=20000)
    p.add_argument('--max-comparisons',type=int,default=2000000);p.add_argument('--seconds',type=float,default=30)
    a=p.parse_args()
    try:
        cert,stats=solve(load_json(a.instance),a.mode,a.max_joins,a.max_states,a.max_comparisons,a.seconds)
        Path(a.certificate).write_text(json.dumps(cert,sort_keys=True,separators=(',',':'))+'\n')
        print(json.dumps(stats,sort_keys=True))
    except (BudgetExceeded,ValueError,KeyError,TypeError,OSError,RecursionError) as e:
        p.exit(2,'NO CERTIFICATE: '+str(e)+'\n')
if __name__=='__main__':main()
