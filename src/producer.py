"""Exact finite-portfolio HPWL dynamic programs. Python standard library only.

Raw coordinates, not clipped summaries, are joined. All alternatives must be
legal in pairwise interior-disjoint fixed owner regions. This is not a placer.
"""
from __future__ import annotations
from dataclasses import dataclass
import argparse
import itertools
import json
import math
import time
from pathlib import Path


class InvalidInstance(ValueError):
    pass


class BudgetExceeded(RuntimeError):
    pass


def require(test: bool, message: str) -> None:
    if not test:
        raise InvalidInstance(message)


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidInstance('duplicate JSON key: ' + key)
        result[key] = value
    return result


def load_json(path: str | Path):
    path = Path(path)
    require(path.stat().st_size <= 64 * 1024 * 1024, 'input exceeds 64 MiB')
    return json.loads(path.read_text(), object_pairs_hook=strict_object,
                      parse_constant=lambda x: (_ for _ in ()).throw(InvalidInstance(x)))


def integer(x):
    return type(x) is int and abs(x) < 2**60


def overlap(a, b):
    return max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3])


def bbox(points):
    return (min(p[0] for p in points), max(p[0] for p in points),
            min(p[1] for p in points), max(p[1] for p in points))


def merge_box(a, b):
    return (min(a[0], b[0]), max(a[1], b[1]),
            min(a[2], b[2]), max(a[3], b[3]))


def hpwl(b):
    return b[1] - b[0] + b[3] - b[2]


def transform(w, h, x, y, angle):
    return {0: (x, y), 90: (h-y, x), 180: (w-x, h-y), 270: (y, w-x)}[angle]


@dataclass
class State:
    closed: int
    live: dict
    choices: tuple
    key: tuple = ()
    cost: int = 0


