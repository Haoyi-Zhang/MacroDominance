"""Independent full-table replay using direct witness geometry, not producer code.

This implementation imports no producer functions. Independence here is a code
path property, not separate authorship, formal verification, or external review.
"""
from __future__ import annotations
import argparse
import itertools
import json
import math
from pathlib import Path
import time


class Rejected(ValueError):
    pass


def need(condition,message):
    if not condition:
        raise Rejected(message)


def pairs_hook(pairs):
    d={}
    for k,v in pairs:
        need(k not in d,'duplicate JSON key')
        d[k]=v
    return d


def read(path):
    p=Path(path)
    need(p.stat().st_size<=64*1024*1024,'file limit')
    return json.loads(p.read_text(),object_pairs_hook=pairs_hook,
                      parse_constant=lambda x: (_ for _ in ()).throw(Rejected(x)))


def enc(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def isint(x):
    return type(x) is int and -(2**60)<x<2**60


class Replay:
    def __init__(self,data):
        need(type(data) is dict and {'name','regions','weights','tree'}<=set(data)<= {'name','regions','weights','tree','provenance'},'input fields')
        need(type(data['name']) is str,'instance name')
        rr=data['regions']
        need(type(rr) is list and 1<=len(rr)<=48,'region limit')
        self.names=[];self.points=[];self.netregions={};owner_boxes=[];allmacros=set()
        def legal_rect(b):
            return type(b) in (tuple,list) and len(b)==4 and all(isint(z) for z in b) and b[0]<b[2] and b[1]<b[3]
        def separated(a,b):
            return a[2]<=b[0] or b[2]<=a[0] or a[3]<=b[1] or b[3]<=a[1]
        for rnum,r in enumerate(rr):
            need(type(r) is dict and set(r)=={'id','box','macros','candidates'},'region schema')
            need(type(r['id']) is str and r['id'] and r['id'] not in self.names,'region id')
            self.names.append(r['id']);ob=r['box']
            need(type(ob) is list and legal_rect(ob),'region rectangle')
            need(all(separated(ob,old) for old in owner_boxes),'region overlap')
            owner_boxes.append(ob);defs={}
            need(type(r['macros']) is list and r['macros'],'macros')
            for m in r['macros']:
                need(type(m) is dict and set(m)=={'id','size','pins'},'macro schema')
                mid=m['id'];need(type(mid) is str and mid and mid not in allmacros,'macro id');allmacros.add(mid)
                size=m['size'];need(type(size) is list and len(size)==2 and all(isint(z) and z>0 for z in size),'size')
                w,h=size;need(type(m['pins']) is list,'pins');pid=set()
                for pin in m['pins']:
                    need(type(pin) is dict and set(pin)=={'id','net','offset'},'pin schema')
                    need(type(pin['id']) is str and pin['id'] and pin['id'] not in pid,'pin id');pid.add(pin['id'])
                    need(type(pin['net']) is str and pin['net'],'net id')
                    off=pin['offset'];need(type(off) is list and len(off)==2 and all(isint(z) for z in off),'offset')
                    need(0<=off[0]<=w and 0<=off[1]<=h,'pin outside shape')
                    self.netregions.setdefault(pin['net'],set()).add(rnum)
                defs[mid]=m
            cs=r['candidates'];need(type(cs) is list and 1<=len(cs)<=32,'candidate limit')
            alternatives=[]
            for cspec in cs:
                need(type(cspec) is list and len(cspec)==len(defs),'macro coverage')
                seen=set();rects=[];pts={}
                for pos in cspec:
                    need(type(pos) is dict and set(pos)=={'macro','xy','rotation'},'pose schema')
                    mid=pos['macro'];need(type(mid) is str and mid in defs and mid not in seen,'pose id');seen.add(mid)
                    xy=pos['xy'];need(type(xy) is list and len(xy)==2 and all(isint(z) for z in xy),'pose xy')
                    turn=pos['rotation'];need(type(turn) is int and turn in (0,90,180,270),'rotation')
                    x,y=xy;w,h=defs[mid]['size'];pw,ph=(h,w) if turn%180 else (w,h)
                    b=(x,y,x+pw,y+ph)
                    need(ob[0]<=x and ob[1]<=y and b[2]<=ob[2] and b[3]<=ob[3],'outside owner')
                    need(all(separated(b,old) for old in rects),'overlap');rects.append(b)
                    for pin in defs[mid]['pins']:
                        px,py=pin['offset']
                        # Repeated quarter turns, separate from the producer's lookup.
                        tw,th=w,h
                        for _ in range(turn//90):
                            px,py=th-py,px;tw,th=th,tw
                        pts.setdefault(pin['net'],[]).append((x+px,y+py))
                alternatives.append(pts)
            self.points.append(alternatives)
        self.weights=data['weights']
        need(type(self.weights) is dict and set(self.weights)==set(self.netregions),'net weights')
        need(all(isint(w) and w>0 for w in self.weights.values()),'positive integer weights')
        self.order=[];self.groups={};self.kids={};self.leaf={};seen=[]
        def walk(t,path,depth):
            need(depth<=48,'tree depth')
            if type(t) is str:
                need(t in self.names and t not in seen,'tree leaf');seen.append(t)
                self.leaf[path]=self.names.index(t);g={self.leaf[path]}
            else:
                need(type(t) is list and len(t)==2,'binary hierarchy')
                self.kids[path]=[path+'0',path+'1']
                g=walk(t[0],path+'0',depth+1)|walk(t[1],path+'1',depth+1)
            self.groups[path]=g;self.order.append(path);return g
        walk(data['tree'],'',0)
        need(set(seen)==set(self.names),'tree coverage')
        self.ranges={};self.live={}
        for path in self.order:
            inside=self.groups[path];live=sorted(e for e,rs in self.netregions.items() if rs&inside and not rs<=inside)
            self.live[path]=live;bounds={}
            for e in live:
                d=[]
                for axis in (0,1):
                    per_region=[]
                    for r in sorted(self.netregions[e]-inside):
                        mins=[];maxs=[]
                        for alternative in self.points[r]:
                            vals=sorted(p[axis] for p in alternative[e]);mins.append(vals[0]);maxs.append(vals[-1])
                        per_region.append((min(mins),max(mins),min(maxs),max(maxs)))
                    d.append((min(v[0] for v in per_region),min(v[1] for v in per_region),
                              max(v[2] for v in per_region),max(v[3] for v in per_region)))
                bounds[e]=d
            self.ranges[path]=bounds

    def evaluate(self,path,witness,method):
        points={}
        need(set(r for r,c in witness)==self.groups[path] and len(witness)==len(self.groups[path]),'witness region coverage')
        for r,c in witness:
            need(type(c) is int and 0<=c<len(self.points[r]),'choice index')
            for e,pts in self.points[r][c].items():
                points.setdefault(e,[]).extend(pts)
        closed=0;offset=0;key=[]
        for e,pts in sorted(points.items()):
            lows=[min(p[d] for p in pts) for d in (0,1)]
            highs=[max(p[d] for p in pts) for d in (0,1)]
            if e not in self.live[path]:
                closed+=self.weights[e]*sum(highs[d]-lows[d] for d in (0,1));continue
            coordinates=[]
            for d in (0,1):
                lo,hi=lows[d],highs[d]
                if method=='raw':
                    coordinates.extend((lo,hi));continue
                al,ah,bl,bh=self.ranges[path][e][d]
                if method=='envelope':
                    ah=bh;bl=al
                # Piecewise endpoint responses; no helper shared with producer.
                l=al if lo<al else ah if lo>ah else lo
                u=bl if hi<bl else bh if hi>bh else hi
                coordinates.extend((l,u))
                if lo<al:offset+=self.weights[e]*(al-lo)
                if hi>bh:offset+=self.weights[e]*(hi-bh)
            key.append([e,*coordinates])
        return {'key':key,'cost':closed+offset,'choices':[[self.names[r],c] for r,c in witness]}


def verify(data,certificate,max_joins=200000,max_states=20000,seconds=30):
    start=time.perf_counter();cpu=time.process_time()
    need(type(max_joins) is int and max_joins>0 and type(max_states) is int and max_states>0,'positive work limits')
    need(type(seconds) in (int,float) and math.isfinite(seconds) and seconds>0,'positive finite time limit')
    need(type(certificate) is dict and set(certificate)=={'method','tables','optimum','placement'},'certificate fields')
    method=certificate['method'];need(method in ('raw','envelope','support'),'method')
    model=Replay(data)
    tables=certificate['tables'];need(type(tables) is list and len(tables)==len(model.order),'table coverage')
    verified={};transitions=0
    for path,supplied in zip(model.order,tables):
        need(time.perf_counter()-start<=seconds,'replay time limit')
        need(type(supplied) is dict and set(supplied)=={'node','rows'} and supplied['node']==path,'node order')
        need(type(supplied['rows']) is list and len(supplied['rows'])<=max_states,'table size')
        if path in model.leaf:
            r=model.leaf[path];witnesses=(((r,c),) for c in range(len(model.points[r])))
            count=len(model.points[r])
        else:
            a,b=model.kids[path];count=len(verified[a])*len(verified[b])
            witnesses=(tuple(sorted(x+y)) for x,y in itertools.product(verified[a],verified[b]))
        need(transitions+count<=max_joins,'replay transition limit')
        expected={}
        for witness in witnesses:
            transitions+=1
            if transitions%128==0:need(time.perf_counter()-start<=seconds,'replay time limit')
            row=model.evaluate(path,witness,method);key=tuple(tuple(t) for t in row['key'])
            old=expected.get(key)
            if old is None or (row['cost'],witness)<(old[0]['cost'],old[1]):
                expected[key]=(row,witness)
            need(len(expected)<=max_states,'replay state limit')
        rows=[expected[k][0] for k in sorted(expected)]
        need(enc(rows)==enc(supplied['rows']),'table differs from exhaustive child replay at '+repr(path))
        verified[path]=[expected[k][1] for k in sorted(expected)]
    root=certificate['tables'][-1]['rows']
    need(len(root)==1 and root[0]['key']==[],'closed root')
    need(type(certificate['optimum']) is int and root[0]['cost']==certificate['optimum'],'optimum')
    need(enc(root[0]['choices'])==enc(certificate['placement']),'root witness')
    need(time.perf_counter()-start<=seconds,'replay time limit')
    return {'accepted':True,'optimum':certificate['optimum'],'replayed_transitions':transitions,
            'cpu_seconds':time.process_time()-cpu,'wall_seconds':time.perf_counter()-start}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('instance');parser.add_argument('certificate')
    parser.add_argument('--max-joins',type=int,default=200000);parser.add_argument('--max-states',type=int,default=20000);parser.add_argument('--seconds',type=float,default=30)
    a=parser.parse_args()
    try:
        print(json.dumps(verify(read(a.instance),read(a.certificate),a.max_joins,a.max_states,a.seconds),sort_keys=True))
    except (Rejected,KeyError,TypeError,ValueError,RecursionError,OSError) as exc:
        parser.exit(2,'REJECTED: '+str(exc)+'\n')


if __name__=='__main__':
    main()