class Model:
    def __init__(self, data):
        self.data = data
        require(type(data) is dict and set(data) <= {'name', 'regions', 'weights', 'tree', 'provenance'}, 'instance fields')
        require({'name','regions','weights','tree'} <= set(data), 'missing instance fields')
        require(type(data['name']) is str, 'name must be text')
        regions = data['regions']
        require(type(regions) is list and 1 <= len(regions) <= 48, '1..48 regions required')
        self.ids = []
        self.leaves = []
        self.owners = {}
        boxes = []
        macro_ids = set()
        for ri, region in enumerate(regions):
            require(type(region) is dict and set(region) == {'id','box','macros','candidates'}, 'region fields')
            name = region['id']
            require(type(name) is str and name and name not in self.ids, 'unique region identifiers required')
            self.ids.append(name)
            box = region['box']
            require(type(box) is list and len(box)==4 and all(integer(x) for x in box), 'integer owner box')
            require(box[0] < box[2] and box[1] < box[3], 'positive owner box')
            require(not any(overlap(box, old) for old in boxes), 'owner regions overlap')
            boxes.append(box)
            macros = region['macros']
            require(type(macros) is list and len(macros)>0, 'nonempty macro list')
            defs = {}
            for m in macros:
                require(type(m) is dict and set(m) == {'id','size','pins'}, 'macro fields')
                mid = m['id']
                require(type(mid) is str and mid and mid not in macro_ids, 'unique macro identifiers required')
                macro_ids.add(mid)
                require(type(m['size']) is list and len(m['size'])==2 and all(integer(x) and x>0 for x in m['size']), 'macro size')
                w,h = m['size']
                require(type(m['pins']) is list, 'pin list')
                pids = set()
                for p in m['pins']:
                    require(type(p) is dict and set(p)=={'id','net','offset'}, 'pin fields')
                    require(type(p['id']) is str and p['id'] and p['id'] not in pids, 'unique macro pin identifiers')
                    pids.add(p['id'])
                    require(type(p['net']) is str and p['net'], 'net identifier')
                    off = p['offset']
                    require(type(off) is list and len(off)==2 and all(integer(x) for x in off), 'pin offsets')
                    require(0 <= off[0] <= w and 0 <= off[1] <= h, 'pin outside macro')
                    self.owners.setdefault(p['net'],set()).add(ri)
                defs[mid] = m
            candidates = region['candidates']
            require(type(candidates) is list and 1 <= len(candidates) <= 32, '1..32 candidates per region')
            candidate_boxes = []
            for candidate in candidates:
                require(type(candidate) is list and len(candidate)==len(defs), 'candidate macro coverage')
                seen = set(); occupied=[]; netpoints={}
                for placement in candidate:
                    require(type(placement) is dict and set(placement)=={'macro','xy','rotation'}, 'placement fields')
                    mid = placement['macro']
                    require(type(mid) is str and mid in defs and mid not in seen, 'candidate macro identity')
                    seen.add(mid)
                    xy = placement['xy']; angle=placement['rotation']
                    require(type(xy) is list and len(xy)==2 and all(integer(x) for x in xy), 'placement coordinates')
                    require(type(angle) is int and angle in (0,90,180,270), 'quarter-turn rotation')
                    x,y=xy; m=defs[mid]; w,h=m['size']
                    rw,rh=(h,w) if angle in (90,270) else (w,h)
                    rect=(x,y,x+rw,y+rh)
                    require(box[0]<=rect[0]<rect[2]<=box[2] and box[1]<=rect[1]<rect[3]<=box[3], 'macro outside owner')
                    require(not any(overlap(rect, old) for old in occupied), 'local macro overlap')
                    occupied.append(rect)
                    for p in m['pins']:
                        ox,oy=transform(w,h,*p['offset'],angle)
                        netpoints.setdefault(p['net'],[]).append((x+ox,y+oy))
                candidate_boxes.append({e:bbox(points) for e,points in netpoints.items()})
            self.leaves.append(candidate_boxes)
        weights=data['weights']
        require(type(weights) is dict and set(weights)==set(self.owners), 'weights must cover exactly the nets')
        require(all(integer(v) and v>0 for v in weights.values()), 'positive integer net weights')
        self.weights=weights
        self.nodes=[]; self.subsets={}; self.children={}; seen=[]
        def walk(tree,path,depth):
            require(depth<=48,'tree depth')
            if type(tree) is str:
                require(tree in self.ids and tree not in seen, 'tree leaf identity/coverage')
                seen.append(tree); subset=frozenset([self.ids.index(tree)])
            else:
                require(type(tree) is list and len(tree)==2, 'binary tree required')
                left,right=path+'0',path+'1'
                subset=walk(tree[0],left,depth+1)|walk(tree[1],right,depth+1)
                self.children[path]=(left,right)
            self.subsets[path]=subset; self.nodes.append(path)
            return subset
        walk(data['tree'],'',0)
        require(set(seen)==set(self.ids),'tree must cover every region once')
        self.live={}; self.support={}
        for node in self.nodes:
            inside=self.subsets[node]
            self.live[node]=tuple(sorted(e for e,rs in self.owners.items() if rs & inside and rs-inside))
            bounds={}
            for e in self.live[node]:
                outside=self.owners[e]-inside
                alternatives=[[v[e] for v in self.leaves[r]] for r in sorted(outside)]
                # Exact marginal ranges of the outside minimum and maximum.
                intervals=[]
                for low_index,high_index in ((0,1),(2,3)):
                    amin=min(min(b[low_index] for b in alts) for alts in alternatives)
                    amax=min(max(b[low_index] for b in alts) for alts in alternatives)
                    bmin=max(min(b[high_index] for b in alts) for alts in alternatives)
                    bmax=max(max(b[high_index] for b in alts) for alts in alternatives)
                    intervals.extend((amin,amax,bmin,bmax))
                bounds[e]=tuple(intervals)
            self.support[node]=bounds

    def normalize(self,node,state,method):
        cost=state.closed; key=[]
        for e in self.live[node]:
            raw=state.live[e]
            if method=='raw':
                key.append((e,*raw)); continue
            ranges=self.support[node][e]; canon=[]; extra=0
            for k in (0,2):
                amin,amax,bmin,bmax=ranges[2*k:2*k+4]
                if method=='envelope':
                    amax=bmax; bmin=amin
                low,high=raw[k:k+2]
                canon.extend((min(amax,max(amin,low)),min(bmax,max(bmin,high))))
                extra+=max(amin-low,0)+max(high-bmax,0)
            key.append((e,*canon)); cost+=self.weights[e]*extra
        state.key=tuple(key); state.cost=cost
        return state

    def leaf(self,node,choice,method):
        r=next(iter(self.subsets[node])); geometry=self.leaves[r][choice]
        closed=sum(self.weights[e]*hpwl(box) for e,box in geometry.items() if e not in self.live[node])
        return self.normalize(node,State(closed,{e:geometry[e] for e in self.live[node]},((r,choice),)),method)

    def join(self,node,left,right,method):
        boxes=dict(left.live)
        for e,b in right.live.items():
            boxes[e]=merge_box(boxes[e],b) if e in boxes else b
        closed=left.closed+right.closed
        for e in set(boxes)-set(self.live[node]):
            closed+=self.weights[e]*hpwl(boxes.pop(e))
        choices=tuple(sorted(left.choices+right.choices))
        return self.normalize(node,State(closed,boxes,choices),method)

    def record(self,s):
        return {'key':[list(p) for p in s.key], 'cost':s.cost,
                'choices':[[self.ids[r],c] for r,c in s.choices]}


def solve(data,method='support',max_joins=200000,max_states=20000,seconds=30):
    require(method in ('raw','envelope','support'),'unknown method')
    require(type(max_joins) is int and max_joins>0 and type(max_states) is int and max_states>0,'positive work limits')
    require(type(seconds) in (int,float) and math.isfinite(seconds) and seconds>0,'positive finite time limit')
    start=time.perf_counter(); cpu=time.process_time(); model=Model(data)
    tables={}; transitions=0; rows=[]; per_node=[]
    for node in model.nodes:
        if time.perf_counter()-start>seconds:raise BudgetExceeded('wall-time limit')
        result={}
        if node not in model.children:
            r=next(iter(model.subsets[node]))
            candidates=(model.leaf(node,c,method) for c in range(len(model.leaves[r])))
            count=len(model.leaves[r])
        else:
            a,b=model.children[node]
            count=len(tables[a])*len(tables[b])
            if transitions+count>max_joins:
                raise BudgetExceeded(f'join limit at {node!r}: {transitions}+{count}>{max_joins}')
            candidates=(model.join(node,x,y,method) for x,y in itertools.product(tables[a].values(),tables[b].values()))
        for s in candidates:
            transitions+=1
            if transitions>max_joins:
                raise BudgetExceeded('transition limit')
            if transitions%256==0 and time.perf_counter()-start>seconds:
                raise BudgetExceeded('wall-time limit')
            prior=result.get(s.key)
            if prior is None or (s.cost,s.choices)<(prior.cost,prior.choices):
                result[s.key]=s
            if len(result)>max_states:
                raise BudgetExceeded('state limit')
        tables[node]=result
        ordered=[model.record(result[k]) for k in sorted(result)]
        rows.append({'node':node,'rows':ordered})
        per_node.append({'node':node,'width':len(model.live[node]),'transitions':count,'states':len(result)})
    if time.perf_counter()-start>seconds:raise BudgetExceeded('wall-time limit')
    root=tables[''][()]
    certificate={'method':method,'tables':rows,'optimum':root.cost,'placement':model.record(root)['choices']}
    stats={'method':method,'transitions':transitions,'table_states':sum(len(t) for t in tables.values()),
           'peak_states':max(map(len,tables.values())), 'width':max(map(len,model.live.values())),
           'cpu_seconds':time.process_time()-cpu,'wall_seconds':time.perf_counter()-start,
           'per_node':per_node}
    return certificate,stats


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('instance');p.add_argument('certificate');p.add_argument('--method',choices=['support','envelope','raw'],default='support')
    p.add_argument('--max-joins',type=int,default=200000);p.add_argument('--max-states',type=int,default=20000);p.add_argument('--seconds',type=float,default=30)
    args=p.parse_args()
    try:
        cert,stats=solve(load_json(args.instance),args.method,args.max_joins,args.max_states,args.seconds)
        Path(args.certificate).write_text(json.dumps(cert,sort_keys=True,separators=(',',':'))+'\n')
        print(json.dumps(stats,sort_keys=True))
    except (InvalidInstance,BudgetExceeded,KeyError,TypeError,ValueError,RecursionError,OSError) as exc:
        p.exit(2,str(exc)+'\n')


if __name__=='__main__':
    main()
